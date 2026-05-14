from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=150)


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str = Field(validation_alias="full_name")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
