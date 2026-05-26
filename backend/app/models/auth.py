from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    device_info: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    user = relationship("User", back_populates="sessions", foreign_keys=[user_id], lazy="selectin")
    tenant = relationship("Tenant", back_populates="user_sessions", foreign_keys=[tenant_id], lazy="selectin")
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="session",
        cascade="all, delete-orphan",
        foreign_keys="RefreshToken.session_id",
        lazy="selectin",
    )

    __table_args__ = ( 
        Index("idx_user_sessions_tenant_id", "tenant_id"),
        Index("idx_user_sessions_tenant_user_id", "tenant_id", "user_id"),
    )


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    # JWT jti stored as text to map to token presented by client
    jti: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    family_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    replaced_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    user = relationship("User", back_populates="refresh_tokens", foreign_keys=[user_id], lazy="selectin")
    session = relationship("UserSession", back_populates="refresh_tokens", foreign_keys=[session_id], lazy="selectin")
