from typing import Dict, Set, Optional
import asyncio
import json
import threading
from uuid import UUID
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

try:
    import redis
except Exception:
    redis = None

from app.core.config import settings
from app.db.session import SessionLocal
from app.core.security import get_current_user
from app.models.user import User
from app.services.rbac import AuthorizationService
from app.services.event_bus import event_bus

logger = logging.getLogger(__name__)

router = APIRouter()


class WebSocketManager:
    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, tenant_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(tenant_id, set()).add(websocket)
        try:
            logger.info("ws_connected", extra={"tenant_id": tenant_id, "active_connections": len(self.active.get(tenant_id, []))})
            try:
                from app.core import metrics
                metrics.ws_connection_inc(tenant=str(tenant_id))
            except Exception:
                pass
        except Exception:
            logger.exception("failed_to_log_ws_connect")

    def disconnect(self, tenant_id: str, websocket: WebSocket):
        conns = self.active.get(tenant_id)
        if conns and websocket in conns:
            conns.remove(websocket)
        try:
            logger.info("ws_disconnected", extra={"tenant_id": tenant_id, "active_connections": len(self.active.get(tenant_id, []))})
            try:
                from app.core import metrics
                metrics.ws_connection_dec(tenant=str(tenant_id))
            except Exception:
                pass
        except Exception:
            logger.exception("failed_to_log_ws_disconnect")

    async def broadcast(self, tenant_id: str, message: dict):
        conns = list(self.active.get(tenant_id, []))
        for ws in conns:
            try:
                await ws.send_json(message)
                try:
                    from app.core import metrics
                    metrics.inc_ws_broadcast(tenant=str(tenant_id))
                except Exception:
                    pass
            except Exception:
                logger.exception("Failed to send WS message")

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop


def start_alert_bus_listener():
    if not redis or not settings.REDIS_URL:
        return

    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        logger.exception("Failed to initialize Redis alert listener")
        return

    def _run():
        pubsub = client.pubsub()
        pubsub.subscribe("alerts")
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                payload = json.loads(message["data"])
                tenant_id = payload.get("tenant_id")
                if not tenant_id or not manager.loop:
                    continue
                asyncio.run_coroutine_threadsafe(manager.broadcast(str(tenant_id), payload), manager.loop)
            except Exception:
                logger.exception("Failed to dispatch alert bus message to websocket clients")

    threading.Thread(target=_run, name="alert-ws-listener", daemon=True).start()
    logger.info("started_alert_ws_listener")


manager = WebSocketManager()


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket, token: str = Query(None), tenant_id: str = Query(None)):
    if not token or not tenant_id:
        await websocket.close(code=4001)
        return

    db: Session = SessionLocal()
    try:
        # authenticate user from token
        try:
            user: User = get_current_user(token, db)
        except Exception:
            await websocket.close(code=4003)
            return

        # check RBAC
        service = AuthorizationService(db)
        try:
            service.require_permission(user, "alerts:view", UUID(tenant_id))
        except Exception:
            await websocket.close(code=4003)
            return

        await manager.connect(tenant_id, websocket)
        try:
            while True:
                data = await websocket.receive_text()
                # ping/pong or simple echo for now
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            manager.disconnect(tenant_id, websocket)
    finally:
        db.close()
