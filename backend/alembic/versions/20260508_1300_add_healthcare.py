"""Add healthcare domain tables (elders, caregivers, doctors, family, care relationships, medical, consents, care plans, preferences)

Revision ID: 20260508_1300_healthcare
Revises: 20260508_1210_rbac_seed
Create Date: 2026-05-08 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260508_1300_healthcare"
down_revision = "20260508_1210_rbac_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "elders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("medical_record_number", sa.String(128), nullable=False),
        sa.Column("first_name", sa.String(150), nullable=False),
        sa.Column("last_name", sa.String(150), nullable=False),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("blood_group", sa.String(10), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Integer(), nullable=True),
        sa.Column("profile_photo_url", sa.String(500), nullable=True),
        sa.Column("preferred_language", sa.String(50), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_unit_id"], ["organization_units.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_elders_tenant_mrn", "elders", ["tenant_id", "medical_record_number"], unique=True)
    op.create_index("idx_elders_organization_unit_id", "elders", ["organization_unit_id"])
    op.create_index("idx_elders_user_id", "elders", ["user_id"])
    op.create_index("idx_elders_deleted_at", "elders", ["deleted_at"])

    op.create_table(
        "caregivers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("caregiver_type", sa.String(30), nullable=False),
        sa.Column("specialization", sa.String(255), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("availability_status", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_caregivers_user_id", "caregivers", ["user_id"])

    op.create_table(
        "doctors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialization", sa.String(255), nullable=False),
        sa.Column("license_number", sa.String(128), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("hospital_name", sa.String(255), nullable=True),
        sa.Column("consultation_mode", sa.String(32), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_doctors_tenant_license", "doctors", ["tenant_id", "license_number"], unique=True)
    op.create_index("idx_doctors_user_id", "doctors", ["user_id"])

    op.create_table(
        "family_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(64), nullable=False),
        sa.Column("is_primary_contact", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("can_make_decisions", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_family_members_user_id", "family_members", ["user_id"])

    op.create_table(
        "care_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_role", sa.String(64), nullable=False),
        sa.Column("permissions", postgresql.JSONB, nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_care_relationships_related_user_id", "care_relationships", ["related_user_id"])

    op.create_table(
        "emergency_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("relationship", sa.String(64), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("priority_order", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("address", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "medical_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allergies", postgresql.JSONB, nullable=True),
        sa.Column("chronic_conditions", postgresql.JSONB, nullable=True),
        sa.Column("medications", postgresql.JSONB, nullable=True),
        sa.Column("disabilities", postgresql.JSONB, nullable=True),
        sa.Column("surgeries_history", postgresql.JSONB, nullable=True),
        sa.Column("insurance_provider", sa.String(255), nullable=True),
        sa.Column("insurance_policy_number", sa.String(255), nullable=True),
        sa.Column("primary_physician", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_medical_profiles_elder_id", "medical_profiles", ["elder_id"], unique=True)

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_to_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_type", sa.String(128), nullable=False),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="granted"),
        sa.Column("granted_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("revoked_at", sa.Date(), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_to_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_consent_records_granted_to_user_id", "consent_records", ["granted_to_user_id"])

    op.create_table(
        "care_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goals", postgresql.JSONB, nullable=True),
        sa.Column("care_schedule", postgresql.JSONB, nullable=True),
        sa.Column("risk_level", sa.String(32), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_care_plans_created_by", "care_plans", ["created_by"])

    op.create_table(
        "health_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("elder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dietary_preferences", postgresql.JSONB, nullable=True),
        sa.Column("activity_preferences", postgresql.JSONB, nullable=True),
        sa.Column("communication_preferences", postgresql.JSONB, nullable=True),
        sa.Column("emergency_preferences", postgresql.JSONB, nullable=True),
        sa.Column("sleep_preferences", postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(["elder_id"], ["elders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_health_preferences_elder_id", "health_preferences", ["elder_id"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_health_preferences_elder_id", "health_preferences")
    op.drop_table("health_preferences")
    op.drop_table("care_plans")
    op.drop_table("consent_records")
    op.drop_index("idx_medical_profiles_elder_id", "medical_profiles")
    op.drop_table("medical_profiles")
    op.drop_table("emergency_contacts")
    op.drop_table("care_relationships")
    op.drop_table("family_members")
    op.drop_index("idx_doctors_tenant_license", "doctors")
    op.drop_table("doctors")
    op.drop_table("caregivers")
    op.drop_index("idx_elders_tenant_mrn", "elders")
    op.drop_index("idx_elders_deleted_at", "elders")
    op.drop_table("elders")
