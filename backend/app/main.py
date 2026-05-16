from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.v1.api import api_router
from app.db.database import engine
from sqlalchemy import text

from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.middleware.tenant_context import TenantContextMiddleware
from app.middleware.logging_middleware import LoggingMiddleware


configure_logging()
logger = get_logger("app.main")

app = FastAPI()
app.add_middleware(LoggingMiddleware, logger_name="app")
app.add_middleware(TenantContextMiddleware)

# Mount the single aggregated API router under the global version prefix
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    safe_errors = jsonable_encoder(
        exc.errors(),
        custom_encoder={bytes: lambda b: b.decode("utf-8", errors="replace")},
    )
    logger.warning("validation_error", extra={"path": request.url.path, "errors": safe_errors})
    return JSONResponse(status_code=400, content={"detail": safe_errors, "request_id": request_id_ctx.get()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", exc_info=exc, extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "request_id": request_id_ctx.get()})


@app.get("/")
def read_root():
    return {"message": "API is working"}


@app.get("/health")
def health():
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.get("/test-db")
def test_db():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return {"status": "DB Connected", "result": [row[0] for row in result]}
    except Exception as e:
        logger.exception("db_connection_error")
        return {"error": str(e), "request_id": request_id_ctx.get()}