from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.dependencies.authorization import require_permission
from app.middleware.tenant_context import require_tenant_context
from app.schemas.healthcare import (
    ElderCreate,
    ElderResponse,
    ElderUpdate,
    MedicalProfileResponse,
    MedicalProfileCreate,
    EmergencyContactCreate,
    EmergencyContactResponse,
    CarePlanCreate,
    CarePlanResponse,
)
from app.services.healthcare import ElderService, EmergencyContactService, CarePlanService

router = APIRouter(prefix="/healthcare", tags=["Healthcare"])


@router.post("/elders", response_model=ElderResponse, dependencies=[Depends(require_permission("elders:create"))])
def create_elder(payload: ElderCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user), tenant_id: UUID = Depends(require_tenant_context)):
    svc = ElderService(db, tenant_id, actor_id=current_user.id)
    elder = svc.create_elder(payload)
    return elder


@router.get("/elders/{elder_id}", response_model=ElderResponse, dependencies=[Depends(require_permission("elders:view"))])
def get_elder(elder_id: UUID, db: Session = Depends(get_db), tenant_id: UUID = Depends(require_tenant_context)):
    svc = ElderService(db, tenant_id)
    elder = svc.get(elder_id)
    if not elder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Elder not found")
    return elder


@router.put("/elders/{elder_id}", response_model=ElderResponse, dependencies=[Depends(require_permission("elders:update"))])
def update_elder(elder_id: UUID, payload: ElderUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user), tenant_id: UUID = Depends(require_tenant_context)):
    svc = ElderService(db, tenant_id, actor_id=current_user.id)
    updated = svc.update(elder_id, payload)
    return updated


@router.post("/elders/{elder_id}/emergency-contacts", response_model=EmergencyContactResponse, dependencies=[Depends(require_permission("elders:update"))])
def add_emergency_contact(elder_id: UUID, payload: EmergencyContactCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user), tenant_id: UUID = Depends(require_tenant_context)):
    svc = EmergencyContactService(db, tenant_id, actor_id=current_user.id)
    contact = svc.create(elder_id, payload)
    return contact


@router.post("/elders/{elder_id}/care-plans", response_model=CarePlanResponse, dependencies=[Depends(require_permission("careplans:manage"))])
def create_care_plan(elder_id: UUID, payload: CarePlanCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user), tenant_id: UUID = Depends(require_tenant_context)):
    svc = CarePlanService(db, tenant_id, actor_id=current_user.id)
    cp = svc.create(elder_id, payload)
    return cp


@router.get("/elders/{elder_id}/medical-profile", response_model=MedicalProfileResponse, dependencies=[Depends(require_permission("medical:read"))])
def get_medical_profile(elder_id: UUID, db: Session = Depends(get_db), tenant_id: UUID = Depends(require_tenant_context)):
    mp_repo = ElderService(db, tenant_id).mp_repo
    mp = mp_repo.get_by_elder(elder_id)
    if not mp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical profile not found")
    return mp


@router.put("/elders/{elder_id}/medical-profile", response_model=MedicalProfileResponse, dependencies=[Depends(require_permission("medical:update"))])
def update_medical_profile(elder_id: UUID, payload: MedicalProfileCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user), tenant_id: UUID = Depends(require_tenant_context)):
    svc = ElderService(db, tenant_id, actor_id=current_user.id)
    mp = svc.mp_repo.get_by_elder(elder_id)
    if not mp:
        # create
        mp = svc.mp_repo.add(type(svc.mp_repo.model)(elder_id=elder_id, **payload.model_dump()))
    else:
        svc.mp_repo.update(mp.id, payload.model_dump())
    return svc.mp_repo.get_by_elder(elder_id)
