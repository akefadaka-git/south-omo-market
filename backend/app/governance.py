from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import User


def require_permission(permission_code: str):
    """Require an explicit effective RBAC permission; is_admin is not Owner authority."""
    def dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        allowed = db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM user_roles ur
                    JOIN roles r ON r.id = ur.role_id
                    JOIN role_permissions rp ON rp.role_id = r.id
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE ur.user_id = :user_id
                      AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                      AND p.code = :permission_code
                    UNION ALL
                    SELECT 1
                    FROM user_permissions up
                    JOIN permissions p ON p.id = up.permission_id
                    WHERE up.user_id = :user_id
                      AND up.granted = TRUE
                      AND p.code = :permission_code
                )
            """),
            {"user_id": user.id, "permission_code": permission_code},
        ).scalar_one()
        if not allowed:
            raise HTTPException(status_code=403, detail="Required permission is not assigned")
        return user
    return dependency
