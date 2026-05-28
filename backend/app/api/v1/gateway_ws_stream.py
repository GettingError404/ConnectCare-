"""WS stream gateway router.

This file exists to keep router mounting explicit and avoid optional try/except
masking issues.
"""


from fastapi import APIRouter

from app.websocket.gateway import router as stream_router

router = APIRouter()
router.include_router(stream_router)

