"""Add streaming tables

Revision ID: 20260508_1320_add_streams
Revises: 20260508_1310_update_devices
Create Date: 2026-05-08 13:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_1320_add_streams"
down_revision = "20260508_1310_update_devices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vital_stream_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingestion_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_topic", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("processing_status", sa.String(32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_vse_tenant_id", "vital_stream_events", ["tenant_id"])
    op.create_index("idx_vse_elder_id", "vital_stream_events", ["elder_id"])
    op.create_index("idx_vse_device_id", "vital_stream_events", ["device_id"])
    op.create_index("idx_vse_event_timestamp", "vital_stream_events", ["event_timestamp"])
    op.create_index("idx_vse_checksum", "vital_stream_events", ["checksum"])

    op.create_table(
        "device_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heart_rate", sa.Float(), nullable=True),
        sa.Column("spo2", sa.Float(), nullable=True),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Float(), nullable=True),
        sa.Column("glucose_level", sa.Float(), nullable=True),
        sa.Column("ecg_signal", postgresql.JSONB, nullable=True),
        sa.Column("body_temperature", sa.Float(), nullable=True),
        sa.Column("battery_level", sa.Integer(), nullable=True),
        sa.Column("signal_strength", sa.Integer(), nullable=True),
        sa.Column("fall_detected", sa.Boolean(), nullable=True),
        sa.Column("stress_level", sa.Float(), nullable=True),
        sa.Column("sleep_quality", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id", "recorded_at"),
    )
    op.create_index("idx_dt_tenant_id", "device_telemetry", ["tenant_id"])
    op.create_index("idx_dt_elder_id", "device_telemetry", ["elder_id"])
    op.create_index("idx_dt_device_id", "device_telemetry", ["device_id"])
    op.create_index("idx_dt_recorded_at", "device_telemetry", ["recorded_at"])

    op.execute(
        "SELECT create_hypertable('device_telemetry', 'recorded_at', if_not_exists => TRUE, migrate_data => TRUE, create_default_indexes => FALSE);"
    )

    op.create_table(
        "vital_anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("anomaly_type", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("detected_value", sa.Float(), nullable=True),
        sa.Column("expected_range", postgresql.JSONB, nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("detection_source", sa.String(64), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_va_tenant_id", "vital_anomalies", ["tenant_id"])
    op.create_index("idx_va_elder_id", "vital_anomalies", ["elder_id"])
    op.create_index("idx_va_device_id", "vital_anomalies", ["device_id"])

    op.create_table(
        "vital_thresholds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("min_heart_rate", sa.Float(), nullable=True),
        sa.Column("max_heart_rate", sa.Float(), nullable=True),
        sa.Column("min_spo2", sa.Float(), nullable=True),
        sa.Column("max_spo2", sa.Float(), nullable=True),
        sa.Column("min_glucose", sa.Float(), nullable=True),
        sa.Column("max_glucose", sa.Float(), nullable=True),
        sa.Column("min_temp", sa.Float(), nullable=True),
        sa.Column("max_temp", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_vt_tenant_id", "vital_thresholds", ["tenant_id"])
    op.create_index("idx_vt_elder_id", "vital_thresholds", ["elder_id"])

    op.create_table(
        "device_heartbeats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("battery_level", sa.Integer(), nullable=True),
        sa.Column("signal_strength", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dh_tenant_id", "device_heartbeats", ["tenant_id"])
    op.create_index("idx_dh_device_id", "device_heartbeats", ["device_id"])

    op.create_table(
        "ingestion_failure_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_id", sa.String(128), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ifl_tenant_id", "ingestion_failure_logs", ["tenant_id"])
    op.create_index("idx_ifl_device_id", "ingestion_failure_logs", ["device_id"])


def downgrade() -> None:
    op.drop_index("idx_ifl_device_id", table_name="ingestion_failure_logs", if_exists=True)
    op.drop_index("idx_ifl_tenant_id", table_name="ingestion_failure_logs", if_exists=True)
    op.drop_table("ingestion_failure_logs")

    op.drop_index("idx_dh_device_id", table_name="device_heartbeats", if_exists=True)
    op.drop_index("idx_dh_tenant_id", table_name="device_heartbeats", if_exists=True)
    op.drop_table("device_heartbeats")

    op.drop_index("idx_vt_elder_id", table_name="vital_thresholds", if_exists=True)
    op.drop_index("idx_vt_tenant_id", table_name="vital_thresholds", if_exists=True)
    op.drop_table("vital_thresholds")

    op.drop_index("idx_va_device_id", table_name="vital_anomalies", if_exists=True)
    op.drop_index("idx_va_elder_id", table_name="vital_anomalies", if_exists=True)
    op.drop_index("idx_va_tenant_id", table_name="vital_anomalies", if_exists=True)
    op.drop_table("vital_anomalies")

    op.drop_index("idx_dt_recorded_at", table_name="device_telemetry", if_exists=True)
    op.drop_index("idx_dt_device_id", table_name="device_telemetry", if_exists=True)
    op.drop_index("idx_dt_elder_id", table_name="device_telemetry", if_exists=True)
    op.drop_index("idx_dt_tenant_id", table_name="device_telemetry", if_exists=True)
    op.drop_table("device_telemetry")

    op.drop_index("idx_vse_checksum", table_name="vital_stream_events", if_exists=True)
    op.drop_index("idx_vse_event_timestamp", table_name="vital_stream_events", if_exists=True)
    op.drop_index("idx_vse_device_id", table_name="vital_stream_events", if_exists=True)
    op.drop_index("idx_vse_elder_id", table_name="vital_stream_events", if_exists=True)
    op.drop_index("idx_vse_tenant_id", table_name="vital_stream_events", if_exists=True)
    op.drop_table("vital_stream_events")
