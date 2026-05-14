import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.healthcare import Elder, MedicalProfile, EmergencyContact, CarePlan, Doctor
from app.repositories.healthcare import (
    ElderRepository,
    MedicalProfileRepository,
    EmergencyContactRepository,
    CarePlanRepository,
    DoctorRepository,
)

logger = logging.getLogger(__name__)


def _calculate_age(dob: date | None) -> int | None:
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class ElderService:
    def __init__(self, db: Session, tenant_id: UUID, actor_id: Optional[UUID] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = ElderRepository(db, tenant_id)
        self.mp_repo = MedicalProfileRepository(db, tenant_id)
        self.actor_id = actor_id

    def create_elder(self, payload) -> Elder:
        # age validation
        age = _calculate_age(payload.date_of_birth)
        if age is not None and (age < 0 or age > 150):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_of_birth")

        # ensure MRN uniqueness per tenant
        if self.repo.get_by_medical_record_number(payload.medical_record_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="medical_record_number already exists")

        elder = Elder(
            tenant_id=self.tenant_id,
            organization_id=getattr(payload, "organization_id", None),
            organization_unit_id=getattr(payload, "organization_unit_id", None),
            medical_record_number=payload.medical_record_number,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
        )

        try:
            self.db.add(elder)
            self.db.commit()
            self.db.refresh(elder)

            # auto-create medical profile
            mp = MedicalProfile(elder_id=elder.id)
            try:
                self.db.add(mp)
                self.db.commit()
            except Exception:
                self.db.rollback()

            logger.info("elder.created", extra={"elder_id": str(elder.id), "actor": str(self.actor_id) if self.actor_id else None})
            return elder
        except IntegrityError as exc:
            self.db.rollback()
            logger.warning("Failed to create elder: %s", exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid elder payload")
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.exception("Database error creating elder: %s", exc)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")

    def get(self, elder_id: UUID) -> Optional[Elder]:
        return self.repo.get_by_id(elder_id)

    def update(self, elder_id: UUID, data) -> Optional[Elder]:
        elder = self.repo.get_by_id(elder_id)
        if not elder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Elder not found")

        # validate dob if provided
        if getattr(data, "date_of_birth", None):
            age = _calculate_age(data.date_of_birth)
            if age is not None and (age < 0 or age > 150):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_of_birth")

        updated = self.repo.update(elder_id, data.__dict__)
        logger.info("elder.updated", extra={"elder_id": str(elder_id), "actor": str(self.actor_id) if self.actor_id else None})
        return updated


class EmergencyContactService:
    def __init__(self, db: Session, tenant_id: UUID, actor_id: Optional[UUID] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = EmergencyContactRepository(db, tenant_id)
        self.actor_id = actor_id

    def create(self, elder_id, payload):
        # ensure only one primary per elder
        if payload.is_primary:
            existing = self.repo.get_primary_for_elder(elder_id)
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Primary emergency contact already exists")

        contact = self.repo.add(
            type(self.repo.model)(
                elder_id=elder_id,
                name=payload.name,
                relationship=payload.relationship,
                phone_number=payload.phone_number,
                email=payload.email,
                priority_order=payload.priority_order,
                is_primary=payload.is_primary,
                address=getattr(payload, "address", None),
            )
        )
        logger.info("emergency_contact.created", extra={"elder_id": str(elder_id), "actor": str(self.actor_id) if self.actor_id else None})
        return contact


class DoctorService:
    def __init__(self, db: Session, tenant_id: UUID, actor_id: Optional[UUID] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = DoctorRepository(db, tenant_id)
        self.actor_id = actor_id

    def create(self, payload):
        # license uniqueness per tenant
        if self.repo.get_by_license(payload.license_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Doctor license already exists")

        doc = self.repo.add(type(self.repo.model)(
            tenant_id=self.tenant_id,
            user_id=payload.user_id,
            specialization=payload.specialization,
            license_number=payload.license_number,
            years_experience=getattr(payload, "years_experience", None),
            hospital_name=getattr(payload, "hospital_name", None),
            consultation_mode=getattr(payload, "consultation_mode", None),
            is_verified=getattr(payload, "is_verified", False),
        ))

        logger.info("doctor.created", extra={"doctor_id": str(doc.id), "actor": str(self.actor_id) if self.actor_id else None})
        return doc


class CarePlanService:
    def __init__(self, db: Session, tenant_id: UUID, actor_id: Optional[UUID] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = CarePlanRepository(db, tenant_id)
        self.actor_id = actor_id

    def create(self, elder_id, payload):
        # prevent overlapping active care plans for same elder and time window
        existing = self.repo.active_plans_for_elder(elder_id)
        for p in existing:
            if p.start_date and payload.start_date and p.end_date is None or payload.end_date is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Overlapping care plan exists")

        cp = self.repo.add(type(self.repo.model)(
            elder_id=elder_id,
            created_by=self.actor_id,
            title=payload.title,
            description=payload.description,
            goals=getattr(payload, "goals", None),
            care_schedule=getattr(payload, "care_schedule", None),
            risk_level=getattr(payload, "risk_level", None),
            start_date=getattr(payload, "start_date", None),
            end_date=getattr(payload, "end_date", None),
        ))
        logger.info("careplan.created", extra={"careplan_id": str(cp.id), "elder_id": str(elder_id), "actor": str(self.actor_id) if self.actor_id else None})
        return cp
