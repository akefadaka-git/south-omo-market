"""Deterministic, repeatable system-reference seeding. Never creates or assigns users."""
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text
from sqlalchemy.orm import Session


def _id(kind: str, code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"south-omo-market:{kind}:{code}"))


ROLES = {
    "owner": "Project Owner",
    "admin": "Administrator",
    "agent": "Agency Agent",
    "merchant": "Merchant",
    "vendor": "Vendor",
    "customer": "Customer",
}
PERMISSIONS = {
    "marketplace.listing.create": "Create ordinary marketplace listings",
    "marketplace.listing.moderate": "Moderate ordinary marketplace listings",
    "business.profile.manage": "Manage an approved business profile",
    "employment.provider.request": "Submit an employment provider verification request",
    "employment.opportunity.submit": "Submit a job opportunity for Owner review",
    "employment.advertisement.publish": "Publish a paid employment advertisement",
    "employment.payment.verify": "Verify evidence of direct advertising payment",
    "employment.provider.verify": "Verify an employment provider",
    "employment.candidate.refer": "Refer a candidate for human review",
    "policy.pack.manage": "Manage governed policy packs",
    "ai.provider.configure": "Configure allowlisted AI providers",
    "ai.model.configure": "Configure AI model registry and routing",
    "ai.audit.read": "Read AI governance and usage audit records",
}
ROLE_PERMISSIONS = {
    "owner": tuple(PERMISSIONS),
    "admin": (
        "marketplace.listing.moderate",
        "business.profile.manage",
        "employment.candidate.refer",
        "ai.audit.read",
    ),
    "agent": ("employment.candidate.refer",),
    "merchant": ("marketplace.listing.create",),
    "vendor": ("marketplace.listing.create",),
    "customer": (),
}


def seed_system_reference_data(db: Session) -> None:
    """Upsert codes/descriptions without overwriting user-authored business data."""
    for code, name in ROLES.items():
        db.execute(text("""
            INSERT INTO roles (id, code, name, description, is_system)
            VALUES (:id, :code, :name, :description, TRUE)
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
        """), {"id": _id("role", code), "code": code, "name": name,
              "description": f"System role: {code}"})

    for code, description in PERMISSIONS.items():
        db.execute(text("""
            INSERT INTO permissions (id, code, description)
            VALUES (:id, :code, :description)
            ON CONFLICT (code) DO UPDATE SET description = EXCLUDED.description
        """), {"id": _id("permission", code), "code": code, "description": description})

    role_ids = {code: _id("role", code) for code in ROLES}
    permission_ids = {code: _id("permission", code) for code in PERMISSIONS}
    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        for permission_code in permission_codes:
            db.execute(text("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (:role_id, :permission_id)
                ON CONFLICT DO NOTHING
            """), {"role_id": role_ids[role_code], "permission_id": permission_ids[permission_code]})

    db.execute(text("""
        INSERT INTO ai_providers
            (id, code, display_name, provider_kind, enabled, primary_provider,
             endpoint_configured, allowlisted)
        VALUES (:id, 'iroka', 'IROKA', 'native', FALSE, TRUE, FALSE, TRUE)
        ON CONFLICT (code) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            primary_provider = TRUE
    """), {"id": _id("ai-provider", "iroka")})

    db.execute(text("""
        INSERT INTO ai_providers
            (id, code, display_name, provider_kind, enabled, primary_provider,
             endpoint_configured, allowlisted)
        VALUES (:id, 'secondary-unconfigured', 'Secondary AI provider (unconfigured)',
                'external', FALSE, FALSE, FALSE, FALSE)
        ON CONFLICT (code) DO NOTHING
    """), {"id": _id("ai-provider", "secondary-unconfigured")})

    db.execute(text("""
        INSERT INTO policy_packs (id, code, version, status, policy_json)
        VALUES (:id, 'south-omo-default-deny', '1.0.0', 'active',
                '{"default_effect":"deny","owner_approval_required":true}')
        ON CONFLICT (code, version) DO NOTHING
    """), {"id": _id("policy-pack", "south-omo-default-deny:1.0.0")})

    pack_id = _id("policy-pack", "south-omo-default-deny:1.0.0")
    db.execute(text("""
        INSERT INTO policy_rules
            (id, policy_pack_id, rule_code, effect, subject, action, resource, conditions)
        VALUES (:id, :pack_id, 'employment-advertisement-publish-owner-only',
                'allow', 'role:owner', 'employment.advertisement.publish',
                'employment_advertisements',
                '{"provider_verified":true,"agreement_accepted":true,"payment_verified":true}')
        ON CONFLICT (policy_pack_id, rule_code) DO NOTHING
    """), {"id": _id("policy-rule", "employment-advertisement-publish-owner-only"),
           "pack_id": pack_id})
    db.commit()
