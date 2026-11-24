"""Out-of-band, one-time Owner-role assignment. Never exposed as an HTTP endpoint."""
import argparse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_engine


def assign_owner(phone_number: str, operator: str) -> str:
    if not operator.strip():
        raise ValueError("Operator identifier is required")
    with Session(get_engine()) as db, db.begin():
        user = db.execute(
            text("SELECT id FROM users WHERE phone_number = :phone FOR UPDATE"),
            {"phone": phone_number},
        ).scalar_one_or_none()
        if user is None:
            raise ValueError("No existing account matches the supplied phone number")
        owner_role = db.execute(
            text("SELECT id FROM roles WHERE code = 'owner'")
        ).scalar_one_or_none()
        if owner_role is None:
            raise ValueError("System reference seeder must run before Owner provisioning")
        existing = db.execute(
            text("SELECT user_id FROM user_roles WHERE role_id = :role_id LIMIT 1"),
            {"role_id": owner_role},
        ).scalar_one_or_none()
        if existing and existing != user:
            raise ValueError("An Owner principal is already assigned; use a separately governed succession process")
        db.execute(text("""
            INSERT INTO user_roles (user_id, role_id, assigned_by)
            VALUES (:user_id, :role_id, NULL)
            ON CONFLICT (user_id, role_id) DO NOTHING
        """), {"user_id": user, "role_id": owner_role})
        db.execute(text("""
            INSERT INTO audit_events
                (id, actor_id, action, resource_type, resource_id, event_metadata)
            VALUES (:id, NULL, 'owner.role.assigned', 'user', :user_id,
                    :metadata)
        """), {
            "id": "owner-provision-" + user,
            "user_id": user,
            "metadata": {"provisioning_method": "trusted_cli", "operator": operator},
        })
        return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Protected initial Project Owner provisioning")
    parser.add_argument("--operator", required=True, help="Authenticated operator identifier")
    args = parser.parse_args()
    phone = input("Phone number of the existing account: ").strip()
    confirmation = input("Re-enter the exact phone number: ").strip()
    if not phone or phone != confirmation:
        parser.error("Phone number confirmation did not match")
    if input("Type ASSIGN-OWNER to continue: ").strip() != "ASSIGN-OWNER":
        parser.error("Owner provisioning was not confirmed")
    try:
        user_id = assign_owner(phone, args.operator)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Owner role assigned to existing account {user_id}")


if __name__ == "__main__":
    main()
