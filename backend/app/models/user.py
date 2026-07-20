from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.evidence import EvidenceFile


def current_utc_time() -> datetime:
    """
    Returns the current UTC date and time.
    """

    return datetime.now(timezone.utc)


class User(Base):
    """
    Stores investigator accounts.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    full_name: Mapped[str] = mapped_column(
        String(100)
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255)
    )

    role: Mapped[str] = mapped_column(
        String(30),
        default="investigator",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
    )

    cases: Mapped[list["Case"]] = relationship(
        back_populates="creator"
    )

    uploaded_evidence: Mapped[list["EvidenceFile"]] = relationship(
        back_populates="uploader"
    )