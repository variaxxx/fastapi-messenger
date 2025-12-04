from src.routers.auth import router as auth_router
from src.routers.chat import router as chats_router
from src.routers.user import router as user_router
from src.routers.websocket import router as websocket_router

routers = [auth_router, user_router, chats_router, websocket_router]
