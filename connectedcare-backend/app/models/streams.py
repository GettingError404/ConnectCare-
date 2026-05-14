from __future__ import annotations

from datetime import datetime
import enum
import uuid
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class ProcessingStatus(enum.Enum):
    pending = "pending"
    validated = "validated"
    persisted = "persisted"
    failed = "failed"


class VitalStreamEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vital_stream_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    elder_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id"), nullable=True, index=True)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("devices.id"), nullable=True, index=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ingestion_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    processing_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=False, server_default="pending")
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    raw_payload: Mapped[Optional[str]] = mapped_column(String())


class DeviceTelemetry(TimestampMixin, Base):
    __tablename__ = "device_telemetry"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    elder_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)

    heart_rate: Mapped[Optional[float]] = mapped_column(nullable=True)
    spo2: Mapped[Optional[float]] = mapped_column(nullable=True)
    systolic_bp: Mapped[Optional[int]] = mapped_column(nullable=True)
    diastolic_bp: Mapped[Optional[int]] = mapped_column(nullable=True)
    respiratory_rate: Mapped[Optional[float]] = mapped_column(nullable=True)
    glucose_level: Mapped[Optional[float]] = mapped_column(nullable=True)
    ecg_signal: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    body_temperature: Mapped[Optional[float]] = mapped_column(nullable=True)
    battery_level: Mapped[Optional[int]] = mapped_column(nullable=True)
    signal_strength: Mapped[Optional[int]] = mapped_column(nullable=True)
    fall_detected: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    stress_level: Mapped[Optional[float]] = mapped_column(nullable=True)
    sleep_quality: Mapped[Optional[float]] = mapped_column(nullable=True)


class VitalAnomaly(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vital_anomalies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    elder_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id"), nullable=True, index=True)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("devices.id"), nullable=True, index=True)
    anomaly_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    detected_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    expected_range: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    detection_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class VitalThreshold(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vital_thresholds"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    elder_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("elders.id"), nullable=True, index=True)
    min_heart_rate: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_heart_rate: Mapped[Optional[float]] = mapped_column(nullable=True)
    min_spo2: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_spo2: Mapped[Optional[float]] = mapped_column(nullable=True)
    min_glucose: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_glucose: Mapped[Optional[float]] = mapped_column(nullable=True)
    min_temp: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_temp: Mapped[Optional[float]] = mapped_column(nullable=True)


class DeviceHeartbeat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_heartbeats"

    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    device_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("devices.id"), nullable=False, index=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    battery_level: Mapped[Optional[int]] = mapped_column(nullable=True)
    signal_strength: Mapped[Optional[int]] = mapped_column(nullable=True)


class IngestionFailureLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingestion_failure_logs"

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    event_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
