from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Handover(Base):
    __tablename__ = "handovers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    trip_customer_id: Mapped[int] = mapped_column(
        ForeignKey("trip_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    submit_reference: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    handed_over_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class HandoverLine(Base):
    __tablename__ = "handover_lines"

    __table_args__ = (
        UniqueConstraint(
            "handover_id",
            "fish_type_id",
            name="uq_handover_lines_handover_fish_type",
        ),
        CheckConstraint("bags >= 0", name="ck_handover_lines_bags_nonnegative"),
                CheckConstraint(
            "rate_per_bag >= 0",
            name="ck_handover_lines_rate_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    handover_id: Mapped[int] = mapped_column(
        ForeignKey("handovers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    fish_type_id: Mapped[int] = mapped_column(
        ForeignKey("fish_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    bags: Mapped[int] = mapped_column(Integer, nullable=False)

    rate_per_bag: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )