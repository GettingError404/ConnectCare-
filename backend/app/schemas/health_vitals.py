from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


class MetricType(str, Enum):
    steps = "steps"
    heart_rate = "heart_rate"
    sleep = "sleep"
    calories = "calories"
    spo2 = "spo2"
    respiratory_rate = "respiratory_rate"
    body_temperature = "body_temperature"


class HealthVitalCreate(BaseModel):
    user_id: UUID
    device_id: UUID
    metric_type: MetricType
    value: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=20)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def validate_recorded_at_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("recorded_at must be timezone-aware")
        return value


class HealthVitalResponse(BaseModel):
    id: UUID
    user_id: UUID
    device_id: UUID
    metric_type: MetricType
    value: float
    unit: str
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthVitalBatchCreate(RootModel[list[HealthVitalCreate]]):
    pass
