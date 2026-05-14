"""Update devices table with metadata, ownership, and auth fields

Revision ID: 20260508_1310_update_devices
Revises: 20260506_1705_add_password_hash_and_device_name
Create Date: 2026-05-08 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_1310_update_devices"
down_revision = "20260508_1300_healthcare"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add tenant and ownership columns
    op.add_column("devices", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("devices", sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("devices", sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("devices", sa.Column("assigned_caregiver_id", postgresql.UUID(as_uuid=True), nullable=True))

    # identity & metadata
    op.add_column("devices", sa.Column("serial_number", sa.String(128), nullable=True))
    op.add_column("devices", sa.Column("device_category", sa.String(64), nullable=True))
    op.add_column("devices", sa.Column("firmware_version", sa.String(64), nullable=True))
    op.add_column("devices", sa.Column("battery_level", sa.Integer(), nullable=True))
    op.add_column("devices", sa.Column("signal_strength", sa.Integer(), nullable=True))
    op.add_column("devices", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("device_status", sa.String(32), nullable=True))
    op.add_column("devices", sa.Column("connectivity_status", sa.String(32), nullable=True))

    # authentication
    op.add_column("devices", sa.Column("device_api_key", sa.String(255), nullable=True))
    op.add_column("devices", sa.Column("certificate_fingerprint", sa.String(255), nullable=True))
    op.add_column("devices", sa.Column("mqtt_client_id", sa.String(255), nullable=True))
    op.add_column("devices", sa.Column("extra", postgresql.JSONB, nullable=True))

    # indexes and FKs
    op.create_index("idx_devices_tenant_id", "devices", ["tenant_id"])
    op.create_index("idx_devices_elder_id", "devices", ["elder_id"])
    op.create_index("idx_devices_last_seen_at", "devices", ["last_seen_at"])

    op.create_foreign_key("fk_devices_tenant", "devices", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_devices_organization", "devices", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_devices_elder", "devices", "elders", ["elder_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_devices_caregiver", "devices", "caregivers", ["assigned_caregiver_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_devices_caregiver", "devices", type_="foreignkey")
    op.drop_constraint("fk_devices_elder", "devices", type_="foreignkey")
    op.drop_constraint("fk_devices_organization", "devices", type_="foreignkey")
    op.drop_constraint("fk_devices_tenant", "devices", type_="foreignkey")

    op.drop_index("idx_devices_last_seen_at", table_name="devices")
    op.drop_index("idx_devices_elder_id", table_name="devices")
    op.drop_index("idx_devices_tenant_id", table_name="devices")

    op.drop_column("devices", "extra")
    op.drop_column("devices", "mqtt_client_id")
    op.drop_column("devices", "certificate_fingerprint")
    op.drop_column("devices", "device_api_key")
    op.drop_column("devices", "connectivity_status")
    op.drop_column("devices", "device_status")
    op.drop_column("devices", "last_seen_at")
    op.drop_column("devices", "signal_strength")
    op.drop_column("devices", "battery_level")
    op.drop_column("devices", "firmware_version")
    op.drop_column("devices", "device_category")
    op.drop_column("devices", "serial_number")
    op.drop_column("devices", "assigned_caregiver_id")
    op.drop_column("devices", "elder_id")
    op.drop_column("devices", "organization_id")
    op.drop_column("devices", "tenant_id")
