"""Add RBAC, business membership, employment agency and AI governance foundations.

Revision ID: 0011_owner_governance_employment_ai
Revises: 0010_market_schedule_effectivity
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_gov_employment_ai"
down_revision = "0010_market_schedule_effectivity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_table(
        "user_permissions",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("granted_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "business_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_code", sa.String(80), nullable=False, unique=True),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("business_type", sa.String(60), nullable=False),
        sa.Column("verification_status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("verification_status IN ('pending','verified','rejected','suspended')", name="ck_business_verification_status"),
    )
    op.create_table(
        "business_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("membership_role", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("business_id", "user_id", name="uq_business_membership_user"),
    )
    op.create_table(
        "employment_providers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id"), nullable=False, unique=True),
        sa.Column("verification_status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_table(
        "job_seeker_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("experience", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("qualifications", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preferred_occupations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preferred_location_codes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("availability", sa.String(40), nullable=True),
        sa.Column("contact_preferences", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("visibility", sa.String(24), nullable=False, server_default="private"),
        sa.Column("consent_version", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("visibility IN ('private','consented_employers')", name="ck_job_seeker_visibility"),
    )
    op.create_table(
        "employment_opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("employment_providers.id"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("occupation_code", sa.String(80), nullable=False),
        sa.Column("location_code", sa.String(80), nullable=False),
        sa.Column("employment_type", sa.String(40), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "advertising_agreements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("employment_providers.id"), nullable=False),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("employment_opportunities.id"), nullable=False),
        sa.Column("terms_version", sa.String(40), nullable=False),
        sa.Column("agreed_price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ETB"),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("provider_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_acceptance_evidence", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.CheckConstraint("agreed_price_minor > 0 AND duration_days > 0", name="ck_ad_agreement_price_duration"),
    )
    op.create_table(
        "advertising_payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agreement_id", sa.String(36), sa.ForeignKey("advertising_agreements.id"), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ETB"),
        sa.Column("payment_method", sa.String(40), nullable=False),
        sa.Column("external_reference", sa.String(160), nullable=True),
        sa.Column("evidence_ref", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="submitted"),
        sa.CheckConstraint("amount_minor > 0", name="ck_ad_payment_amount"),
    )
    op.create_table(
        "employment_advertisements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("employment_opportunities.id"), nullable=False),
        sa.Column("agreement_id", sa.String(36), sa.ForeignKey("advertising_agreements.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending_owner"),
        sa.Column("published_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending_owner','published','rejected','expired','withdrawn')", name="ck_employment_ad_status"),
    )
    op.create_table(
        "candidate_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_seeker_id", sa.String(36), sa.ForeignKey("job_seeker_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("employment_providers.id"), nullable=False),
        sa.Column("purpose", sa.String(120), nullable=False),
        sa.Column("consent_version", sa.String(40), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "employment_applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("employment_opportunities.id"), nullable=False),
        sa.Column("job_seeker_id", sa.String(36), sa.ForeignKey("job_seeker_profiles.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="submitted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("opportunity_id", "job_seeker_id", name="uq_employment_application"),
    )
    op.create_table(
        "candidate_referrals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("employment_applications.id"), nullable=False),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("employment_providers.id"), nullable=False),
        sa.Column("referred_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(24), nullable=False, server_default="human_review"),
        sa.Column("matching_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("decision IN ('human_review','referred','declined_by_human')", name="ck_candidate_referral_human_decision"),
    )
    op.create_table(
        "employment_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "policy_packs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("policy_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", "version", name="uq_policy_pack_version"),
    )
    op.create_table(
        "policy_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("policy_pack_id", sa.String(36), sa.ForeignKey("policy_packs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_code", sa.String(100), nullable=False),
        sa.Column("effect", sa.String(12), nullable=False),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource", sa.String(120), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("policy_pack_id", "rule_code", name="uq_policy_rule_code"),
        sa.CheckConstraint("effect IN ('allow','deny')", name="ck_policy_rule_effect"),
    )
    op.create_table(
        "ai_providers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("provider_kind", sa.String(40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("primary_provider", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("endpoint_configured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowlisted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "ai_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_code", sa.String(120), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("data_classification_max", sa.String(24), nullable=False, server_default="public"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("provider_id", "model_code", "model_version", name="uq_ai_model_version"),
    )
    op.create_table(
        "ai_task_routes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_code", sa.String(100), nullable=False, unique=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("ai_providers.id"), nullable=True),
        sa.Column("model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_human_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("max_data_classification", sa.String(24), nullable=False, server_default="public"),
        sa.Column("quota_per_day", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_employment_opportunities_provider", "employment_opportunities", ["provider_id"])
    op.create_index("ix_employment_ads_status_expiry", "employment_advertisements", ["status", "expires_at"])


def downgrade() -> None:
    for table in (
        "ai_task_routes", "ai_models", "ai_providers", "policy_rules", "policy_packs",
        "employment_events", "candidate_referrals", "employment_applications",
        "candidate_consents", "employment_advertisements", "advertising_payments",
        "advertising_agreements", "employment_opportunities", "job_seeker_profiles",
        "employment_providers", "business_memberships", "business_profiles",
        "user_permissions", "user_roles", "role_permissions", "permissions", "roles",
    ):
        op.drop_table(table)
