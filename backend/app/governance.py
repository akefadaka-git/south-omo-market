from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import User


OWNER_ONLY_PERMISSIONS = {
    "employment.advertisement.manage", "employment.advertisement.publish",
    "employment.payment.verify", "employment.provider.verify",
    "business.verification.manage", "policy.pack.manage",
    "ai.provider.configure", "ai.model.configure",
}


def require_permission(permission_code: str):
    """Require effective global RBAC permission; sensitive controls require platform Owner."""
    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if permission_code in OWNER_ONLY_PERMISSIONS:
            allowed = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM user_roles ur
                    JOIN roles r ON r.id=ur.role_id
                    JOIN role_permissions rp ON rp.role_id=r.id
                    JOIN permissions p ON p.id=rp.permission_id
                    WHERE ur.user_id=:user_id AND r.code='owner'
                      AND (ur.expires_at IS NULL OR ur.expires_at>CURRENT_TIMESTAMP)
                      AND p.code=:permission_code
                )
            """), {"user_id": user.id, "permission_code": permission_code}).scalar_one()
        else:
            allowed = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM user_roles ur
                    JOIN roles r ON r.id=ur.role_id
                    JOIN role_permissions rp ON rp.role_id=r.id
                    JOIN permissions p ON p.id=rp.permission_id
                    WHERE ur.user_id=:user_id
                      AND (ur.expires_at IS NULL OR ur.expires_at>CURRENT_TIMESTAMP)
                      AND p.code=:permission_code
                    UNION ALL
                    SELECT 1 FROM user_permissions up
                    JOIN permissions p ON p.id=up.permission_id
                    WHERE up.user_id=:user_id AND up.granted=TRUE AND p.code=:permission_code
                )
            """), {"user_id": user.id, "permission_code": permission_code}).scalar_one()
        if not allowed:
            raise HTTPException(status_code=403, detail="Required permission is not assigned")
        return user
    return dependency


def ensure_marketplace_seller_role(db: Session, user_id: str) -> None:
    """Bind a seller profile to the least-privilege merchant role.

    The profile is the eligibility signal; public account registration alone
    never grants seller permissions. Existing seller profiles are reconciled
    idempotently when they next perform a protected listing operation.
    """
    has_profile = db.execute(text(
        "SELECT EXISTS (SELECT 1 FROM seller_profiles WHERE user_id=:user_id)"
    ), {"user_id": user_id}).scalar_one()
    if not has_profile:
        raise HTTPException(status_code=409, detail="Create a seller profile before listing")
    configured = db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM roles r
            JOIN role_permissions rp ON rp.role_id=r.id
            JOIN permissions p ON p.id=rp.permission_id
            WHERE r.code='merchant' AND p.code='marketplace.listing.create'
        )
    """)).scalar_one()
    if not configured:
        raise HTTPException(status_code=503, detail="Marketplace seller permissions are not configured")
    db.execute(text("""
        INSERT INTO user_roles (user_id, role_id, assigned_by, expires_at)
        SELECT :user_id, r.id, NULL, NULL FROM roles r
        WHERE r.code='merchant'
        ON CONFLICT (user_id, role_id) DO NOTHING
    """), {"user_id": user_id})


def require_marketplace_listing_policy(
    db: Session, user: User, *, action: str, category_id: str
) -> None:
    """Require both the merchant RBAC grant and an affirmative policy decision."""
    from app.policy_engine import evaluate_policy

    ensure_marketplace_seller_role(db, user.id)
    allowed = db.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM user_roles ur
            JOIN roles r ON r.id=ur.role_id
            JOIN role_permissions rp ON rp.role_id=r.id
            JOIN permissions p ON p.id=rp.permission_id
            WHERE ur.user_id=:user_id AND r.code='merchant'
              AND (ur.expires_at IS NULL OR ur.expires_at>CURRENT_TIMESTAMP)
              AND p.code='marketplace.listing.create'
        )
    """), {"user_id": user.id}).scalar_one()
    if not allowed or not evaluate_policy(
        db, subject="role:merchant", action=action, resource="listings",
        facts={"category_id": category_id},
    ):
        raise HTTPException(status_code=403, detail="Marketplace listing policy denied this action")


def require_business_permission(permission_code: str):
    """Require a verified, active business, active membership and role-scoped permission."""
    def dependency(
        business_id: str,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        allowed = db.execute(text("""
            SELECT EXISTS (
                SELECT 1
                FROM business_memberships bm
                JOIN business_profiles bp ON bp.id=bm.business_id
                JOIN business_role_permissions brp ON brp.membership_role=bm.membership_role
                JOIN users u ON u.id=bm.user_id
                WHERE bm.business_id=:business_id AND bm.user_id=:user_id
                  AND bm.status='active'
                  AND (bm.expires_at IS NULL OR bm.expires_at>CURRENT_TIMESTAMP)
                  AND bp.is_active=TRUE AND bp.verification_status='verified'
                  AND u.is_active=TRUE AND u.is_suspended=FALSE
                  AND brp.permission_code=:permission_code
            )
        """), {"business_id": business_id, "user_id": user.id,
                "permission_code": permission_code}).scalar_one()
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Verified business, active membership and permission required",
            )
        return user
    return dependency



def require_seller_business_listing_access(db: Session, user: User) -> None:
    """Fail closed unless the seller belongs to a verified, active business.

    Listing permissions are business-scoped. A global merchant role or the
    existence of a seller profile is not sufficient authorization.
    """
    allowed = db.execute(text("""
        SELECT EXISTS (
            SELECT 1
            FROM seller_profiles sp
            JOIN business_profiles bp ON bp.id = sp.business_id
            JOIN business_memberships bm ON bm.business_id = bp.id
            JOIN users u ON u.id = bm.user_id
            WHERE sp.user_id = :user_id
              AND bm.user_id = :user_id
              AND bm.status = 'active'
              AND (bm.expires_at IS NULL OR bm.expires_at > CURRENT_TIMESTAMP)
              AND bm.membership_role IN ('owner','administrator','manager','staff')
              AND bp.is_active = TRUE
              AND bp.verification_status = 'verified'
              AND u.is_active = TRUE
              AND u.is_suspended = FALSE
        )
    """), {"user_id": user.id}).scalar_one()
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="A verified active business and active listing-authorized membership are required",
        )
