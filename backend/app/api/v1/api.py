from fastapi import APIRouter

# Import feature routers (they must define only feature-level prefixes)
from app.api.v1 import auth, alerts, devices, vitals, telemetry, healthcare, rbac, tenants, ws_alerts, vector_search, ai_memory

api_router = APIRouter()

# Include feature routers as-is — do NOT re-prefix with /api/v1 here.
# Each feature router should declare only its feature prefix (e.g. "/auth").
api_router.include_router(auth.router)
api_router.include_router(rbac.router)
api_router.include_router(tenants.router)
api_router.include_router(healthcare.router)
api_router.include_router(telemetry.router)
api_router.include_router(vitals.router)
api_router.include_router(devices.router)
api_router.include_router(alerts.router)
api_router.include_router(vector_search.router)
api_router.include_router(ai_memory.router)
# WebSocket or non-prefixed routers can be included too
try:
    api_router.include_router(ws_alerts.router)
except Exception:
    # ws_alerts may be optional or define websocket routes already
    pass

__all__ = ["api_router"]
