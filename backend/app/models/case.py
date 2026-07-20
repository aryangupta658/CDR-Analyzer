from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.evidence import EvidenceFile
    from app.models.cdr_record import CDRRecord


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    """
    Stores forensic investigation cases.
    """

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    case_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200)
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="new",
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
    )

    creator: Mapped["User"] = relationship(
        back_populates="cases"
    )

    evidence_files: Mapped[list["EvidenceFile"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )

    cdr_records: Mapped[list["CDRRecord"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )