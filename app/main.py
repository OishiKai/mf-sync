"""FastAPI entrypoint for the read-only financial summary service."""

from __future__ import annotations

import logging
import secrets
import threading
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.errors import MfSyncError
from app.gcs_cache import GcsSqliteCache
from app.models import ErrorResponse, FinancialSummary
from app.rate_limit import SlidingWindowRateLimiter
from app.repository import SqliteSummaryRepository
from app.service import FinancialSummaryService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


def create_app(
    *,
    settings: Settings | None = None,
    cache: GcsSqliteCache | None = None,
    repository: SqliteSummaryRepository | None = None,
) -> FastAPI:
    application = FastAPI(
        title="Money Forward Financial Summary API",
        version="1.0.0",
        description=(
            "Read-only access to the latest mf-dashboard financial snapshot for Custom GPT "
            "Actions. Monetary values are returned in JPY."
        ),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.state.settings = settings
    application.state.cache = cache
    application.state.repository = repository
    application.state.summary_service = None
    application.state.unauthorized_limiter = None
    application.state.authenticated_limiter = None
    application.state.runtime_lock = threading.RLock()

    def get_settings() -> Settings:
        current = application.state.settings
        if current is None:
            with application.state.runtime_lock:
                current = application.state.settings
                if current is None:
                    current = Settings.from_env()
                    application.state.settings = current
        return current

    def get_service() -> FinancialSummaryService:
        current = application.state.summary_service
        if current is None:
            with application.state.runtime_lock:
                current = application.state.summary_service
                if current is None:
                    current_settings = get_settings()
                    current_cache = application.state.cache or GcsSqliteCache(current_settings)
                    current_repository = application.state.repository or SqliteSummaryRepository()
                    current = FinancialSummaryService(current_cache, current_repository)
                    application.state.summary_service = current
        return current

    def get_rate_limiters() -> tuple[SlidingWindowRateLimiter, SlidingWindowRateLimiter]:
        unauthorized = application.state.unauthorized_limiter
        authenticated = application.state.authenticated_limiter
        if unauthorized is None or authenticated is None:
            with application.state.runtime_lock:
                unauthorized = application.state.unauthorized_limiter
                authenticated = application.state.authenticated_limiter
                if unauthorized is None or authenticated is None:
                    current_settings = get_settings()
                    unauthorized = SlidingWindowRateLimiter(
                        current_settings.unauthorized_rate_limit,
                        current_settings.rate_limit_window_seconds,
                    )
                    authenticated = SlidingWindowRateLimiter(
                        current_settings.authenticated_rate_limit,
                        current_settings.rate_limit_window_seconds,
                    )
                    application.state.unauthorized_limiter = unauthorized
                    application.state.authenticated_limiter = authenticated
        return unauthorized, authenticated

    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @application.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.exception_handler(MfSyncError)
    async def handle_service_error(_request: Request, exc: MfSyncError) -> JSONResponse:
        logger.error("request failed error_type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": exc.code, "message": exc.public_message}},
        )

    @application.get(
        "/v1/summary",
        response_model=FinancialSummary,
        operation_id="getFinancialSummary",
        summary="Get the latest complete financial snapshot",
        description=(
            "Returns the user's latest financial asset snapshot, including cash, securities, "
            "holdings, liabilities, account update states, and data freshness. Use this whenever "
            "current financial asset information is needed."
        ),
        responses={
            401: {"description": "Bearer API key is missing or invalid."},
            503: {
                "model": ErrorResponse,
                "description": "The GCS database is unavailable, unreadable, or incomplete.",
            },
        },
    )
    def get_financial_summary(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> FinancialSummary:
        current_settings = get_settings()
        authorized = not (
            credentials is None
            or credentials.scheme.lower() != "bearer"
            or not secrets.compare_digest(credentials.credentials, current_settings.api_key)
        )
        unauthorized_limiter, authenticated_limiter = get_rate_limiters()
        if not authorized:
            if not unauthorized_limiter.allow():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many authentication attempts",
                    headers={"Retry-After": str(current_settings.rate_limit_window_seconds)},
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not authenticated_limiter.allow():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(current_settings.rate_limit_window_seconds)},
            )
        return get_service().get_summary()

    return application


app = create_app()
