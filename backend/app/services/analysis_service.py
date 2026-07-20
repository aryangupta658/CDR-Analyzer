from collections import defaultdict, deque
from datetime import date, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord


# =========================================================
# Helper functions
# =========================================================

def normalize_phone_number(
    phone_number: str | None,
) -> str:
    """
    Keeps only digits and an optional plus sign.

    This follows the same basic cleaning approach used
    during CDR import.
    """

    if not phone_number:
        return ""

    allowed_characters = set(
        "+0123456789"
    )

    return "".join(
        character
        for character in phone_number.strip()
        if character in allowed_characters
    )


def get_evidence_records(
    database: Session,
    case_id: int,
    evidence_id: int,
) -> list[CDRRecord]:
    """
    Returns normalized CDR records belonging to one case
    and one selected evidence file.
    """

    query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
        )
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    return list(
        database.scalars(query).all()
    )


def evidence_scope_text(
    evidence_id: int,
) -> str:
    """
    Returns a consistent evidence-scope explanation.
    """

    return (
        "Results are limited to selected "
        f"evidence file ID {evidence_id}."
    )


# =========================================================
# Evidence summary
# =========================================================

def calculate_case_summary(
    database: Session,
    case_id: int,
    evidence_id: int,
) -> dict[str, Any]:
    """
    Calculates high-level summary statistics for one
    selected evidence file.
    """

    records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    total_records = len(records)

    total_calls = 0
    total_sms = 0
    total_other_events = 0

    outgoing_records = 0
    incoming_records = 0

    unique_numbers: set[str] = set()
    unique_imeis: set[str] = set()
    unique_imsis: set[str] = set()
    unique_cell_ids: set[str] = set()

    total_duration_seconds = 0

    first_activity: datetime | None = None
    last_activity: datetime | None = None

    for record in records:
        event_type = (
            record.event_type or ""
        ).strip().lower()

        if event_type == "call":
            total_calls += 1
        elif event_type == "sms":
            total_sms += 1
        else:
            total_other_events += 1

        direction = (
            record.direction or ""
        ).strip().lower()

        if direction == "outgoing":
            outgoing_records += 1
        elif direction == "incoming":
            incoming_records += 1

        if record.caller_number:
            unique_numbers.add(
                record.caller_number
            )

        if record.receiver_number:
            unique_numbers.add(
                record.receiver_number
            )

        if record.imei:
            unique_imeis.add(
                record.imei
            )

        if record.imsi:
            unique_imsis.add(
                record.imsi
            )

        if record.cell_id:
            unique_cell_ids.add(
                record.cell_id
            )

        total_duration_seconds += int(
            record.duration_seconds or 0
        )

        if record.start_datetime:
            if first_activity is None:
                first_activity = (
                    record.start_datetime
                )

            last_activity = (
                record.start_datetime
            )

    average_duration_seconds = (
        round(
            total_duration_seconds
            / total_records,
            2,
        )
        if total_records > 0
        else 0.0
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            evidence_scope_text(
                evidence_id
            )
        ),
        "total_records": total_records,
        "total_calls": total_calls,
        "total_sms": total_sms,
        "total_other_events": (
            total_other_events
        ),
        "outgoing_records": (
            outgoing_records
        ),
        "incoming_records": (
            incoming_records
        ),
        "unique_numbers": len(
            unique_numbers
        ),
        "unique_imeis": len(
            unique_imeis
        ),
        "unique_imsis": len(
            unique_imsis
        ),
        "unique_cell_ids": len(
            unique_cell_ids
        ),
        "total_duration_seconds": (
            total_duration_seconds
        ),
        "average_duration_seconds": (
            average_duration_seconds
        ),
        "first_activity": (
            first_activity
        ),
        "last_activity": (
            last_activity
        ),
    }


# =========================================================
# Number list
# =========================================================

