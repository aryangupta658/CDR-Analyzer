from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.case import Case
    from app.models.evidence import EvidenceFile


class CDRRecord(Base):
    __tablename__ = "cdr_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="CASCADE"), nullable=False, index=True
    )

    case: Mapped["Case"] = relationship("Case", back_populates="cdr_records")
    evidence: Mapped["EvidenceFile"] = relationship(
        "EvidenceFile", back_populates="cdr_records"
    )

    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Normalized fields used by the existing analysis services.
    caller_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    receiver_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    direction: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    start_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    imei: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    imsi: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    cell_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    lac: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    tower_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_provider: Mapped[str | None] = mapped_column(String(150), nullable=True)
    roaming: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)

    # Original 23-field operator CDR values.
    pan_no: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    target_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    call_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    connection_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    b_party_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    lrn_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lrn_translation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    call_date_raw: Mapped[str | None] = mapped_column(String(50), nullable=True)
    call_time_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)

    first_bts_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_cell_global_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    first_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_bts_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_cell_global_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    last_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    sms_centre_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    imei_esn: Mapped[str | None] = mapped_column(String(50), nullable=True)
    imsi_min: Mapped[str | None] = mapped_column(String(50), nullable=True)
    call_forwarding_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    roaming_network_circle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    switch_msc_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    in_tg: Mapped[str | None] = mapped_column(String(100), nullable=True)
    out_tg: Mapped[str | None] = mapped_column(String(100), nullable=True)


Index(
    "ix_cdr_case_evidence_datetime",
    CDRRecord.case_id,
    CDRRecord.evidence_id,
    CDRRecord.start_datetime,
)
Index(
    "ix_cdr_case_evidence_caller",
    CDRRecord.case_id,
    CDRRecord.evidence_id,
    CDRRecord.caller_number,
)
Index(
    "ix_cdr_case_evidence_receiver",
    CDRRecord.case_id,
    CDRRecord.evidence_id,
    CDRRecord.receiver_number,
)
