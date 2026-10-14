from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SupplierListItem(Base):
    __tablename__ = "supplier_list_items"

    __table_args__ = (
        UniqueConstraint(
            "supplier_list_id",
            "fish_type_id",
            name="uq_supplier_list_items_list_fish_type",
        ),
        CheckConstraint(
            "quantity_bags >= 0",
            name="ck_supplier_list_items_bags_nonnegative",
        ),
        CheckConstraint(
            "tub_count >= 0",
            name="ck_supplier_list_items_tubs_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    supplier_list_id: Mapped[int] = mapped_column(
        ForeignKey("supplier_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    fish_type_id: Mapped[int] = mapped_column(
        ForeignKey("fish_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fish_type_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    quantity_bags: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tub_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )