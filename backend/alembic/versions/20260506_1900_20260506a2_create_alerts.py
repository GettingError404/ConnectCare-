"""create alerts

Revision ID: 20260506a2
Revises: 20260506a1
Create Date: 2026-05-06 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260506a2"
down_revision: Union[str, Sequence[str], None] = "20260506a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("vital_id", sa.UUID(), nullable=False),
        sa.Column("vital_recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["vital_id", "vital_recorded_at"],
            ["health_vitals.id", "health_vitals.recorded_at"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "vital_id",
            "vital_recorded_at",
            "alert_type",
            name="uq_alerts_user_vital_recorded_at_type",
        ),
    )
    op.create_index(op.f("ix_alerts_user_id"), "alerts", ["user_id"], unique=False)
    op.create_index(op.f("ix_alerts_vital_id"), "alerts", ["vital_id"], unique=False)
    op.create_index(op.f("ix_alerts_vital_recorded_at"), "alerts", ["vital_recorded_at"], unique=False)
    op.create_index(op.f("ix_alerts_alert_type"), "alerts", ["alert_type"], unique=False)
    op.create_index(op.f("ix_alerts_severity"), "alerts", ["severity"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_severity"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_alert_type"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_vital_recorded_at"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_vital_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_user_id"), table_name="alerts")
    op.drop_table("alerts")
