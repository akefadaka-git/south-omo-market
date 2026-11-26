"""ORM mappings for the additive governance, employment and AI-control schema."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserPermission(Base):
    __tablename__ = "user_permissions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusinessProfile(Base):
    __tablename__ = "business_profiles"
    __table_args__ = (
        CheckConstraint(
            "public_contact_method IS NULL OR public_contact_method IN ('phone','sms','email')",
            name="ck_business_public_contact_method",
        ),
        CheckConstraint(
            "public_location_visibility IN ('hidden','approximate','exact')",
            name="ck_business_public_location_visibility",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_business_public_coordinates_pair",
        ),
        CheckConstraint(
            "(latitude IS NULL OR latitude BETWEEN -90 AND 90) AND (longitude IS NULL OR longitude BETWEEN -180 AND 180)",
            name="ck_business_public_coordinates_range",
        ),
        CheckConstraint(
            "public_location_visibility != 'exact' OR (latitude IS NOT NULL AND longitude IS NOT NULL AND location_consent_at IS NOT NULL)",
            name="ck_business_exact_location_consent",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_code: Mapped[str] = mapped_column(String(80), unique=True)
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200))
    business_type: Mapped[str] = mapped_column(String(60))
    verification_status: Mapped[str] = mapped_column(String(24), default="pending")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registration_number: Mapped[str | None] = mapped_column(String(120))
    registered_address: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(String(254))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text)
    primary_category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    operating_location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"), index=True)
    service_area: Mapped[list] = mapped_column(JSON, default=list)
    operating_hours: Mapped[dict] = mapped_column(JSON, default=dict)
    supported_languages: Mapped[list] = mapped_column(JSON, default=lambda: ["am", "en"])
    public_contact_phone: Mapped[str | None] = mapped_column(String(32))
    public_contact_email: Mapped[str | None] = mapped_column(String(254))
    public_contact_method: Mapped[str | None] = mapped_column(String(16))
    public_location_visibility: Mapped[str] = mapped_column(String(16), default="hidden", server_default="hidden")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    location_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_evidence: Mapped[list] = mapped_column(JSON, default=list)
    verification_notes: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusinessMembership(Base):
    __tablename__ = "business_memberships"
    __table_args__ = (
        CheckConstraint("membership_role IN ('owner','administrator','manager','staff','finance','viewer')", name="ck_business_membership_role"),
        CheckConstraint("status IN ('invited','pending','active','suspended','rejected','revoked','expired')", name="ck_business_membership_status"),
        Index("uq_business_membership_current", "business_id", "user_id", unique=True,
              sqlite_where=__import__("sqlalchemy").text("status IN ('invited','pending','active','suspended')"),
              postgresql_where=__import__("sqlalchemy").text("status IN ('invited','pending','active','suspended')")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    membership_role: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    invited_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusinessMembershipEvent(Base):
    __tablename__ = "business_membership_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id", ondelete="CASCADE"))
    membership_id: Mapped[str] = mapped_column(ForeignKey("business_memberships.id", ondelete="CASCADE"))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(80))
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusinessVerificationEvent(Base):
    __tablename__ = "business_verification_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id", ondelete="CASCADE"))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    previous_status: Mapped[str | None] = mapped_column(String(24))
    new_status: Mapped[str] = mapped_column(String(24))
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusinessRolePermission(Base):
    __tablename__ = "business_role_permissions"
    __table_args__ = (
        UniqueConstraint("membership_role", "permission_code", name="uq_business_role_permission"),
        CheckConstraint("membership_role IN ('owner','administrator','manager','staff','finance','viewer')", name="ck_business_role_permission_role"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    membership_role: Mapped[str] = mapped_column(String(40))
    permission_code: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmploymentProvider(Base):
    __tablename__ = "employment_providers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id"), unique=True)
    verification_status: Mapped[str] = mapped_column(String(24), default="pending")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class JobSeekerProfile(Base):
    __tablename__ = "job_seeker_profiles"
    __table_args__ = (CheckConstraint("visibility IN ('private','consented_employers')", name="ck_job_seeker_visibility"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    experience: Mapped[list] = mapped_column(JSON, default=list)
    qualifications: Mapped[list] = mapped_column(JSON, default=list)
    preferred_occupations: Mapped[list] = mapped_column(JSON, default=list)
    preferred_location_codes: Mapped[list] = mapped_column(JSON, default=list)
    availability: Mapped[str | None] = mapped_column(String(40))
    contact_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    visibility: Mapped[str] = mapped_column(String(24), default="private")
    consent_version: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmploymentOpportunity(Base):
    __tablename__ = "employment_opportunities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("employment_providers.id"))
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    occupation_code: Mapped[str] = mapped_column(String(80))
    location_code: Mapped[str] = mapped_column(String(80))
    employment_type: Mapped[str] = mapped_column(String(40))
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdvertisingAgreement(Base):
    __tablename__ = "advertising_agreements"
    __table_args__ = (CheckConstraint("agreed_price_minor > 0 AND duration_days > 0", name="ck_ad_agreement_price_duration"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("employment_providers.id"))
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("employment_opportunities.id"))
    terms_version: Mapped[str] = mapped_column(String(40))
    agreed_price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    duration_days: Mapped[int] = mapped_column(Integer)
    provider_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_acceptance_evidence: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="pending")


class AdvertisingPayment(Base):
    __tablename__ = "advertising_payments"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="ck_ad_payment_amount"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agreement_id: Mapped[str] = mapped_column(ForeignKey("advertising_agreements.id"))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    payment_method: Mapped[str] = mapped_column(String(40))
    external_reference: Mapped[str | None] = mapped_column(String(160))
    evidence_ref: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), default="submitted")


class EmploymentAdvertisement(Base):
    __tablename__ = "employment_advertisements"
    __table_args__ = (CheckConstraint("status IN ('pending_owner','published','rejected','expired','withdrawn')", name="ck_employment_ad_status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("employment_opportunities.id"))
    agreement_id: Mapped[str] = mapped_column(ForeignKey("advertising_agreements.id"), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="pending_owner")
    published_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateConsent(Base):
    __tablename__ = "candidate_consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_seeker_id: Mapped[str] = mapped_column(ForeignKey("job_seeker_profiles.id", ondelete="CASCADE"))
    provider_id: Mapped[str] = mapped_column(ForeignKey("employment_providers.id"))
    purpose: Mapped[str] = mapped_column(String(120))
    consent_version: Mapped[str] = mapped_column(String(40))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmploymentApplication(Base):
    __tablename__ = "employment_applications"
    __table_args__ = (UniqueConstraint("opportunity_id", "job_seeker_id", name="uq_employment_application"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("employment_opportunities.id"))
    job_seeker_id: Mapped[str] = mapped_column(ForeignKey("job_seeker_profiles.id"))
    status: Mapped[str] = mapped_column(String(24), default="submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateReferral(Base):
    __tablename__ = "candidate_referrals"
    __table_args__ = (CheckConstraint("decision IN ('human_review','referred','declined_by_human')", name="ck_candidate_referral_human_decision"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("employment_applications.id"))
    provider_id: Mapped[str] = mapped_column(ForeignKey("employment_providers.id"))
    referred_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(24), default="human_review")
    matching_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmploymentEvent(Base):
    __tablename__ = "employment_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(36))
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PolicyPack(Base):
    __tablename__ = "policy_packs"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_policy_pack_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), default="draft")
    policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PolicyRule(Base):
    __tablename__ = "policy_rules"
    __table_args__ = (
        UniqueConstraint("policy_pack_id", "rule_code", name="uq_policy_rule_code"),
        CheckConstraint("effect IN ('allow','deny')", name="ck_policy_rule_effect"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    policy_pack_id: Mapped[str] = mapped_column(ForeignKey("policy_packs.id", ondelete="CASCADE"))
    rule_code: Mapped[str] = mapped_column(String(100))
    effect: Mapped[str] = mapped_column(String(12))
    subject: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(120))
    resource: Mapped[str] = mapped_column(String(120))
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)


class AIProvider(Base):
    __tablename__ = "ai_providers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    provider_kind: Mapped[str] = mapped_column(String(40))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_provider: Mapped[bool] = mapped_column(Boolean, default=False)
    endpoint_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    allowlisted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (UniqueConstraint("provider_id", "model_code", "model_version", name="uq_ai_model_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("ai_providers.id", ondelete="CASCADE"))
    model_code: Mapped[str] = mapped_column(String(120))
    model_version: Mapped[str] = mapped_column(String(80))
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    data_classification_max: Mapped[str] = mapped_column(String(24), default="public")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class AITaskRoute(Base):
    __tablename__ = "ai_task_routes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_code: Mapped[str] = mapped_column(String(100), unique=True)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("ai_providers.id"))
    model_id: Mapped[str | None] = mapped_column(ForeignKey("ai_models.id"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    max_data_classification: Mapped[str] = mapped_column(String(24), default="public")
    quota_per_day: Mapped[int] = mapped_column(Integer, default=0)



class ProtectedCategoryRoot(Base):
    """Persisted category roots whose descendants are outside seller publication."""
    __tablename__ = "protected_category_roots"
    __table_args__ = (
        UniqueConstraint("category_id", "policy_code", name="uq_protected_category_policy"),
        Index("ix_protected_category_roots_category", "category_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    policy_code: Mapped[str] = mapped_column(String(100), unique=True)
    applies_to_descendants: Mapped[bool] = mapped_column(Boolean, default=True)
    seller_listing_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
