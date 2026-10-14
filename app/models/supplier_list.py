from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SupplierList(Base):
    __tablename__ = "supplier_lists"

    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            "version_number",
            name="uq_supplier_lists_trip_version",
        ),
        CheckConstraint(
            "version_number > 0",
            name="ck_supplier_lists_version_positive",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'FINAL', 'SUPERSEDED')",
            name="ck_supplier_lists_status",
        ),
        Index(
            "uq_supplier_lists_one_final_per_trip",
            "trip_id",
            unique=True,
            postgresql_where=text("status = 'FINAL'"),
            sqlite_where=text("status = 'FINAL'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="DRAFT",
        server_default=text("'DRAFT'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )