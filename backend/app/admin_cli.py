"""Out-of-band administrator provisioning; intentionally not exposed as an API route."""
import argparse
from getpass import getpass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_engine
from app.models import AuditEvent, User
from app.security import hash_password


def set_admin_role(db: Session, phone_number: str, grant: bool, operator: str) -> User:
    if not operator.strip():
        raise ValueError("Operator identifier is required")
    user = db.scalar(select(User).where(User.phone_number == phone_number).with_for_update())
    if user is None:
        raise ValueError("No account exists for the supplied phone number")

    if user.is_admin == grant:
        return user

    if not grant and user.is_active:
        active_admins = db.scalar(
            select(func.count()).select_from(User).where(
                User.is_admin.is_(True), User.is_active.is_(True)
            )
        )
        if active_admins <= 1:
            raise ValueError("Cannot revoke the last active administrator")

    user.is_admin = grant
    db.add(AuditEvent(
        actor_id=None,
        action="admin.access.granted" if grant else "admin.access.revoked",
        resource_type="user",
        resource_id=user.id,
        event_metadata={"provisioning_method": "trusted_cli", "operator": operator},
    ))
    db.commit()
    db.refresh(user)
    return user


def create_test_admin(db: Session, phone_number: str, display_name: str, password: str, operator: str) -> User:
    if get_settings().app_env == "production":
        raise ValueError("Test administrator accounts are disabled in production")
    if not operator.strip() or not phone_number.strip() or not display_name.strip():
        raise ValueError("Operator, phone number and display name are required")
    if len(password) < 12:
        raise ValueError("Test administrator password must contain at least 12 characters")
    if db.scalar(select(User.id).where(User.phone_number == phone_number)):
        raise ValueError("An account already exists for this phone number; use the normal grant workflow if authorized")
    user = User(
        phone_number=phone_number,
        display_name=display_name.strip(),
        account_type="buyer",
        password_hash=hash_password(password),
        is_admin=True,
    )
    db.add(user)
    db.flush()
    db.add(AuditEvent(
        actor_id=None,
        action="admin.test_account.created",
        resource_type="user",
        resource_id=user.id,
        event_metadata={"provisioning_method": "trusted_cli", "operator": operator, "environment": get_settings().app_env},
    ))
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision South Omo Market administrator access")
    parser.add_argument("action", choices=("grant", "revoke", "create-test-admin"))
    parser.add_argument("--operator", required=True, help="Authenticated operator identifier for the audit record")
    args = parser.parse_args()
    if not args.operator.strip():
        parser.error("--operator must not be blank")

    if args.action == "create-test-admin":
        if get_settings().app_env == "production":
            parser.error("Test administrator accounts are disabled in production")
        phone_number = input("New test-admin phone number: ").strip()
        display_name = input("Test-admin display name: ").strip()
        password = getpass("Test-admin password (12+ characters): ")
        confirmation = getpass("Re-enter test-admin password: ")
        if password != confirmation:
            parser.error("Password confirmation did not match")
        with Session(get_engine()) as db:
            try:
                user = create_test_admin(db, phone_number, display_name, password, args.operator)
            except ValueError as error:
                parser.error(str(error))
        print(f"Test administrator created for account {user.id}. The password is not displayed.")
        return

    phone_number = input("Phone number of the existing account: ").strip()
    confirmation = input("Re-enter the exact phone number to confirm: ").strip()
    if not phone_number or phone_number != confirmation:
        parser.error("Phone number confirmation did not match")

    with Session(get_engine()) as db:
        try:
            user = set_admin_role(
                db, phone_number, grant=args.action == "grant", operator=args.operator
            )
        except ValueError as error:
            parser.error(str(error))
    state = "granted" if args.action == "grant" else "revoked"
    print(f"Administrator access {state} for account {user.id}")


if __name__ == "__main__":
    main()
