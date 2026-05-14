from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict
from uuid import UUID
from pydantic import BaseModel, Field


class VitalStreamEventCreate(BaseModel):
    event_id: str
    event_timestamp: datetime
    tenant_id: UUID
    elder_id: Optional[UUID]
    device_id: Optional[UUID]
    payload: Dict


class VitalStreamEventResponse(BaseModel):
    id: UUID
    event_id: str
    event_timestamp: datetime
    ingestion_timestamp: datetime
    processing_status: str

    model_config = dict(from_attributes=True)


class DeviceTelemetryCreate(BaseModel):
    recorded_at: datetime
    tenant_id: UUID
    elder_id: Optional[UUID]
    device_id: Optional[UUID]
    heart_rate: Optional[float]
    spo2: Optional[float]
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    respiratory_rate: Optional[float]
    glucose_level: Optional[float]
    body_temperature: Optional[float]
    ecg_signal: Optional[dict]
    battery_level: Optional[int]
    signal_strength: Optional[int]
    fall_detected: Optional[bool]


class DeviceTelemetryResponse(BaseModel):
    id: UUID
    recorded_at: datetime
    heart_rate: Optional[float]
    spo2: Optional[float]

    model_config = dict(from_attributes=True)
