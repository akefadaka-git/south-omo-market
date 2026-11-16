"""Add administrator roles and listing moderation metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0002_moderation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("listings", sa.Column("moderation_note", sa.Text(), nullable=True))
    op.add_column("listings", sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("listings", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "reviewed_at")
    op.drop_column("listings", "reviewed_by")
    op.drop_column("listings", "moderation_note")
    op.drop_column("users", "is_admin")
