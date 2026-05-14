from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeviceType(str, Enum):
    mobile = "mobile"
    wearable = "wearable"


class DeviceCategory(str, Enum):
    smartwatch = "smartwatch"
    pulse_oximeter = "pulse_oximeter"
    bp_monitor = "bp_monitor"
    glucose_monitor = "glucose_monitor"
    ecg_monitor = "ecg_monitor"
    fall_detector = "fall_detector"
    medication_dispenser = "medication_dispenser"
    smart_speaker = "smart_speaker"


class DeviceRegister(BaseModel):
    device_name: str = Field(min_length=1, max_length=128)
    device_type: DeviceType
    device_category: DeviceCategory | None = None
    device_identifier: str | None = Field(default=None, max_length=128)
    serial_number: str | None = Field(default=None, max_length=128)
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=64)
    elder_id: UUID | None = None
    assigned_caregiver_id: UUID | None = None
    organization_id: UUID | None = None


class DeviceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    device_name: str
    device_type: DeviceType
    device_category: DeviceCategory | None = None
    device_identifier: str | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    firmware_version: str | None = None
    battery_level: int | None = None
    signal_strength: int | None = None
    last_seen_at: datetime | None = None
    device_status: str | None = None
    connectivity_status: str | None = None
    mqtt_client_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
