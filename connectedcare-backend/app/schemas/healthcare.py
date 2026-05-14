from __future__ import annotations

from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ElderCreate(BaseModel):
    medical_record_number: str = Field(..., min_length=1, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=150)
    last_name: str = Field(..., min_length=1, max_length=150)
    date_of_birth: Optional[date]
    gender: Optional[str]
    blood_group: Optional[str]
    height_cm: Optional[int]
    weight_kg: Optional[int]
    organization_id: Optional[UUID]
    organization_unit_id: Optional[UUID]


class ElderUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    blood_group: Optional[str]
    height_cm: Optional[int]
    weight_kg: Optional[int]
    profile_photo_url: Optional[str]
    preferred_language: Optional[str]
    timezone: Optional[str]
    onboarding_completed: Optional[bool]


class ElderResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    medical_record_number: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MedicalProfileCreate(BaseModel):
    allergies: Optional[dict]
    chronic_conditions: Optional[dict]
    medications: Optional[dict]
    disabilities: Optional[dict]
    surgeries_history: Optional[dict]
    insurance_provider: Optional[str]
    insurance_policy_number: Optional[str]
    primary_physician: Optional[str]
    notes: Optional[str]


class MedicalProfileResponse(BaseModel):
    id: UUID
    elder_id: UUID
    allergies: Optional[dict]
    chronic_conditions: Optional[dict]
    medications: Optional[dict]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmergencyContactCreate(BaseModel):
    name: str
    relationship: str
    phone_number: str
    email: Optional[str]
    priority_order: Optional[int]
    is_primary: Optional[bool] = False


class EmergencyContactResponse(BaseModel):
    id: UUID
    elder_id: UUID
    name: str
    relationship: str
    phone_number: str
    email: Optional[str]
    is_primary: bool
    priority_order: Optional[int]

    class Config:
        from_attributes = True


class CarePlanCreate(BaseModel):
    title: str
    description: Optional[str]
    goals: Optional[dict]
    care_schedule: Optional[dict]
    risk_level: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]


class CarePlanResponse(BaseModel):
    id: UUID
    elder_id: UUID
    created_by: UUID
    title: str
    description: Optional[str]
    is_active: bool
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True
