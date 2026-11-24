"""Add configurable market directory and recurring weekly schedule."""
from alembic import op
import sqlalchemy as sa

revision = "0009_market_directory_schedule"
down_revision = "0008_reports_and_seller_blocks"
branch_labels = None
depends_on = None

MARKETS = [
    ("90000000-0000-4000-8000-000000000001", "MAALE-BENETA", "Beneta", 3),
    ("90000000-0000-4000-8000-000000000002", "MAALE-ASHEKER", "Asheker", 1),
    ("90000000-0000-4000-8000-000000000003", "MAALE-BOSHKORO", "Boshkoro", 5),
    ("90000000-0000-4000-8000-000000000004", "MAALE-BALA", "Bala", 1),
    ("90000000-0000-4000-8000-000000000005", "MAALE-KOYBE", "Koybe", 0),
    ("90000000-0000-4000-8000-000000000006", "MAALE-BOBO", "Bobo", 2),
    ("90000000-0000-4000-8000-000000000007", "MAALE-AJO", "Ajo", 5),
    ("90000000-0000-4000-8000-000000000008", "MAALE-GENTO", "Gento", 5),
]


def upgrade() -> None:
    op.create_table(
        "markets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_markets_code", "markets", ["code"], unique=True)
    op.create_index("ix_markets_location_id", "markets", ["location_id"])
    op.create_index("ix_markets_is_active", "markets", ["is_active"])
    op.create_table(
        "market_schedule_days",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("market_id", sa.String(36), sa.ForeignKey("markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("market_id", "weekday", name="uq_market_schedule_market_weekday"),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_market_schedule_weekday"),
    )
    op.create_index("ix_market_schedule_days_market_id", "market_schedule_days", ["market_id"])
    op.create_index("ix_market_schedule_days_weekday", "market_schedule_days", ["weekday"])

    # Idempotent owner-provided seed. Location associations remain NULL until confirmed.
    bind = op.get_bind()
    market_table = sa.table(
        "markets", sa.column("id", sa.String(36)), sa.column("code", sa.String(40)),
        sa.column("name", sa.String(120)), sa.column("location_id", sa.String(36)),
        sa.column("is_active", sa.Boolean()),
    )
    schedule_table = sa.table(
        "market_schedule_days", sa.column("id", sa.String(36)),
        sa.column("market_id", sa.String(36)), sa.column("weekday", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    existing_markets = {
        code: market_id for market_id, code in bind.execute(
            sa.select(market_table.c.id, market_table.c.code)
        ).all()
    }
    existing_days = set(bind.execute(sa.select(
        schedule_table.c.market_id, schedule_table.c.weekday
    )).all())
    for market_id, code, name, weekday in MARKETS:
        actual_id = existing_markets.get(code)
        if actual_id is None:
            bind.execute(market_table.insert().values(
                id=market_id, code=code, name=name, location_id=None, is_active=True,
            ))
            actual_id = market_id
            existing_markets[code] = actual_id
        if (actual_id, weekday) not in existing_days:
            bind.execute(schedule_table.insert().values(
                id=f"91000000-0000-4000-8000-{actual_id[-12:]}",
                market_id=actual_id, weekday=weekday, is_active=True,
            ))
            existing_days.add((actual_id, weekday))


def downgrade() -> None:
    op.drop_index("ix_market_schedule_days_weekday", table_name="market_schedule_days")
    op.drop_index("ix_market_schedule_days_market_id", table_name="market_schedule_days")
    op.drop_table("market_schedule_days")
    op.drop_index("ix_markets_is_active", table_name="markets")
    op.drop_index("ix_markets_location_id", table_name="markets")
    op.drop_index("ix_markets_code", table_name="markets")
    op.drop_table("markets")
