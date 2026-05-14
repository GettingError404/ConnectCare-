from __future__ import annotations

from datetime import datetime, date
import enum
import uuid
from typing import Optional

from sqlalchemy import (
    String,
    ForeignKey,
    Index,
    Boolean,
    Integer,
    Date,
    DateTime,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Gender(enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class ElderStatus(enum.Enum):
    active = "active"
    inactive = "inactive"
    deceased = "deceased"


class CaregiverType(enum.Enum):
    professional = "professional"
    family = "family"
    volunteer = "volunteer"


class ConsultationMode(enum.Enum):
    in_person = "in_person"
    remote = "remote"
    hybrid = "hybrid"


class RiskLevel(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Elder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "elders"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organization_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    medical_record_number: Mapped[str] = mapped_column(String(128), nullable=False)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False)
    last_name: Mapped[str] = mapped_column(String(150), nullable=False)
    gender: Mapped[Optional[Gender]] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    blood_group: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preferred_language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[Optional[ElderStatus]] = mapped_column(String(20), nullable=False, server_default="active")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    medical_profile: Mapped[Optional["MedicalProfile"]] = relationship(
        back_populates="elder", uselist=False, cascade="all, delete-orphan"
    )
    health_preferences: Mapped[Optional["HealthPreferences"]] = relationship(
        back_populates="elder", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_elders_tenant_mrn", "tenant_id", "medical_record_number", unique=True),
    )


class Caregiver(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "caregivers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    caregiver_type: Mapped[CaregiverType] = mapped_column(String(30), nullable=False)
    specialization: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    availability_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class Doctor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "doctors"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False)
    license_number: Mapped[str] = mapped_column(String(128), nullable=False)
    years_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hospital_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    consultation_mode: Mapped[Optional[ConsultationMode]] = mapped_column(String(32), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __table_args__ = (
        Index("idx_doctors_tenant_license", "tenant_id", "license_number", unique=True),
    )


class FamilyMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "family_members"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    elder_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_primary_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    can_make_decisions: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class CareRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "care_relationships"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    elder_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, index=True)
    related_user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_role: Mapped[str] = mapped_column(String(64), nullable=False)
    permissions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class EmergencyContact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "emergency_contacts"

    elder_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    priority_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MedicalProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "medical_profiles"

    elder_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    allergies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    chronic_conditions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    medications: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    disabilities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    surgeries_history: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    insurance_provider: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    insurance_policy_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    primary_physician: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    elder: Mapped["Elder"] = relationship(back_populates="medical_profile")


class ConsentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "consent_records"

    elder_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_to_user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(128), nullable=False)
    granted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="granted")
    granted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    revoked_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, name="metadata")


class CarePlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "care_plans"

    elder_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    goals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    care_schedule: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[Optional[RiskLevel]] = mapped_column(String(32), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")


class HealthPreferences(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "health_preferences"

    elder_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    dietary_preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    activity_preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    communication_preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    emergency_preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sleep_preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    elder: Mapped["Elder"] = relationship(back_populates="health_preferences")
