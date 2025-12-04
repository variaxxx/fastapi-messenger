from json import JSONDecodeError
from logging import getLogger
from typing import Annotated, List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_async_session, socket_auth_guard
from src.routers.websocket_handlers import websocket_manager
from src.schemas.auth import TokenUserInfo
from src.services.chat import get_all_chat_ids

logger = getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def ws(
    websocket: WebSocket,
    user: Annotated[TokenUserInfo, Depends(socket_auth_guard)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    await websocket_manager.connect_socket(websocket)

    await websocket_manager.add_user_connection(
        user_id=user.id, websocket=websocket
    )

    chat_ids: List[int] = await get_all_chat_ids(db=db, user_id=user.id)
    for chat_id in chat_ids:
        await websocket_manager.add_user_to_chat(
            chat_id=chat_id, websocket=websocket
        )

    try:
        while True:
            try:
                message = await websocket.receive_json()

                event = message.get("event")
                if not event:
                    await websocket_manager.send_error(
                        error="No event provided", websocket=websocket
                    )
                    continue

                handler = websocket_manager.handlers.get(event)
                if not handler:
                    await websocket_manager.send_error(
                        error="Invalid event provided", websocket=websocket
                    )
                    continue

                try:
                    await handler(
                        db=db,
                        user=user,
                        payload=message.get("data"),
                        websocket=websocket,
                    )
                except ValidationError:
                    await websocket_manager.send_error(
                        error="Invalid message payload", websocket=websocket
                    )
                except HTTPException as e:
                    await websocket_manager.send_error(e.detail, websocket)
                except Exception as e:
                    logger.exception(
                        f"Something went wrong on ws connection: {e}"
                    )
            except (JSONDecodeError, AttributeError):
                await websocket_manager.send_error(
                    error="Invalid message format", websocket=websocket
                )
    except WebSocketDisconnect:
        for chat_id in chat_ids:
            await websocket_manager.remove_user_from_chat(
                chat_id=chat_id, websocket=websocket
            )
        await websocket_manager.remove_user_connection(
            user_id=user.id, websocket=websocket
        )
