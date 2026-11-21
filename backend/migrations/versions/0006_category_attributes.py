"""Add hierarchical categories and structured listing attributes."""
from alembic import op
import sqlalchemy as sa

revision = "0006_category_attributes"
down_revision = "0005_localized_geography"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("parent_id", sa.String(36), nullable=True))
    op.add_column("categories", sa.Column("attributes_schema", sa.JSON(), nullable=False, server_default="[]"))
    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories", "categories", ["parent_id"], ["id"],
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
    op.add_column("listings", sa.Column("attributes", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("listings", "attributes")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_constraint("fk_categories_parent_id_categories", "categories", type_="foreignkey")
    op.drop_column("categories", "attributes_schema")
    op.drop_column("categories", "parent_id")
