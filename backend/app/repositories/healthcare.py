from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session

from app.repositories.tenant import TenantAwareRepository
from app.models.healthcare import (
    Elder,
    MedicalProfile,
    EmergencyContact,
    CarePlan,
    Doctor,
)


class ElderRepository(TenantAwareRepository[Elder]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, Elder, tenant_id)

    def get_by_medical_record_number(self, mrn: str) -> Optional[Elder]:
        return self.db.execute(
            select(Elder).where(and_(Elder.tenant_id == self.tenant_id, Elder.medical_record_number == mrn))
        ).scalar_one_or_none()

    def search(self, query: Optional[str], skip: int = 0, limit: int = 50) -> List[Elder]:
        q = select(Elder).where(Elder.tenant_id == self.tenant_id)
        if query:
            ilike = f"%{query}%"
            q = q.where(or_(Elder.first_name.ilike(ilike), Elder.last_name.ilike(ilike), Elder.medical_record_number.ilike(ilike)))
        q = q.offset(skip).limit(limit)
        return self.db.execute(q).scalars().all()


class MedicalProfileRepository(TenantAwareRepository[MedicalProfile]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, MedicalProfile, tenant_id)

    def get_by_elder(self, elder_id: UUID) -> Optional[MedicalProfile]:
        return self.db.execute(select(MedicalProfile).where(MedicalProfile.elder_id == elder_id)).scalar_one_or_none()


class EmergencyContactRepository(TenantAwareRepository[EmergencyContact]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, EmergencyContact, tenant_id)

    def get_primary_for_elder(self, elder_id: UUID) -> Optional[EmergencyContact]:
        return self.db.execute(
            select(EmergencyContact).where(and_(EmergencyContact.elder_id == elder_id, EmergencyContact.is_primary.is_(True)))
        ).scalar_one_or_none()


class CarePlanRepository(TenantAwareRepository[CarePlan]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, CarePlan, tenant_id)

    def active_plans_for_elder(self, elder_id: UUID):
        return self.db.execute(
            select(CarePlan).where(and_(CarePlan.elder_id == elder_id, CarePlan.is_active.is_(True)))
        ).scalars().all()


class DoctorRepository(TenantAwareRepository[Doctor]):
    def __init__(self, db: Session, tenant_id: UUID):
        super().__init__(db, Doctor, tenant_id)

    def get_by_license(self, license_number: str) -> Optional[Doctor]:
        return self.db.execute(
            select(Doctor).where(and_(Doctor.tenant_id == self.tenant_id, Doctor.license_number == license_number))
        ).scalar_one_or_none()
