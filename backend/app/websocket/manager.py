from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """In-memory connection registry.

    Note: This is per-process. For horizontal scaling, rely on Redis pub/sub
    for cross-replica fanout. This manager only tracks live sockets on the
    current worker.
    """

    def __init__(self):
        # tenant_id -> user_id -> session_id -> websockets
        self._lock = asyncio.Lock()
        self._by_tenant: Dict[str, Dict[str, Dict[str, Set[WebSocket]]]] = {}

        # Track last heartbeat per websocket
        self._last_seen: Dict[WebSocket, float] = {}

        # Store last activity for cleanup
        self._heartbeat_interval_seconds: int = 20
        self._stale_after_seconds: int = 60

    def configure_heartbeat(self, *, heartbeat_interval_seconds: int = 20, stale_after_seconds: int = 60) -> None:
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._stale_after_seconds = stale_after_seconds

    async def connect(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        t = str(tenant_id)
        u = str(user_id)
        s = str(session_id)

        async with self._lock:
            self._by_tenant.setdefault(t, {}).setdefault(u, {}).setdefault(s, set()).add(websocket)
            self._last_seen[websocket] = time.time()

        logger.info(
            "ws_connected",
            extra={"tenant_id": t, "user_id": u, "session_id": s},
        )

    async def disconnect(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        session_id: UUID,
        websocket: WebSocket,
    ) -> None:
        t = str(tenant_id)
        u = str(user_id)
        s = str(session_id)

        async with self._lock:
            conns = self._by_tenant.get(t, {}).get(u, {}).get(s)
            if conns and websocket in conns:
                conns.remove(websocket)
                if not conns:
                    del self._by_tenant[t][u][s]
                if not self._by_tenant[t][u]:
                    del self._by_tenant[t][u]
                if not self._by_tenant[t]:
                    del self._by_tenant[t]

            self._last_seen.pop(websocket, None)

        logger.info(
            "ws_disconnected",
            extra={"tenant_id": t, "user_id": u, "session_id": s},
        )

    async def mark_heartbeat(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._last_seen:
                self._last_seen[websocket] = time.time()

    def _stale(self, websocket: WebSocket) -> bool:
        last = self._last_seen.get(websocket)
        if last is None:
            return True
        return (time.time() - last) > self._stale_after_seconds

    async def cleanup_stale(self) -> None:
        stale: Set[WebSocket] = set()
        async with self._lock:
            stale = {ws for ws in list(self._last_seen.keys()) if self._stale(ws)}

        for ws in stale:
            try:
                await ws.close(code=4000)
            except Exception:
                pass

    async def send_json(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            # Actual cleanup will happen via disconnect when socket drops
            logger.exception("ws_send_failed")

    async def send_to_user(self, *, tenant_id: UUID, user_id: UUID, message: Dict[str, Any]) -> None:
        t = str(tenant_id)
        u = str(user_id)
        async with self._lock:
            sessions = self._by_tenant.get(t, {}).get(u, {})
            sockets: Set[WebSocket] = set()
            for ss in sessions.values():
                sockets |= ss

        for ws in sockets:
            await self.send_json(ws, message)

    async def send_to_session(self, *, tenant_id: UUID, session_id: UUID, message: Dict[str, Any]) -> None:
        t = str(tenant_id)
        s = str(session_id)
        async with self._lock:
            tenant_users = self._by_tenant.get(t, {})
            sockets: Set[WebSocket] = set()
            for user_sessions in tenant_users.values():
                conns = user_sessions.get(s)
                if conns:
                    sockets |= conns

        for ws in sockets:
            await self.send_json(ws, message)

    async def send_to_tenant(self, *, tenant_id: UUID, message: Dict[str, Any]) -> None:
        t = str(tenant_id)
        async with self._lock:
            tenant_users = self._by_tenant.get(t, {})
            sockets: Set[WebSocket] = set()
            for user_sessions in tenant_users.values():
                for conns in user_sessions.values():
                    sockets |= conns

        for ws in sockets:
            await self.send_json(ws, message)

