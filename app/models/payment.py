from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("method IN ('CASH', 'ONLINE')", name="ck_payments_method"),
        CheckConstraint("kind IN ('ADVANCE', 'PAYMENT')", name="ck_payments_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    trip_customer_id: Mapped[int] = mapped_column(
        ForeignKey("trip_customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    reference: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    method: Mapped[str] = mapped_column(String(10), nullable=False)

    kind: Mapped[str] = mapped_column(String(10), nullable=False)

    paid_at: Mapped[datetime] = mapped_column(
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
