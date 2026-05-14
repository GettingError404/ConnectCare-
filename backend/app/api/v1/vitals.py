from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.health_vitals import HealthVital
from app.schemas.health_vitals import (
    HealthVitalBatchCreate,
    HealthVitalCreate,
    HealthVitalResponse,
    MetricType,
)
from app.services.vitals_service import (
    create_vital as create_vital_service,
    create_vitals_batch as create_vitals_batch_service,
    get_latest_vitals as get_latest_vitals_service,
    get_user_vitals as get_user_vitals_service,
)
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/vitals", tags=["Vitals"])


@router.post("", response_model=HealthVitalResponse, status_code=status.HTTP_201_CREATED)
def create_vital(payload: HealthVitalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> HealthVital:
    # enforce current authenticated user as the record owner
    payload = payload.model_copy(update={"user_id": current_user.id})
    return create_vital_service(db=db, payload=payload)


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def create_vitals_batch(payload: HealthVitalBatchCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, int]:
    # override any provided user_ids to current user for security
    updated = [item.model_copy(update={"user_id": current_user.id}) for item in payload.root]
    from app.schemas.health_vitals import HealthVitalBatchCreate as HBC
    return create_vitals_batch_service(db=db, payload=HBC(root=updated))


@router.get("/{user_id}", response_model=list[HealthVitalResponse])
def get_user_vitals(
    user_id: UUID,
    metric_type: MetricType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HealthVital]:
    # only allow fetching for the authenticated user
    if str(current_user.id) != str(user_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return get_user_vitals_service(db=db, user_id=user_id, metric_type=metric_type, limit=limit)


@router.get("/{user_id}/latest", response_model=list[HealthVitalResponse])
def get_latest_vitals_per_metric(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[HealthVital]:
    if str(current_user.id) != str(user_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return get_latest_vitals_service(db=db, user_id=user_id)
