"""add supplier deliveries

Revision ID: f1913f2a0353
Revises: 620e28a75437
Create Date: 2026-10-15 18:42:10.685454

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1913f2a0353"
down_revision: str | Sequence[str] | None = "620e28a75437"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "supplier_list_id",
            sa.Integer(),
            sa.ForeignKey("supplier_lists.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_table(
        "supplier_delivery_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "delivery_id",
            sa.Integer(),
            sa.ForeignKey("supplier_deliveries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fish_type_id",
            sa.Integer(),
            sa.ForeignKey("fish_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fish_type_name", sa.String(100), nullable=False),
        sa.Column("planned_bags", sa.Integer(), nullable=False),
        sa.Column("delivered_bags", sa.Integer(), nullable=False),
        sa.Column("rejected_bags", sa.Integer(), nullable=False),
        sa.Column("damaged_bags", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "delivery_id",
            "fish_type_id",
            name="uq_delivery_items_delivery_fish_type",
        ),
        sa.CheckConstraint("planned_bags >= 0", name="ck_delivery_planned_nonnegative"),
        sa.CheckConstraint("delivered_bags >= 0", name="ck_delivery_delivered_nonnegative"),
        sa.CheckConstraint("rejected_bags >= 0", name="ck_delivery_rejected_nonnegative"),
        sa.CheckConstraint("damaged_bags >= 0", name="ck_delivery_damaged_nonnegative"),
        sa.CheckConstraint(
            "rejected_bags + damaged_bags <= delivered_bags",
            name="ck_delivery_rejected_damaged_within_delivered",
        ),
    )

    op.create_index(
        "ix_supplier_delivery_items_delivery_id",
        "supplier_delivery_items",
        ["delivery_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_supplier_delivery_items_delivery_id",
        table_name="supplier_delivery_items",
    )
    op.drop_table("supplier_delivery_items")
    op.drop_table("supplier_deliveries")