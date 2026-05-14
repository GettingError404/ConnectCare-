from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, validator


class Operator(str, Enum):
    gt = ">"
    gte = ">="
    lt = "<"
    lte = "<="
    eq = "=="


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DeliveryChannel(str, Enum):
    websocket = "websocket"
    email = "email"
    sms = "sms"
    push = "push"


class AlertRuleCreate(BaseModel):
    name: str
    description: Optional[str]
    metric_name: str
    operator: Operator
    threshold_value: float
    severity: Severity
    duration_seconds: int = 0
    cooldown_seconds: int = 60
    enabled: bool = True

    model_config = ConfigDict()

    @validator("duration_seconds", "cooldown_seconds")
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("must be non-negative")
        return v


class AlertRuleUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    operator: Optional[Operator]
    threshold_value: Optional[float]
    severity: Optional[Severity]
    duration_seconds: Optional[int]
    cooldown_seconds: Optional[int]
    enabled: Optional[bool]

    model_config = ConfigDict()


class AlertRuleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    metric_name: str
    operator: Operator
    threshold_value: float
    severity: Severity
    duration_seconds: int
    cooldown_seconds: int
    enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertEventResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    elder_id: Optional[UUID]
    device_id: Optional[UUID]
    telemetry_id: Optional[UUID]
    alert_rule_id: Optional[UUID]
    metric_name: str
    metric_value: Optional[float]
    severity: Severity
    status: str
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    metadata: Optional[dict]

    model_config = ConfigDict(from_attributes=True)
