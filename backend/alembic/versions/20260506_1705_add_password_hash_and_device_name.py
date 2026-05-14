"""add password_hash and device_name

Revision ID: 20260506a1
Revises: 10911737759d
Create Date: 2026-05-06 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260506a1"
down_revision: Union[str, Sequence[str], None] = "10911737759d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=False))
    op.add_column("devices", sa.Column("device_name", sa.String(length=128), nullable=False))


def downgrade() -> None:
    op.drop_column("devices", "device_name")
    op.drop_column("users", "password_hash")