
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord
from app.schemas.location_analysis import (
    CoLocationRequest,
    IncidentTowerRequest,
)


# =========================================================
# Helper functions
# =========================================================

def normalize_numeric_identifier(
    value: str,
) -> str:
    """
    Cleans phone numbers while retaining digits
    and an optional plus sign.
    """

    if not value:
        return ""

    allowed_characters = set(
        "+0123456789"
    )

    return "".join(
        character
        for character in value.strip()
        if character in allowed_characters
    )


def normalize_datetime_for_database(
    value: datetime,
) -> datetime:
    """
    Converts an aware datetime to naive UTC because
    the current SQLite model stores naive datetime values.
    """

    if value.tzinfo is None:
        return value

    utc_value = value.astimezone(
        timezone.utc
    )

    return utc_value.replace(
        tzinfo=None
    )


def record_phone_numbers(
    record: CDRRecord,
) -> set[str]:
    """
    Returns both phone numbers appearing in one CDR record.
    """

    numbers: set[str] = set()

    if record.caller_number:
        numbers.add(
            record.caller_number
        )

    if record.receiver_number:
        numbers.add(
            record.receiver_number
        )

    return numbers


def clean_optional_text(
    value: Any,
) -> str | None:
    """
    Returns a stripped text value or None for blank values.
    """

    if value is None:
        return None

    cleaned = str(value).strip()

    if not cleaned or cleaned.lower() in {
        "none",
        "nan",
        "null",
    }:
        return None

    return cleaned


def operator_target_number(
    record: CDRRecord,
) -> str:
    """
    Returns the subscriber that owns the operator-CDR technical metadata.

    In the 23-field format, FIRST_CGI, LAST_CGI, coordinates, IMEI and IMSI
    belong to TARGET_NO. For older imported files where TARGET_NO is blank,
    caller_number is used as the legacy fallback.
    """

    target_number = normalize_numeric_identifier(
        clean_optional_text(
            getattr(
                record,
                "target_number",
                None,
            )
        )
        or ""
    )

    if target_number:
        return target_number

    return normalize_numeric_identifier(
        clean_optional_text(
            getattr(
                record,
                "caller_number",
                None,
            )
        )
        or ""
    )


def operator_b_party_number(
    record: CDRRecord,
    target_number: str,
) -> str | None:
    """
    Returns B_PARTY from the operator columns, with a normalized-record
    fallback for older evidence.
    """

    b_party = normalize_numeric_identifier(
        clean_optional_text(
            getattr(
                record,
                "b_party_number",
                None,
            )
        )
        or ""
    )

    if b_party:
        return b_party

    caller = normalize_numeric_identifier(
        clean_optional_text(
            getattr(
                record,
                "caller_number",
                None,
            )
        )
        or ""
    )
    receiver = normalize_numeric_identifier(
        clean_optional_text(
            getattr(
                record,
                "receiver_number",
                None,
            )
        )
        or ""
    )

    if caller and caller != target_number:
        return caller

    if receiver and receiver != target_number:
        return receiver

    return None


def first_cell_id(
    record: CDRRecord,
) -> str | None:
    return clean_optional_text(
        getattr(
            record,
            "first_cell_global_id",
            None,
        )
        or getattr(
            record,
            "cell_id",
            None,
        )
    )


def last_cell_id(
    record: CDRRecord,
) -> str | None:
    return clean_optional_text(
        getattr(
            record,
            "last_cell_global_id",
            None,
        )
        or first_cell_id(record)
    )


def first_coordinate(
    record: CDRRecord,
) -> tuple[float | None, float | None]:
    latitude = getattr(
        record,
        "first_latitude",
        None,
    )
    longitude = getattr(
        record,
        "first_longitude",
        None,
    )

    if latitude is None:
        latitude = getattr(
            record,
            "latitude",
            None,
        )

    if longitude is None:
        longitude = getattr(
            record,
            "longitude",
            None,
        )

    return latitude, longitude


