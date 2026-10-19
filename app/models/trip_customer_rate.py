from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TripCustomerRate(Base):
    __tablename__ = "trip_customer_rates"

    __table_args__ = (
        UniqueConstraint(
            "trip_customer_id",
            "fish_type_id",
            name="uq_trip_customer_rates_customer_fish",
        ),
        CheckConstraint(
            "rate_per_bag >= 0",
            name="ck_trip_customer_rates_rate_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

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

    rate_per_bag: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )