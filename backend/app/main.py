from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.errors import install_error_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.routers.chat import router as chat_router
from app.utils.config import settings
from app.utils.logging import configure_logging


configure_logging()

app = FastAPI(
    title="SHL Conversational Assessment Recommender",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
install_error_handlers(app)
app.include_router(chat_router)

