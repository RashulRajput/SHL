from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("request validation failed: %s", exc)
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid request. Send messages as user/assistant role objects."},
        )

    @app.exception_handler(Exception)
    async def generic_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled request failure")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

