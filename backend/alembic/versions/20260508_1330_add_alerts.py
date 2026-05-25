"""Create alert tables

Revision ID: 20260508_1330_add_alerts
Revises: 20260508_1320_add_streams
Create Date: 2026-05-08 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_1330_add_alerts"
down_revision = "20260508_1320_add_streams"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("operator", sa.String(8), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default='0'),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default='60'),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default='true'),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_alert_rule_tenant_metric", "alert_rules", ["tenant_id", "metric_name"])

    op.create_table(
        "alert_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("telemetry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("alert_rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default='triggered'),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["alert_rule_id"], ["alert_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_alert_event_tenant_time", "alert_events", ["tenant_id", "triggered_at"])
    op.create_index("idx_alert_event_elder", "alert_events", ["tenant_id", "elder_id"])
    op.create_index("idx_alert_event_device", "alert_events", ["tenant_id", "device_id"])
    op.create_index("idx_alert_event_rule", "alert_events", ["alert_rule_id"])

    op.create_table(
        "alert_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("alert_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default='1'),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delivery_channel", sa.String(32), nullable=False),
        sa.Column("delivery_status", sa.String(32), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(["alert_event_id"], ["alert_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_alert_escalations_event_id", "alert_escalations", ["alert_event_id"])


def downgrade() -> None:
    op.drop_table("alert_escalations")
    op.drop_index("idx_alert_event_elder", "alert_events")
    op.drop_index("idx_alert_event_tenant_time", "alert_events")
    op.drop_table("alert_events")
    op.drop_index("idx_alert_rule_tenant_metric", "alert_rules")
    op.drop_table("alert_rules")
