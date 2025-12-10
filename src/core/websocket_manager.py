from typing import Callable, Dict, Set

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class WebSocketManager:
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.user_uuid_to_ws: Dict[str, Set[WebSocket]] = {}
        self.chat_uuid_to_ws: Dict[str, Set[WebSocket]] = {}

    def handler(self, event_type):
        def decorator(func):
            self.handlers[event_type] = func
            return func

        return decorator

    async def connect_socket(self, websocket: WebSocket):
        await websocket.accept()

    async def add_user_connection(self, user_id: str, websocket: WebSocket):
        self.user_uuid_to_ws.setdefault(str(user_id), set()).add(websocket)

    async def add_user_to_chat(self, chat_id: str, user_id: str):
        self.chat_uuid_to_ws.setdefault(str(chat_id), set()).update(
            self.user_uuid_to_ws.get(str(user_id), set())
        )

    async def remove_user_connection(self, user_id: str, websocket: WebSocket):
        self.user_uuid_to_ws.get(str(user_id), set()).remove(websocket)

    async def remove_user_from_chat(self, chat_id: str, websocket: WebSocket):
        self.chat_uuid_to_ws.get(str(chat_id), set()).remove(websocket)

    async def send_error(self, error: str, websocket: WebSocket):
        await websocket.send_json({"event": "error", "message": error})

    async def broadcast_to_chat(self, chat_id: str, event: str, message: dict):
        message = jsonable_encoder({"event": event, "data": message})
        for ws in self.chat_uuid_to_ws.get(str(chat_id), []):
            await ws.send_json(message)

    async def broadcast_to_user(self, user_id: str, event: str, message: dict):
        message = jsonable_encoder({"event": event, "data": message})
        for ws in self.user_uuid_to_ws.get(str(user_id), []):
            await ws.send_json(message)
