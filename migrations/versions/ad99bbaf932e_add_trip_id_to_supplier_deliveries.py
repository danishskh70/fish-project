"""add trip ownership to supplier deliveries

Supplier delivery slips now belong directly to a trip instead of being
dependent on a supplier list. Existing rows are backfilled from their
supplier list's trip; the migration fails rather than assigning arbitrary
trips when a row cannot be resolved.

Revision ID: ad99bbaf932e
Revises: f1913f2a0353
Create Date: 2026-10-16 14:59:22.785134

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ad99bbaf932e"
down_revision: str | Sequence[str] | None = "f1913f2a0353"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add trip ownership as nullable so existing rows can be backfilled.
    op.add_column(
        "supplier_deliveries",
        sa.Column("trip_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_supplier_deliveries_trip_id",
        "supplier_deliveries",
        "trips",
        ["trip_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # 2. Backfill every existing row from its supplier list's trip.
    op.execute(
        """
        UPDATE supplier_deliveries
        SET trip_id = (
            SELECT supplier_lists.trip_id
            FROM supplier_lists
            WHERE supplier_lists.id = supplier_deliveries.supplier_list_id
        )
        WHERE trip_id IS NULL
        """
    )

    # 3. Refuse to continue if any row could not be resolved. Assigning an
    #    arbitrary trip here would silently corrupt trip ownership.
    connection = op.get_bind()
    unbackfilled = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM supplier_deliveries WHERE trip_id IS NULL"
        )
    ).scalar_one()

    if unbackfilled:
        raise RuntimeError(
            "Cannot backfill supplier_deliveries.trip_id: "
            f"{unbackfilled} supplier delivery row(s) have no trip resolvable "
            "through their supplier list. Fix these rows before migrating; "
            "no trip was assigned automatically."
        )

    # 4. Only after a successful backfill, require trip ownership.
    op.alter_column(
        "supplier_deliveries",
        "trip_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_index(
        "ix_supplier_deliveries_trip_id",
        "supplier_deliveries",
        ["trip_id"],
    )

    # 5. A slip no longer requires a supplier list or a planned quantity.
    op.alter_column(
        "supplier_deliveries",
        "supplier_list_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "supplier_delivery_items",
        "planned_bags",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 6. Delivery details recorded on the slip itself.
    op.add_column(
        "supplier_deliveries",
        sa.Column("tub_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "supplier_deliveries",
        sa.Column("vehicle", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "supplier_deliveries",
        sa.Column("driver", sa.String(length=100), nullable=True),
    )
    op.create_check_constraint(
        "ck_delivery_tubs_nonnegative",
        "supplier_deliveries",
        "tub_count >= 0",
    )


def downgrade() -> None:
    # The previous schema required every slip to reference a supplier list and
    # every item to carry a planned quantity. It cannot represent independent
    # trip-owned slips, so refuse to destroy that information silently.
    connection = op.get_bind()

    independent_slips = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM supplier_deliveries "
            "WHERE supplier_list_id IS NULL"
        )
    ).scalar_one()
    unplanned_items = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM supplier_delivery_items "
            "WHERE planned_bags IS NULL"
        )
    ).scalar_one()

    if independent_slips or unplanned_items:
        raise RuntimeError(
            "Cannot downgrade: the previous schema cannot represent "
            f"{independent_slips} supplier deliver(y/ies) without a supplier "
            f"list or {unplanned_items} item(s) without a planned quantity. "
            "Re-link or remove these rows before downgrading."
        )

    op.drop_constraint(
        "ck_delivery_tubs_nonnegative",
        "supplier_deliveries",
        type_="check",
    )
    op.drop_column("supplier_deliveries", "driver")
    op.drop_column("supplier_deliveries", "vehicle")
    op.drop_column("supplier_deliveries", "tub_count")

    op.alter_column(
        "supplier_delivery_items",
        "planned_bags",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "supplier_deliveries",
        "supplier_list_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_index(
        "ix_supplier_deliveries_trip_id",
        table_name="supplier_deliveries",
    )
    op.drop_constraint(
        "fk_supplier_deliveries_trip_id",
        "supplier_deliveries",
        type_="foreignkey",
    )
    op.drop_column("supplier_deliveries", "trip_id")