def calculate_number_list(
    database: Session,
    case_id: int,
    evidence_id: int,
    search_text: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Builds a unique phone-number list from one selected
    evidence file.
    """

    records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    number_statistics: dict[
        str,
        dict[str, Any],
    ] = {}

    def default_statistics() -> dict[str, Any]:
        return {
            "total_records": 0,
            "outgoing_records": 0,
            "incoming_records": 0,
            "total_duration_seconds": 0,
            "first_activity": None,
            "last_activity": None,
        }

    for record in records:
        caller = normalize_phone_number(
            record.caller_number
        )

        receiver = normalize_phone_number(
            record.receiver_number
        )

        duration = int(
            record.duration_seconds or 0
        )

        activity_time = (
            record.start_datetime
        )

        if caller:
            if caller not in number_statistics:
                number_statistics[
                    caller
                ] = default_statistics()

            caller_stats = (
                number_statistics[caller]
            )

            caller_stats[
                "total_records"
            ] += 1

            caller_stats[
                "outgoing_records"
            ] += 1

            caller_stats[
                "total_duration_seconds"
            ] += duration

            if (
                caller_stats[
                    "first_activity"
                ]
                is None
            ):
                caller_stats[
                    "first_activity"
                ] = activity_time

            caller_stats[
                "last_activity"
            ] = activity_time

        if receiver:
            if (
                receiver
                not in number_statistics
            ):
                number_statistics[
                    receiver
                ] = default_statistics()

            receiver_stats = (
                number_statistics[
                    receiver
                ]
            )

            receiver_stats[
                "total_records"
            ] += 1

            receiver_stats[
                "incoming_records"
            ] += 1

            receiver_stats[
                "total_duration_seconds"
            ] += duration

            if (
                receiver_stats[
                    "first_activity"
                ]
                is None
            ):
                receiver_stats[
                    "first_activity"
                ] = activity_time

            receiver_stats[
                "last_activity"
            ] = activity_time

    normalized_search = (
        normalize_phone_number(
            search_text
        )
        if search_text
        else ""
    )

    items: list[dict[str, Any]] = []

    for (
        phone_number,
        statistics,
    ) in number_statistics.items():
        if (
            normalized_search
            and normalized_search
            not in phone_number
        ):
            continue

        items.append(
            {
                "phone_number": (
                    phone_number
                ),
                **statistics,
            }
        )

    items.sort(
        key=lambda item: (
            -item["total_records"],
            item["phone_number"],
        )
    )

    total_numbers = len(items)

    paginated_items = items[
        offset: offset + limit
    ]

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            evidence_scope_text(
                evidence_id
            )
        ),
        "total_numbers": total_numbers,
        "offset": offset,
        "limit": limit,
        "numbers": paginated_items,
    }


# =========================================================
# Single-number analysis
# =========================================================

def calculate_number_analysis(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
) -> dict[str, Any] | None:
    """
    Creates a detailed profile for one phone number.
    """

    normalized_number = (
        normalize_phone_number(
            phone_number
        )
    )

    if not normalized_number:
        return None

    query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id
            == evidence_id,
            or_(
                CDRRecord.caller_number
                == normalized_number,
                CDRRecord.receiver_number
                == normalized_number,
            ),
        )
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(query).all()
    )

    if not records:
        return None

    outgoing_records = 0
    incoming_records = 0

    outgoing_calls = 0
    incoming_calls = 0

    sms_sent = 0
    sms_received = 0

    missed_or_zero_duration_calls = 0

    contacts: set[str] = set()
    imeis: set[str] = set()
    imsis: set[str] = set()
    cell_ids: set[str] = set()

    total_duration_seconds = 0

    for record in records:
        event_type = (
            record.event_type or ""
        ).strip().lower()

        duration = int(
            record.duration_seconds or 0
        )

        total_duration_seconds += (
            duration
        )

        is_outgoing = (
            record.caller_number
            == normalized_number
        )

        is_incoming = (
            record.receiver_number
            == normalized_number
        )

        if is_outgoing:
            outgoing_records += 1

            if record.receiver_number:
                contacts.add(
                    record.receiver_number
                )

            if event_type == "call":
                outgoing_calls += 1
            elif event_type == "sms":
                sms_sent += 1

        if is_incoming:
            incoming_records += 1

            if record.caller_number:
                contacts.add(
                    record.caller_number
                )

            if event_type == "call":
                incoming_calls += 1
            elif event_type == "sms":
                sms_received += 1

        if (
            event_type == "call"
            and duration == 0
        ):
            missed_or_zero_duration_calls += 1

        record_target_number = normalize_phone_number(
            record.target_number
        )

        technical_metadata_belongs_to_number = (
            not record_target_number
            or record_target_number == normalized_number
        )

        if technical_metadata_belongs_to_number:
            imei_value = (
                record.imei
                or record.imei_esn
                or ""
            ).strip()

            imsi_value = (
                record.imsi
                or record.imsi_min
                or ""
            ).strip()

            cell_id_value = (
                record.cell_id
                or record.first_cell_global_id
                or ""
            ).strip()

            if imei_value:
                imeis.add(imei_value)

            if imsi_value:
                imsis.add(imsi_value)

            if cell_id_value:
                cell_ids.add(cell_id_value)

    contacts.discard(
        normalized_number
    )

    total_records = len(records)

    average_duration_seconds = (
        round(
            total_duration_seconds
            / total_records,
            2,
        )
        if total_records > 0
        else 0.0
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            evidence_scope_text(
                evidence_id
            )
        ),
        "phone_number": (
            normalized_number
        ),
        "total_records": total_records,
        "outgoing_records": (
            outgoing_records
        ),
        "incoming_records": (
            incoming_records
        ),
        "outgoing_calls": (
            outgoing_calls
        ),
        "incoming_calls": (
            incoming_calls
        ),
        "sms_sent": sms_sent,
        "sms_received": sms_received,
        "missed_or_zero_duration_calls": (
            missed_or_zero_duration_calls
        ),
        "unique_contacts": len(
            contacts
        ),
        "unique_imeis": len(
            imeis
        ),
        "unique_imsis": len(
            imsis
        ),
        "unique_cell_ids": len(
            cell_ids
        ),
        "imei_values": sorted(imeis),
        "imsi_values": sorted(imsis),
        "total_duration_seconds": (
            total_duration_seconds
        ),
        "average_duration_seconds": (
            average_duration_seconds
        ),
        "first_activity": (
            records[0].start_datetime
        ),
        "last_activity": (
            records[-1].start_datetime
        ),
    }


# =========================================================
# Top contacts
# =========================================================

def calculate_top_contacts(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
    limit: int = 10,
) -> dict[str, Any] | None:
    """
    Finds the most active contacts for one phone number.
    """

    normalized_number = (
        normalize_phone_number(
            phone_number
        )
    )

    if not normalized_number:
        return None

    query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id
            == evidence_id,
            or_(
                CDRRecord.caller_number
                == normalized_number,
                CDRRecord.receiver_number
                == normalized_number,
            ),
        )
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(query).all()
    )

    if not records:
        return None

    contact_statistics: dict[
        str,
        dict[str, Any],
    ] = {}

    def default_contact() -> dict[str, Any]:
        return {
            "total_records": 0,
            "outgoing_records": 0,
            "incoming_records": 0,
            "total_duration_seconds": 0,
            "first_contact": None,
            "last_contact": None,
        }

    for record in records:
        if (
            record.caller_number
            == normalized_number
        ):
            contact_number = (
                record.receiver_number
            )

            direction_key = (
                "outgoing_records"
            )
        else:
            contact_number = (
                record.caller_number
            )

            direction_key = (
                "incoming_records"
            )

        contact_number = (
            normalize_phone_number(
                contact_number
            )
        )

        if (
            not contact_number
            or contact_number
            == normalized_number
        ):
            continue

        if (
            contact_number
            not in contact_statistics
        ):
            contact_statistics[
                contact_number
            ] = default_contact()

        statistics = (
            contact_statistics[
                contact_number
            ]
        )

        statistics[
            "total_records"
        ] += 1

        statistics[
            direction_key
        ] += 1

        statistics[
            "total_duration_seconds"
        ] += int(
            record.duration_seconds or 0
        )

        if (
            statistics[
                "first_contact"
            ]
            is None
        ):
            statistics[
                "first_contact"
            ] = record.start_datetime

        statistics[
            "last_contact"
        ] = record.start_datetime

    items: list[dict[str, Any]] = []

    for (
        contact_number,
        statistics,
    ) in contact_statistics.items():
        total_records = (
            statistics[
                "total_records"
            ]
        )

        average_duration = (
            round(
                statistics[
                    "total_duration_seconds"
                ]
                / total_records,
                2,
            )
            if total_records > 0
            else 0.0
        )

        items.append(
            {
                "contact_number": (
                    contact_number
                ),
                **statistics,
                "average_duration_seconds": (
                    average_duration
                ),
            }
        )

    items.sort(
        key=lambda item: (
            -item["total_records"],
            -item[
                "total_duration_seconds"
            ],
            item["contact_number"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            evidence_scope_text(
                evidence_id
            )
        ),
        "phone_number": (
            normalized_number
        ),
        "contacts": items[:limit],
    }


# =========================================================
# Direct-contact communication timeline
# =========================================================

def calculate_contact_timeline(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
    contact_number: str,
) -> dict[str, Any] | None:
    """
    Returns every direct CDR record exchanged between one
    analysed number and one selected contact.

    Records are ordered from the earliest communication to
    the latest communication so the frontend can display a
    clear contact timeline.
    """

    normalized_number = normalize_phone_number(
        phone_number
    )
    normalized_contact = normalize_phone_number(
        contact_number
    )

    if (
        not normalized_number
        or not normalized_contact
        or normalized_number == normalized_contact
    ):
        return None

    query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            or_(
                (
                    CDRRecord.caller_number
                    == normalized_number
                )
                & (
                    CDRRecord.receiver_number
                    == normalized_contact
                ),
                (
                    CDRRecord.caller_number
                    == normalized_contact
                )
                & (
                    CDRRecord.receiver_number
                    == normalized_number
                ),
            ),
        )
        .order_by(
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(query).all()
    )

    if not records:
        return None

    timeline_records: list[dict[str, Any]] = []
    outgoing_records = 0
    incoming_records = 0

    for record in records:
        if (
            record.caller_number
            == normalized_number
        ):
            relative_direction = "outgoing"
            outgoing_records += 1
        elif (
            record.receiver_number
            == normalized_number
        ):
            relative_direction = "incoming"
            incoming_records += 1
        else:
            relative_direction = "unknown"

        timeline_records.append(
            {
                "record_id": record.id,
                "source_row": record.source_row,
                "start_datetime": (
                    record.start_datetime
                ),
                "end_datetime": (
                    record.end_datetime
                ),
                "direction": (
                    relative_direction
                ),
                "event_type": (
                    record.event_type
                    or record.service_type
                    or record.connection_type
                ),
                "caller_number": (
                    record.caller_number
                ),
                "receiver_number": (
                    record.receiver_number
                ),
                "duration_seconds": int(
                    record.duration_seconds or 0
                ),
                "pan_no": record.pan_no,
                "target_number": (
                    record.target_number
                ),
                "call_type": (
                    record.call_type
                ),
                "connection_type": (
                    record.connection_type
                ),
                "b_party_number": (
                    record.b_party_number
                ),
                "lrn_number": (
                    record.lrn_number
                ),
                "lrn_translation": (
                    record.lrn_translation
                ),
                "first_cell_global_id": (
                    record.first_cell_global_id
                    or record.cell_id
                ),
                "first_latitude": (
                    record.first_latitude
                    if record.first_latitude is not None
                    else record.latitude
                ),
                "first_longitude": (
                    record.first_longitude
                    if record.first_longitude is not None
                    else record.longitude
                ),
                "last_cell_global_id": (
                    record.last_cell_global_id
                    or record.cell_id
                ),
                "last_latitude": (
                    record.last_latitude
                    if record.last_latitude is not None
                    else record.latitude
                ),
                "last_longitude": (
                    record.last_longitude
                    if record.last_longitude is not None
                    else record.longitude
                ),
                "sms_centre_number": (
                    record.sms_centre_number
                ),
                "imei": (
                    record.imei
                    or record.imei_esn
                ),
                "imsi": (
                    record.imsi
                    or record.imsi_min
                ),
                "call_forwarding_number": (
                    record.call_forwarding_number
                ),
                "roaming": record.roaming,
                "roaming_network_circle": (
                    record.roaming_network_circle
                ),
                "switch_msc_id": (
                    record.switch_msc_id
                ),
                "in_tg": record.in_tg,
                "out_tg": record.out_tg,
            }
        )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": evidence_scope_text(
            evidence_id
        ),
        "phone_number": normalized_number,
        "contact_number": normalized_contact,
        "total_records": len(
            timeline_records
        ),
        "outgoing_records": (
            outgoing_records
        ),
        "incoming_records": (
            incoming_records
        ),
        "first_contact": (
            records[0].start_datetime
        ),
        "last_contact": (
            records[-1].start_datetime
        ),
        "records": timeline_records,
    }


# =========================================================
# Activity by hour
# =========================================================

def calculate_calls_by_hour(
    database: Session,
    case_id: int,
    evidence_id: int,
) -> dict[str, Any]:
    """
    Groups selected evidence records into hours 0–23.
    """

    records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    hourly_statistics = {
        hour: {
            "record_count": 0,
            "total_duration_seconds": 0,
        }
        for hour in range(24)
    }

    for record in records:
        if not record.start_datetime:
            continue

        hour = (
            record.start_datetime.hour
        )

        hourly_statistics[
            hour
        ][
            "record_count"
        ] += 1

        hourly_statistics[
            hour
        ][
            "total_duration_seconds"
        ] += int(
            record.duration_seconds or 0
        )

    activity = []

    for hour in range(24):
        activity.append(
            {
                "hour": hour,
                "record_count": (
                    hourly_statistics[
                        hour
                    ][
                        "record_count"
                    ]
                ),
                "total_duration_seconds": (
                    hourly_statistics[
                        hour
                    ][
                        "total_duration_seconds"
                    ]
                ),
            }
        )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            evidence_scope_text(
                evidence_id
            )
        ),
        "activity": activity,
    }


# =========================================================
# Activity by date
# =========================================================

def calculate_calls_by_date(
    database: Session,
    case_id: int,
    evidence_id: int,
) -> dict[str, Any]:
    """
    Groups selected evidence records by calendar date.
    """

    records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    daily_statistics: dict[
        date,
        dict[str, int],
    ] = defaultdict(
        lambda: {
            "record_count": 0,
            "total_duration_seconds": 0,
        }
    )

    for record in records:
        if not record.start_datetime:
            continue

        activity_date = (
            record.start_datetime.date()
        )

        daily_statistics[
            activity_date
        ][
            "record_count"
        ] += 1

        daily_statistics[
            activity_date
        ][
            "total_duration_seconds"
        ] += int(
            record.duration_seconds or 0
        )

    activity = []

    for activity_date in sorted(
        daily_statistics.keys()
    ):
        statistics = (
            daily_statistics[
                activity_date
            ]
        )

        activity.append(
            {
                "activity_date": (
                    activity_date
                ),
                "record_count": (
                    statistics[
                        "record_count"
                    ]
                ),
                "total_duration_seconds": (
                    statistics[
                        "total_duration_seconds"
                    ]
                ),
            }
        )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            evidence_scope_text(
                evidence_id
            )
        ),
        "activity": activity,
    }


# =========================================================
# Multi-level contact network
# =========================================================

def build_contact_network(
    database: Session,
    case_id: int,
    evidence_id: int,
    root_number: str,
    depth: int = 2,
    per_number_limit: int = 10,
    maximum_nodes: int = 100,
) -> dict[str, Any]:
    """
    Builds a multi-level communication network.

    Depth 1:
        Direct contacts of the selected root number.

    Depth 2:
        Direct contacts plus contacts of those contacts.

    Depth 3:
        Adds one additional relationship level.
    """

    cleaned_root_number = (
        normalize_phone_number(
            root_number
        )
    )

    if not cleaned_root_number:
        raise ValueError(
            "Root phone number is required."
        )

    depth = max(
        1,
        min(int(depth), 3),
    )

    per_number_limit = max(
        1,
        min(
            int(per_number_limit),
            50,
        ),
    )

    maximum_nodes = max(
        2,
        min(
            int(maximum_nodes),
            500,
        ),
    )

    records = get_evidence_records(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    adjacency: dict[
        str,
        dict[str, dict[str, int]],
    ] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "total_records": 0,
                "total_calls": 0,
                "total_sms": 0,
                "total_duration_seconds": 0,
            }
        )
    )

    number_totals: dict[
        str,
        dict[str, int],
    ] = defaultdict(
        lambda: {
            "total_records": 0,
            "total_duration_seconds": 0,
        }
    )

    for record in records:
        caller = normalize_phone_number(
            record.caller_number
        )

        receiver = normalize_phone_number(
            record.receiver_number
        )

        if (
            not caller
            or not receiver
            or caller == receiver
        ):
            continue

        duration = int(
            record.duration_seconds or 0
        )

        event_type = (
            record.event_type or ""
        ).strip().lower()

        number_totals[
            caller
        ][
            "total_records"
        ] += 1

        number_totals[
            receiver
        ][
            "total_records"
        ] += 1

        number_totals[
            caller
        ][
            "total_duration_seconds"
        ] += duration

        number_totals[
            receiver
        ][
            "total_duration_seconds"
        ] += duration

        forward = (
            adjacency[
                caller
            ][receiver]
        )

        reverse = (
            adjacency[
                receiver
            ][caller]
        )

        for relation in (
            forward,
            reverse,
        ):
            relation[
                "total_records"
            ] += 1

            relation[
                "total_duration_seconds"
            ] += duration

            if event_type == "call":
                relation[
                    "total_calls"
                ] += 1

            elif event_type == "sms":
                relation[
                    "total_sms"
                ] += 1

    if (
        cleaned_root_number
        not in adjacency
    ):
        return {
            "case_id": case_id,
            "evidence_id": evidence_id,
            "root_number": (
                cleaned_root_number
            ),
            "requested_depth": depth,
            "node_count": 0,
            "edge_count": 0,
            "nodes": [],
            "edges": [],
        }

    visited_depth: dict[str, int] = {
        cleaned_root_number: 0
    }

    discovered_nodes: set[str] = {
        cleaned_root_number
    }

    queue: deque[str] = deque(
        [cleaned_root_number]
    )

    edge_keys: set[
        tuple[str, str]
    ] = set()

    graph_edges: list[
        dict[str, Any]
    ] = []

    while queue:
        current_number = (
            queue.popleft()
        )

        current_depth = (
            visited_depth[
                current_number
            ]
        )

        if current_depth >= depth:
            continue

        connected_numbers = list(
            adjacency[
                current_number
            ].items()
        )

        connected_numbers.sort(
            key=lambda item: (
                item[1][
                    "total_records"
                ],
                item[1][
                    "total_duration_seconds"
                ],
            ),
            reverse=True,
        )

        connected_numbers = (
            connected_numbers[
                :per_number_limit
            ]
        )

        for (
            connected_number,
            communication,
        ) in connected_numbers:
            if (
                connected_number
                not in discovered_nodes
                and len(
                    discovered_nodes
                )
                >= maximum_nodes
            ):
                continue

            next_depth = (
                current_depth + 1
            )

            if (
                connected_number
                not in visited_depth
            ):
                visited_depth[
                    connected_number
                ] = next_depth

                discovered_nodes.add(
                    connected_number
                )

                queue.append(
                    connected_number
                )

            edge_key = tuple(
                sorted(
                    (
                        current_number,
                        connected_number,
                    )
                )
            )

            if edge_key in edge_keys:
                continue

            edge_keys.add(
                edge_key
            )

            graph_edges.append(
                {
                    "source": edge_key[0],
                    "target": edge_key[1],
                    "total_records": (
                        communication[
                            "total_records"
                        ]
                    ),
                    "total_calls": (
                        communication[
                            "total_calls"
                        ]
                    ),
                    "total_sms": (
                        communication[
                            "total_sms"
                        ]
                    ),
                    "total_duration_seconds": (
                        communication[
                            "total_duration_seconds"
                        ]
                    ),
                }
            )

    graph_nodes: list[
        dict[str, Any]
    ] = []

    for number in discovered_nodes:
        totals = (
            number_totals[number]
        )

        graph_nodes.append(
            {
                "phone_number": number,
                "is_root": (
                    number
                    == cleaned_root_number
                ),
                "depth": (
                    visited_depth.get(
                        number,
                        depth,
                    )
                ),
                "total_records": (
                    totals[
                        "total_records"
                    ]
                ),
                "total_duration_seconds": (
                    totals[
                        "total_duration_seconds"
                    ]
                ),
            }
        )

    graph_nodes.sort(
        key=lambda node: (
            node["depth"],
            -node[
                "total_records"
            ],
            node["phone_number"],
        )
    )

    graph_edges.sort(
        key=lambda edge: (
            -edge[
                "total_records"
            ],
            edge["source"],
            edge["target"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "root_number": (
            cleaned_root_number
        ),
        "requested_depth": depth,
        "node_count": len(
            graph_nodes
        ),
        "edge_count": len(
            graph_edges
        ),
        "nodes": graph_nodes,
        "edges": graph_edges,
    }


# =========================================================
# Public API-facing service functions
# =========================================================

def get_numbers(
    database: Session,
    case_id: int,
    evidence_id: int,
    search: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """
    API-facing wrapper for the number list.
    """

    return calculate_number_list(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        search_text=search,
        offset=offset,
        limit=limit,
    )


def get_number_analysis(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
) -> dict[str, Any] | None:
    """
    API-facing wrapper for one-number analysis.
    """

    return calculate_number_analysis(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=phone_number,
    )


def get_top_contacts(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
    limit: int = 10,
) -> dict[str, Any] | None:
    """
    API-facing wrapper for top contacts.
    """

    return calculate_top_contacts(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=phone_number,
        limit=limit,
    )


def get_contact_timeline(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
    contact_number: str,
) -> dict[str, Any] | None:
    """
    API-facing wrapper for a direct-contact timeline.
    """

    return calculate_contact_timeline(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=phone_number,
        contact_number=contact_number,
    )


def get_calls_by_hour(
    database: Session,
    case_id: int,
    evidence_id: int,
) -> dict[str, Any]:
    """
    API-facing wrapper for hourly activity.
    """

    return calculate_calls_by_hour(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )


def get_calls_by_date(
    database: Session,
    case_id: int,
    evidence_id: int,
) -> dict[str, Any]:
    """
    API-facing wrapper for daily activity.
    """

    return calculate_calls_by_date(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
    )