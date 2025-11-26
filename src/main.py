import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.response import ApiResponse, ResponseStructure
from src.routers import routers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application started...")
    logger.info(
        f"Link for auth: https://accounts.google.com/o/oauth2/v2/auth?client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={settings.GOOGLE_REDIRECT_URI}&response_type=code&scope=openid%20email%20profile&state=random_state_string&access_type=offline&prompt=consent"
    )
    yield
    logger.info("Application closed")


app = FastAPI(lifespan=lifespan, default_response_class=ApiResponse)

for router in routers:
    app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    content = ResponseStructure(
        status=exc.status_code, message=exc.detail, data=None
    ).model_dump()
    return JSONResponse(content=content, status_code=exc.status_code)
