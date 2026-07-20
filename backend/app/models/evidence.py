from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.case import Case
    from app.models.cdr_record import CDRRecord


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceFile(Base):
    """
    Stores metadata about uploaded evidence files.

    The actual file is stored in storage/originals.
    """

    __tablename__ = "evidence_files"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id"),
        index=True,
    )

    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    original_filename: Mapped[str] = mapped_column(
        String(255)
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        unique=True,
    )

    stored_path: Mapped[str] = mapped_column(
        Text
    )

    extension: Mapped[str] = mapped_column(
        String(20)
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger
    )

    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="uploaded",
    )

    record_count: Mapped[int] = mapped_column(
        default=0
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
    )

    imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    case: Mapped["Case"] = relationship(
        back_populates="evidence_files"
    )

    uploader: Mapped["User"] = relationship(
        back_populates="uploaded_evidence"
    )

    cdr_records: Mapped[list["CDRRecord"]] = relationship(
        back_populates="evidence",
        cascade="all, delete-orphan",
    )