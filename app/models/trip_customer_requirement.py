
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TripCustomerRequirement(Base):
    __tablename__ = "trip_customer_requirements"

    __table_args__ = (
        UniqueConstraint(
            "trip_customer_id",
            "fish_type_id",
            name="uq_trip_customer_requirement_fish_type",
        ),
        CheckConstraint(
            "quantity_bags > 0",
            name="ck_trip_customer_requirement_positive_quantity",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    trip_customer_id: Mapped[int] = mapped_column(
        ForeignKey("trip_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fish_type_id: Mapped[int] = mapped_column(
        ForeignKey("fish_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    quantity_bags: Mapped[int] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