def last_coordinate(
    record: CDRRecord,
) -> tuple[float | None, float | None]:
    first_latitude, first_longitude = (
        first_coordinate(record)
    )

    latitude = getattr(
        record,
        "last_latitude",
        None,
    )
    longitude = getattr(
        record,
        "last_longitude",
        None,
    )

    if latitude is None:
        latitude = first_latitude

    if longitude is None:
        longitude = first_longitude

    return latitude, longitude


def record_imei_value(
    record: CDRRecord,
) -> str | None:
    return clean_optional_text(
        getattr(
            record,
            "imei",
            None,
        )
        or getattr(
            record,
            "imei_esn",
            None,
        )
    )


def record_imsi_value(
    record: CDRRecord,
) -> str | None:
    return clean_optional_text(
        getattr(
            record,
            "imsi",
            None,
        )
        or getattr(
            record,
            "imsi_min",
            None,
        )
    )


# =========================================================
# Tower summary
# =========================================================

def calculate_tower_summary(
    database: Session,
    case_id: int,
    evidence_id: int,
    search: str | None,
    limit: int,
) -> dict[str, Any]:
    """
    Creates a summary of every first CGI/cell ID appearing in one evidence
    file. The table uses the original first and last coordinate fields instead
    of legacy LAC and tower-address columns.
    """

    cell_available = or_(
        and_(
            CDRRecord.cell_id.is_not(None),
            CDRRecord.cell_id != "",
        ),
        and_(
            CDRRecord.first_cell_global_id.is_not(None),
            CDRRecord.first_cell_global_id != "",
        ),
    )

    conditions = [
        CDRRecord.case_id == case_id,
        CDRRecord.evidence_id == evidence_id,
        cell_available,
    ]

    if search:
        search_value = f"%{search.strip()}%"

        conditions.append(
            or_(
                CDRRecord.cell_id.ilike(search_value),
                CDRRecord.first_cell_global_id.ilike(search_value),
                CDRRecord.last_cell_global_id.ilike(search_value),
            )
        )

    records_query = (
        select(CDRRecord)
        .where(and_(*conditions))
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(database.scalars(records_query).all())

    tower_statistics: dict[str, dict[str, Any]] = {}

    for record in records:
        cell_id = (
            record.first_cell_global_id
            or record.cell_id
            or ""
        ).strip()

        if not cell_id:
            continue

        if cell_id not in tower_statistics:
            tower_statistics[cell_id] = {
                "first_coordinates": Counter(),
                "last_coordinates": Counter(),
                "total_records": 0,
                "unique_numbers": set(),
                "first_seen": record.start_datetime,
                "last_seen": record.start_datetime,
            }

        statistics = tower_statistics[cell_id]
        statistics["total_records"] += 1
        statistics["last_seen"] = record.start_datetime
        statistics["unique_numbers"].update(record_phone_numbers(record))

        first_latitude = (
            record.first_latitude
            if record.first_latitude is not None
            else record.latitude
        )
        first_longitude = (
            record.first_longitude
            if record.first_longitude is not None
            else record.longitude
        )
        last_latitude = (
            record.last_latitude
            if record.last_latitude is not None
            else first_latitude
        )
        last_longitude = (
            record.last_longitude
            if record.last_longitude is not None
            else first_longitude
        )

        if first_latitude is not None and first_longitude is not None:
            statistics["first_coordinates"][(
                float(first_latitude),
                float(first_longitude),
            )] += 1

        if last_latitude is not None and last_longitude is not None:
            statistics["last_coordinates"][(
                float(last_latitude),
                float(last_longitude),
            )] += 1

    towers: list[dict[str, Any]] = []

    for cell_id, statistics in tower_statistics.items():
        unique_numbers = sorted(statistics["unique_numbers"])

        first_coordinate = (
            statistics["first_coordinates"].most_common(1)[0][0]
            if statistics["first_coordinates"]
            else (None, None)
        )
        last_coordinate = (
            statistics["last_coordinates"].most_common(1)[0][0]
            if statistics["last_coordinates"]
            else (None, None)
        )

        towers.append(
            {
                "cell_id": cell_id,
                "first_latitude": first_coordinate[0],
                "first_longitude": first_coordinate[1],
                "last_latitude": last_coordinate[0],
                "last_longitude": last_coordinate[1],
                "total_records": statistics["total_records"],
                "unique_number_count": len(unique_numbers),
                "unique_numbers": unique_numbers,
                "first_seen": statistics["first_seen"],
                "last_seen": statistics["last_seen"],
            }
        )

    towers.sort(
        key=lambda item: (
            -item["total_records"],
            item["cell_id"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "tower_count": len(towers),
        "towers": towers[:limit],
    }


# =========================================================
# Tower detail
# =========================================================

def calculate_tower_detail(
    database: Session,
    case_id: int,
    evidence_id: int,
    cell_id: str,
    event_limit: int,
) -> dict[str, Any] | None:
    """
    Returns detailed activity for one cell tower.
    """

    normalized_cell_id = cell_id.strip()

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            CDRRecord.cell_id == normalized_cell_id,
        )
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(
            records_query
        ).all()
    )

    if not records:
        return None

    number_statistics: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:
        for phone_number in record_phone_numbers(record):
            if phone_number not in number_statistics:
                number_statistics[
                    phone_number
                ] = {
                    "record_count": 0,
                    "first_seen": record.start_datetime,
                    "last_seen": record.start_datetime,
                }

            statistics = number_statistics[
                phone_number
            ]

            statistics["record_count"] += 1
            statistics["last_seen"] = (
                record.start_datetime
            )

    number_usage = []

    for phone_number, statistics in number_statistics.items():
        number_usage.append(
            {
                "phone_number": phone_number,
                "record_count": (
                    statistics["record_count"]
                ),
                "first_seen": (
                    statistics["first_seen"]
                ),
                "last_seen": (
                    statistics["last_seen"]
                ),
            }
        )

    number_usage.sort(
        key=lambda item: (
            -item["record_count"],
            item["phone_number"],
        )
    )

    events = []

    for record in records[:event_limit]:
        events.append(
            {
                "record_id": record.id,
                "evidence_id": record.evidence_id,
                "source_row": record.source_row,
                "caller_number": (
                    record.caller_number
                ),
                "receiver_number": (
                    record.receiver_number
                ),
                "event_type": record.event_type,
                "direction": record.direction,
                "start_datetime": (
                    record.start_datetime
                ),
                "duration_seconds": (
                    record.duration_seconds or 0
                ),
                "imei": record.imei,
                "imsi": record.imsi,
            }
        )

    first_record = records[0]

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "cell_id": normalized_cell_id,
        "lac": first_record.lac,
        "tower_address": (
            first_record.tower_address
        ),
        "latitude": first_record.latitude,
        "longitude": first_record.longitude,
        "total_records": len(records),
        "unique_number_count": len(
            number_usage
        ),
        "number_usage": number_usage,
        "first_seen": (
            records[0].start_datetime
        ),
        "last_seen": (
            records[-1].start_datetime
        ),
        "events": events,
    }


