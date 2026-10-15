from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PackingListItem(Base):
    __tablename__ = "packing_list_items"

    __table_args__ = (
        UniqueConstraint(
            "packing_list_id",
            "fish_type_id",
            name="uq_packing_list_items_list_fish_type",
        ),
        CheckConstraint(
            "quantity_bags >= 0",
            name="ck_packing_list_items_bags_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    packing_list_id: Mapped[int] = mapped_column(
        ForeignKey("packing_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    fish_type_id: Mapped[int] = mapped_column(
        ForeignKey("fish_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity_bags: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )