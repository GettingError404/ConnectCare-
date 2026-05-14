"""
Pydantic schemas for tenant and organization domain.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ============= Tenant Schemas =============

class TenantCreate(BaseModel):
    """Schema for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v):
        """Ensure slug is lowercase and contains only alphanumeric and hyphens."""
        if not v.islower():
            raise ValueError("slug must be lowercase")
        return v


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Schema for tenant responses."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantDetailResponse(TenantResponse):
    """Detailed tenant response including metadata."""

    is_soft_deleted: bool


# ============= Organization Schemas =============

class OrganizationCreate(BaseModel):
    """Schema for creating a new organization."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v):
        """Ensure slug is lowercase."""
        if not v.islower():
            raise ValueError("slug must be lowercase")
        return v


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    """Schema for organization responses."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationDetailResponse(OrganizationResponse):
    """Detailed organization response."""

    is_soft_deleted: bool


# ============= Organization Unit Schemas =============

class OrganizationUnitCreate(BaseModel):
    """Schema for creating a new organization unit."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    parent_id: Optional[UUID] = None


class OrganizationUnitUpdate(BaseModel):
    """Schema for updating an organization unit."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    parent_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class OrganizationUnitResponse(BaseModel):
    """Schema for organization unit responses."""

    id: UUID
    organization_id: UUID
    parent_id: Optional[UUID]
    name: str
    description: Optional[str]
    level: int
    is_active: bool
    is_root: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationUnitDetailResponse(OrganizationUnitResponse):
    """Detailed organization unit response."""

    is_soft_deleted: bool


class OrganizationUnitTreeResponse(BaseModel):
    """Organization unit with children (for tree view)."""

    id: UUID
    name: str
    description: Optional[str]
    level: int
    is_active: bool
    children: list["OrganizationUnitTreeResponse"] = []

    class Config:
        from_attributes = True


# Update forward references
OrganizationUnitTreeResponse.model_rebuild()
