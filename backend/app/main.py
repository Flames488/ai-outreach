"""FastAPI application entrypoint.

`create_app()` (Phase 2 §04) rather than a bare module-level `app` — makes
testing possible with isolated app instances / dependency overrides per
test, per `backend/tests/conftest.py`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from flames_shared.enums import ErrorCode
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config.settings import get_settings
from app.core.exceptions import FlamesAPIError
from app.core.logging import setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.schemas.envelope import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

_HTTP_STATUS_TO_ERROR_CODE: dict[int, ErrorCode] = {
    401: ErrorCode.AUTH_INVALID_TOKEN,
    403: ErrorCode.AUTH_FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMIT_EXCEEDED,
    503: ErrorCode.NOT_READY,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging("api")
    get_settings().warn_on_missing_integration_credentials()
    logger.info("Flames API starting up")
    yield
    logger.info("Flames API shutting down")


def _register_middleware(app: FastAPI) -> None:
    # add_middleware() layers outward, so the LAST one added is the
    # OUTERMOST (runs first on the way in). Innermost -> outermost:
    # RequestContext, RateLimit, SecurityHeaders, GZip, CORS, TrustedHost.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_settings().allowed_hosts_list)


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(FlamesAPIError)
    async def flames_api_error_handler(request: Request, exc: FlamesAPIError) -> JSONResponse:
        body = ErrorResponse(
            message=exc.message, errors=[ErrorDetail(code=exc.error_code, detail=exc.message)]
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        error_code = _HTTP_STATUS_TO_ERROR_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        body = ErrorResponse(message=message, errors=[ErrorDetail(code=error_code, detail=message)])
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            ErrorDetail(code=ErrorCode.VALIDATION_ERROR, detail=f"{e['loc']}: {e['msg']}")
            for e in exc.errors()
        ]
        body = ErrorResponse(message="Request validation failed.", errors=errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never return a raw stack trace to the client (Part 5 §63) — full
        # detail goes to the structured logs only.
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        body = ErrorResponse(
            message="An unexpected error occurred.",
            errors=[ErrorDetail(code=ErrorCode.INTERNAL_ERROR, detail="Internal server error")],
        )
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Flames API",
        description="Autonomous job search, application, and tracking assistant",
        version="1.0.0",
        lifespan=lifespan,
        # /docs and /redoc are gated behind DEBUG=false in production
        # (Phase 2 §04) rather than exposing the schema publicly.
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    _register_middleware(app)
    _register_exception_handlers(app)
    app.include_router(api_router)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    return app


app = create_app()  # module-level instance for uvicorn
