from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.middleware.tenant_context import require_tenant_context
from app.dependencies.authorization import require_permission
from app.repositories.streams import DeviceTelemetryRepository
from app.schemas.streams import DeviceTelemetryResponse

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("/elders/{elder_id}/latest", response_model=List[DeviceTelemetryResponse], dependencies=[Depends(require_permission("vitals:view"))])
def get_latest_telemetry(elder_id: UUID, limit: int = Query(50, ge=1, le=1000), db: Session = Depends(get_db), tenant_id: UUID = Depends(require_tenant_context)):
    repo = DeviceTelemetryRepository(db, tenant_id)
    rows = repo.get_latest_for_elder(elder_id, limit=limit)
    return rows


@router.get("/elders/{elder_id}/timeline", response_model=List[DeviceTelemetryResponse], dependencies=[Depends(require_permission("vitals:view"))])
def telemetry_timeline(elder_id: UUID, start: Optional[str] = None, end: Optional[str] = None, limit: int = Query(100, le=1000), db: Session = Depends(get_db), tenant_id: UUID = Depends(require_tenant_context)):
    repo = DeviceTelemetryRepository(db, tenant_id)
    # basic range filtering
    q = repo.db.execute(repo.db.select(repo.model).where(repo.model.elder_id == elder_id)).scalars()
    return q.all()[:limit]
