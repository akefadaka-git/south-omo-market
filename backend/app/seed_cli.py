"""Run versioned system reference seeders after Alembic upgrade."""
from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.seeders.system_reference import seed_system_reference_data


def main() -> None:
    with Session(get_engine()) as db:
        seed_system_reference_data(db)


if __name__ == "__main__":
    main()
