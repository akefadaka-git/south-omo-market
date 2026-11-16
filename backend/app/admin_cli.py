"""Out-of-band administrator provisioning; intentionally not exposed as an API route."""
import argparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.models import AuditEvent, User


def set_admin_role(db: Session, phone_number: str, grant: bool) -> User:
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
        event_metadata={"provisioning_method": "trusted_cli"},
    ))
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision South Omo Market administrator access")
    parser.add_argument("action", choices=("grant", "revoke"))
    parser.add_argument("--phone", required=True, help="Phone number of an already-registered account")
    parser.add_argument(
        "--confirm-phone", required=True,
        help="Repeat the exact phone number to confirm this privileged operation",
    )
    args = parser.parse_args()
    if args.phone != args.confirm_phone:
        parser.error("--phone and --confirm-phone must match exactly")

    with Session(get_engine()) as db:
        try:
            user = set_admin_role(db, args.phone, grant=args.action == "grant")
        except ValueError as error:
            parser.error(str(error))
    state = "granted" if args.action == "grant" else "revoked"
    print(f"Administrator access {state} for account {user.id}")


if __name__ == "__main__":
    main()
