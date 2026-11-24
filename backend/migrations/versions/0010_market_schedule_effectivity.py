"""Add market descriptions and effective schedule dates."""
from alembic import op
import sqlalchemy as sa

revision = "0010_market_schedule_effectivity"
down_revision = "0009_market_directory_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("markets", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("market_schedule_days", sa.Column("effective_from", sa.Date(), nullable=True))
    op.add_column("market_schedule_days", sa.Column("effective_until", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("market_schedule_days", "effective_until")
    op.drop_column("market_schedule_days", "effective_from")
    op.drop_column("markets", "description")
