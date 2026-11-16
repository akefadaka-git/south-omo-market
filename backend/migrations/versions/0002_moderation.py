"""Add administrator roles and listing moderation metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0002_moderation"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("listings") as batch:
        batch.add_column(sa.Column("moderation_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column(
            "reviewed_by", sa.String(36), sa.ForeignKey("users.id", name="fk_listings_reviewed_by_users"), nullable=True
        ))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("listings") as batch:
        batch.drop_constraint("fk_listings_reviewed_by_users", type_="foreignkey")
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by")
        batch.drop_column("moderation_note")
    op.drop_column("users", "is_admin")
