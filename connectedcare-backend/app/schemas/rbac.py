"""
Pydantic schemas for RBAC and permission management.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)
    parent_role_id: Optional[UUID] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if value != value.lower():
            raise ValueError("slug must be lowercase")
        return value


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)
    parent_role_id: Optional[UUID] = None
    is_active: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value != value.lower():
            raise ValueError("slug must be lowercase")
        return value


class RoleResponse(BaseModel):
    id: UUID
    tenant_id: Optional[UUID]
    parent_role_id: Optional[UUID]
    name: str
    slug: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PermissionResponse(BaseModel):
    id: UUID
    resource: str
    action: str
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @property
    def key(self) -> str:
        return f"{self.resource}:{self.action}"


class AssignRoleRequest(BaseModel):
    user_id: UUID
    role_id: UUID
    organization_id: Optional[UUID] = None
    organization_unit_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None


class UserRoleResponse(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    organization_id: Optional[UUID]
    organization_unit_id: Optional[UUID]
    assigned_by: Optional[UUID]
    assigned_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)
