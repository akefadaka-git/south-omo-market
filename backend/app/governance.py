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
