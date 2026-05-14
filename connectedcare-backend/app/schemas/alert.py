from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertResponse(BaseModel):
    id: UUID
    user_id: UUID
    vital_id: UUID
    alert_type: str
    severity: AlertSeverity
    message: str
    created_at: datetime
    is_resolved: bool

    model_config = ConfigDict(from_attributes=True)
