from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SupplierDelivery(Base):
    __tablename__ = "supplier_deliveries"

    __table_args__ = (
        CheckConstraint(
            "tub_count >= 0",
            name="ck_delivery_tubs_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    supplier_list_id: Mapped[int | None] = mapped_column(
        ForeignKey("supplier_lists.id", ondelete="RESTRICT"),
        nullable=True,
    )

    tub_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    vehicle: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    driver: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class SupplierDeliveryItem(Base):
    __tablename__ = "supplier_delivery_items"

    __table_args__ = (
        UniqueConstraint(
            "delivery_id",
            "fish_type_id",
            name="uq_delivery_items_delivery_fish_type",
        ),
        CheckConstraint("planned_bags >= 0", name="ck_delivery_planned_nonnegative"),
        CheckConstraint("delivered_bags >= 0", name="ck_delivery_delivered_nonnegative"),
        CheckConstraint("rejected_bags >= 0", name="ck_delivery_rejected_nonnegative"),
        CheckConstraint("damaged_bags >= 0", name="ck_delivery_damaged_nonnegative"),
        CheckConstraint(
            "rejected_bags + damaged_bags <= delivered_bags",
            name="ck_delivery_rejected_damaged_within_delivered",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    delivery_id: Mapped[int] = mapped_column(
        ForeignKey("supplier_deliveries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    fish_type_id: Mapped[int] = mapped_column(
        ForeignKey("fish_types.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fish_type_name: Mapped[str] = mapped_column(String(100), nullable=False)

    planned_bags: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivered_bags: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_bags: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    damaged_bags: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
