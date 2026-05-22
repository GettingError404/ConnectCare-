from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.api.v1.api import api_router
from app.db.database import engine
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.core.observability import initialize_observability, capture_exception
from app.middleware.tenant_context import TenantContextMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.request_size import RequestSizeLimitMiddleware


configure_logging()
logger = get_logger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_observability()
    logger.info("app_startup_complete")
    try:
        yield
    finally:
        engine.dispose()
        logger.info("app_shutdown_complete")


app = FastAPI(lifespan=lifespan)
app.add_middleware(LoggingMiddleware, logger_name="app")
app.add_middleware(TenantContextMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

allowed_origins = [origin.strip() for origin in settings.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

trusted_hosts = [host.strip() for host in settings.TRUSTED_HOSTS.split(",") if host.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# Mount the single aggregated API router under the global version prefix
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    safe_errors = jsonable_encoder(
        exc.errors(),
        custom_encoder={bytes: lambda b: b.decode("utf-8", errors="replace")},
    )
    logger.warning("validation_error", extra={"path": request.url.path, "errors": safe_errors})
    return JSONResponse(status_code=422, content={"detail": safe_errors, "request_id": request_id_ctx.get()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    capture_exception(exc, request_path=request.url.path)
    logger.exception("unhandled_exception", exc_info=exc, extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "request_id": request_id_ctx.get()})


@app.get("/")
def read_root():
    return {"message": "API is working"}


@app.get("/health")
def health():
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.get("/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        if settings.REDIS_URL:
            import redis

            redis.Redis.from_url(settings.REDIS_URL, decode_responses=True).ping()

        return JSONResponse(status_code=200, content={"status": "ready"})
    except Exception as exc:
        logger.exception("readiness_check_failed", exc_info=exc)
        return JSONResponse(status_code=503, content={"status": "not_ready", "detail": "Readiness checks failed", "request_id": request_id_ctx.get()})


@app.get("/test-db")
def test_db():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return {"status": "DB Connected", "result": [row[0] for row in result]}
    except Exception as e:
        logger.exception("db_connection_error")
        return {"error": str(e), "request_id": request_id_ctx.get()}