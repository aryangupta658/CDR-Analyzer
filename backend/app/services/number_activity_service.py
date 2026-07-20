from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord
from app.services.analysis_service import (
    evidence_scope_text,
    get_evidence_records,
    normalize_phone_number,
)


def _records_for_number(
    records: list[CDRRecord],
    phone_number: str | None,
) -> tuple[list[CDRRecord], str | None]:
    """
    Restricts activity to records involving one analysed number.

    The number can be the caller or receiver.  When phone_number is
    omitted, the complete evidence is returned for backwards compatibility.
    """

    if phone_number is None:
        return records, None

    cleaned_number = normalize_phone_number(phone_number)

    if not cleaned_number:
        raise ValueError("Phone number is required for number activity charts.")

    filtered_records: list[CDRRecord] = []

    for record in records:
        caller = normalize_phone_number(record.caller_number)
        receiver = normalize_phone_number(record.receiver_number)

        if cleaned_number in {caller, receiver}:
            filtered_records.append(record)

    return filtered_records, cleaned_number


def get_calls_by_hour(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str | None = None,
) -> dict[str, Any]:
    """
    Groups CDR records by hour of day.

    When a phone number is provided, only records where that number is the
    caller or receiver are included.  This makes the Number Analysis charts
    describe the analysed number instead of the complete evidence file.
    """

    all_records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    records, cleaned_number = _records_for_number(
        records=all_records,
        phone_number=phone_number,
    )

    hourly_statistics = {
        hour: {
            "record_count": 0,
            "total_duration_seconds": 0,
        }
        for hour in range(24)
    }

    for record in records:
        if record.start_datetime is None:
            continue

        hour = record.start_datetime.hour
        hourly_statistics[hour]["record_count"] += 1
        hourly_statistics[hour]["total_duration_seconds"] += int(
            record.duration_seconds or 0
        )

    activity = [
        {
            "hour": hour,
            "record_count": hourly_statistics[hour]["record_count"],
            "total_duration_seconds": hourly_statistics[hour][
                "total_duration_seconds"
            ],
        }
        for hour in range(24)
    ]

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": evidence_scope_text(evidence_id),
        "phone_number": cleaned_number,
        "activity": activity,
    }


def get_calls_by_date(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str | None = None,
) -> dict[str, Any]:
    """
    Groups CDR records by calendar date.

    When a phone number is provided, only records involving that number are
    included.
    """

    all_records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    records, cleaned_number = _records_for_number(
        records=all_records,
        phone_number=phone_number,
    )

    daily_statistics: dict[date, dict[str, int]] = defaultdict(
        lambda: {
            "record_count": 0,
            "total_duration_seconds": 0,
        }
    )

    for record in records:
        if record.start_datetime is None:
            continue

        activity_date = record.start_datetime.date()
        daily_statistics[activity_date]["record_count"] += 1
        daily_statistics[activity_date]["total_duration_seconds"] += int(
            record.duration_seconds or 0
        )

    activity = []

    for activity_date in sorted(daily_statistics):
        statistics = daily_statistics[activity_date]

        activity.append(
            {
                "activity_date": activity_date,
                "record_count": statistics["record_count"],
                "total_duration_seconds": statistics[
                    "total_duration_seconds"
                ],
            }
        )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": evidence_scope_text(evidence_id),
        "phone_number": cleaned_number,
        "activity": activity,
    }