# =========================================================
# Number location history
# =========================================================

def calculate_number_location_history(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
    limit: int,
) -> dict[str, Any] | None:
    """
    Creates a chronological operator-CDR location history for one TARGET_NO.

    In the 23-field operator format, FIRST_CGI, LAST_CGI, coordinates, IMEI
    and IMSI belong to TARGET_NO. A B_PARTY match is not treated as proof that
    the B-party device was present at the recorded cells.

    Older evidence without TARGET_NO is still supported by using caller_number
    as the legacy location-owner fallback.
    """

    normalized_number = normalize_numeric_identifier(
        phone_number
    )

    if not normalized_number:
        return None

    target_number_missing = or_(
        CDRRecord.target_number.is_(None),
        CDRRecord.target_number == "",
    )

    number_ownership_condition = or_(
        CDRRecord.target_number
        == normalized_number,
        and_(
            target_number_missing,
            CDRRecord.caller_number
            == normalized_number,
        ),
    )

    location_available = or_(
        and_(
            CDRRecord.first_cell_global_id.is_not(None),
            CDRRecord.first_cell_global_id != "",
        ),
        and_(
            CDRRecord.last_cell_global_id.is_not(None),
            CDRRecord.last_cell_global_id != "",
        ),
        and_(
            CDRRecord.cell_id.is_not(None),
            CDRRecord.cell_id != "",
        ),
    )

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            number_ownership_condition,
            location_available,
        )
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(
            records_query
        ).all()
    )

    if not records:
        return None

    history: list[dict[str, Any]] = []

    unique_first_cells: set[str] = set()
    unique_last_cells: set[str] = set()
    unique_all_cells: set[str] = set()

    previous_last_cell: str | None = None

    for record in records[:limit]:
        target_number = (
            operator_target_number(record)
            or normalized_number
        )
        b_party_number = (
            operator_b_party_number(
                record,
                target_number,
            )
        )

        current_first_cell = first_cell_id(
            record
        )
        current_last_cell = last_cell_id(
            record
        )

        first_latitude, first_longitude = (
            first_coordinate(record)
        )
        last_latitude, last_longitude = (
            last_coordinate(record)
        )

        if current_first_cell:
            unique_first_cells.add(
                current_first_cell
            )
            unique_all_cells.add(
                current_first_cell
            )

        if current_last_cell:
            unique_last_cells.add(
                current_last_cell
            )
            unique_all_cells.add(
                current_last_cell
            )

        changed_during_record = (
            current_first_cell is not None
            and current_last_cell is not None
            and current_first_cell
            != current_last_cell
        )

        changed_since_previous_record = (
            previous_last_cell is not None
            and current_first_cell is not None
            and previous_last_cell
            != current_first_cell
        )

        location_changed = (
            changed_during_record
            or changed_since_previous_record
        )

        history.append(
            {
                "record_id": record.id,
                "evidence_id": record.evidence_id,
                "source_row": record.source_row,
                "pan_no": clean_optional_text(
                    getattr(
                        record,
                        "pan_no",
                        None,
                    )
                ),
                "target_number": target_number,
                "call_type": clean_optional_text(
                    getattr(
                        record,
                        "call_type",
                        None,
                    )
                ),
                "connection_type": clean_optional_text(
                    getattr(
                        record,
                        "connection_type",
                        None,
                    )
                    or getattr(
                        record,
                        "service_type",
                        None,
                    )
                    or getattr(
                        record,
                        "event_type",
                        None,
                    )
                ),
                "b_party_number": (
                    b_party_number
                ),
                "start_datetime": (
                    record.start_datetime
                ),
                "call_time_raw": clean_optional_text(
                    getattr(
                        record,
                        "call_time_raw",
                        None,
                    )
                ),
                "duration_seconds": int(
                    record.duration_seconds or 0
                ),
                "first_cell_global_id": (
                    current_first_cell
                ),
                "first_latitude": (
                    first_latitude
                ),
                "first_longitude": (
                    first_longitude
                ),
                "last_cell_global_id": (
                    current_last_cell
                ),
                "last_latitude": (
                    last_latitude
                ),
                "last_longitude": (
                    last_longitude
                ),
                "imei": record_imei_value(
                    record
                ),
                "imsi": record_imsi_value(
                    record
                ),
                "location_changed": (
                    location_changed
                ),
            }
        )

        if current_last_cell:
            previous_last_cell = (
                current_last_cell
            )
        elif current_first_cell:
            previous_last_cell = (
                current_first_cell
            )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "phone_number": normalized_number,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "association_basis": (
            "FIRST_CGI, LAST_CGI, coordinates, IMEI and IMSI are "
            "associated with TARGET_NO in the 23-field operator CDR. "
            "B_PARTY records are not treated as the B-party location."
        ),
        "total_location_records": len(
            records
        ),
        "unique_tower_count": len(
            unique_all_cells
        ),
        "unique_first_cell_count": len(
            unique_first_cells
        ),
        "unique_last_cell_count": len(
            unique_last_cells
        ),
        "first_seen": (
            records[0].start_datetime
        ),
        "last_seen": (
            records[-1].start_datetime
        ),
        "history": history,
    }


