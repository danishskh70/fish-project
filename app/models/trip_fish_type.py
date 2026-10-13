
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TripFishType(Base):
    __tablename__ = "trip_fish_types"

    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            "fish_type_id",
            name="uq_trip_fish_types_trip_fish",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fish_type_id: Mapped[int] = mapped_column(
        ForeignKey("fish_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
