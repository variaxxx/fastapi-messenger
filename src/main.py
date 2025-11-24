from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.items import router as items_router


app = FastAPI()

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(items_router)