# =========================================================
# Co-location analysis
# =========================================================

def calculate_co_location(
    database: Session,
    case_id: int,
    evidence_id: int,
    request: CoLocationRequest,
) -> dict[str, Any]:
    """
    Finds selected numbers appearing at the same cell tower
    within a selected time tolerance.

    This is tower-level co-location, not exact GPS proof.
    """

    target_numbers = []

    for number in request.target_numbers:
        normalized = normalize_numeric_identifier(
            number
        )

        if (
            normalized
            and normalized not in target_numbers
        ):
            target_numbers.append(
                normalized
            )

    if len(target_numbers) < 2:
        raise ValueError(
            "At least two unique valid numbers are required."
        )

    target_set = set(
        target_numbers
    )

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            CDRRecord.cell_id.is_not(None),
            CDRRecord.cell_id != "",
            or_(
                CDRRecord.caller_number.in_(
                    target_numbers
                ),
                CDRRecord.receiver_number.in_(
                    target_numbers
                ),
            ),
        )
        .order_by(
            CDRRecord.cell_id.asc(),
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(
            records_query
        ).all()
    )

    tower_events: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    tower_metadata: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:
        if not record.cell_id:
            continue

        tower_metadata.setdefault(
            record.cell_id,
            {
                "lac": record.lac,
                "tower_address": (
                    record.tower_address
                ),
                "latitude": record.latitude,
                "longitude": record.longitude,
            },
        )

        matching_numbers = (
            record_phone_numbers(record)
            & target_set
        )

        for phone_number in matching_numbers:
            tower_events[
                record.cell_id
            ].append(
                {
                    "phone_number": phone_number,
                    "event_datetime": (
                        record.start_datetime
                    ),
                    "record_id": record.id,
                    "source_row": record.source_row,
                }
            )

    tolerance = timedelta(
        minutes=request.tolerance_minutes
    )

    matches = []
    seen_signatures: set[tuple] = set()

    for cell_id, events in tower_events.items():
        events.sort(
            key=lambda item: (
                item["event_datetime"],
                item["record_id"],
            )
        )

        for start_index, start_event in enumerate(events):
            window_start = start_event[
                "event_datetime"
            ]

            window_end = (
                window_start + tolerance
            )

            window_events = []

            for candidate in events[start_index:]:
                if (
                    candidate["event_datetime"]
                    > window_end
                ):
                    break

                window_events.append(
                    candidate
                )

            matched_numbers = sorted(
                {
                    event["phone_number"]
                    for event in window_events
                }
            )

            if len(matched_numbers) < 2:
                continue

            signature = (
                cell_id,
                tuple(matched_numbers),
                window_start,
            )

            if signature in seen_signatures:
                continue

            seen_signatures.add(
                signature
            )

            metadata = tower_metadata[
                cell_id
            ]

            matches.append(
                {
                    "cell_id": cell_id,
                    "lac": metadata["lac"],
                    "tower_address": (
                        metadata["tower_address"]
                    ),
                    "latitude": (
                        metadata["latitude"]
                    ),
                    "longitude": (
                        metadata["longitude"]
                    ),
                    "matched_number_count": len(
                        matched_numbers
                    ),
                    "matched_numbers": (
                        matched_numbers
                    ),
                    "window_start": (
                        window_start
                    ),
                    "window_end": (
                        window_end
                    ),
                    "events": window_events,
                }
            )

    matches.sort(
        key=lambda item: (
            -item["matched_number_count"],
            item["window_start"],
            item["cell_id"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "requested_numbers": (
            target_numbers
        ),
        "tolerance_minutes": (
            request.tolerance_minutes
        ),
        "match_count": len(matches),
        "matches": matches[
            :request.limit
        ],
    }


# =========================================================
# Incident tower analysis
# =========================================================

def calculate_incident_tower_analysis(
    database: Session,
    case_id: int,
    evidence_id: int,
    request: IncidentTowerRequest,
) -> dict[str, Any]:
    """
    Finds records at selected towers around
    an incident timestamp.
    """

    incident_datetime = (
        normalize_datetime_for_database(
            request.incident_datetime
        )
    )

    window_start = (
        incident_datetime
        - timedelta(
            minutes=request.minutes_before
        )
    )

    window_end = (
        incident_datetime
        + timedelta(
            minutes=request.minutes_after
        )
    )

    normalized_numbers: list[str] | None = None

    conditions = [
        CDRRecord.case_id == case_id,
        CDRRecord.evidence_id == evidence_id,
        CDRRecord.cell_id.in_(
            request.cell_ids
        ),
        CDRRecord.start_datetime
        >= window_start,
        CDRRecord.start_datetime
        <= window_end,
    ]

    if request.phone_numbers:
        normalized_numbers = []

        for number in request.phone_numbers:
            normalized = (
                normalize_numeric_identifier(
                    number
                )
            )

            if (
                normalized
                and normalized not in normalized_numbers
            ):
                normalized_numbers.append(
                    normalized
                )

        if normalized_numbers:
            conditions.append(
                or_(
                    CDRRecord.caller_number.in_(
                        normalized_numbers
                    ),
                    CDRRecord.receiver_number.in_(
                        normalized_numbers
                    ),
                )
            )

    records_query = (
        select(CDRRecord)
        .where(
            and_(*conditions)
        )
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(
            records_query
        ).all()
    )

    total_matching_records = len(
        records
    )

    returned_records = records[
        :request.limit
    ]

    events = []
    unique_numbers: set[str] = set()

    for record in returned_records:
        unique_numbers.update(
            record_phone_numbers(record)
        )

        relative_seconds = int(
            (
                record.start_datetime
                - incident_datetime
            ).total_seconds()
        )

        if relative_seconds < 0:
            phase = "before_incident"
        elif relative_seconds == 0:
            phase = "at_incident"
        else:
            phase = "after_incident"

        events.append(
            {
                "record_id": record.id,
                "evidence_id": record.evidence_id,
                "source_row": record.source_row,
                "caller_number": (
                    record.caller_number
                ),
                "receiver_number": (
                    record.receiver_number
                ),
                "start_datetime": (
                    record.start_datetime
                ),
                "event_type": record.event_type,
                "direction": record.direction,
                "duration_seconds": (
                    record.duration_seconds or 0
                ),
                "cell_id": record.cell_id,
                "lac": record.lac,
                "tower_address": (
                    record.tower_address
                ),
                "latitude": record.latitude,
                "longitude": record.longitude,
                "imei": record.imei,
                "imsi": record.imsi,
                "relative_seconds": (
                    relative_seconds
                ),
                "phase": phase,
            }
        )

    sorted_numbers = sorted(
        unique_numbers
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "incident_datetime": (
            incident_datetime
        ),
        "window_start": window_start,
        "window_end": window_end,
        "requested_cell_ids": (
            request.cell_ids
        ),
        "requested_phone_numbers": (
            normalized_numbers
        ),
        "total_matching_records": (
            total_matching_records
        ),
        "returned_record_count": len(
            returned_records
        ),
        "unique_number_count": len(
            sorted_numbers
        ),
        "unique_numbers": sorted_numbers,
        "events": events,
    }