from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord
from app.schemas.forensic_analysis import (
    CommonContactsRequest,
    IncidentWindowRequest,
)


# =========================================================
# General helper functions
# =========================================================

def normalize_numeric_identifier(
    value: str,
) -> str:
    """
    Cleans phone numbers, IMEIs and IMSIs.

    Only digits and an optional plus sign are retained.
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
    Converts timezone-aware datetime values to UTC.

    The current database stores naive datetime values,
    so timezone information is removed after conversion.
    """

    if value.tzinfo is None:
        return value

    utc_value = value.astimezone(
        timezone.utc
    )

    return utc_value.replace(
        tzinfo=None
    )


# =========================================================
# Operator CDR ownership helper functions
# =========================================================

def get_record_subscriber_number(
    record: CDRRecord,
) -> str:
    """
    Returns the subscriber number that owns the technical
    identifiers in one CDR row.

    For the 23-field operator format, IMEI and IMSI belong to
    TARGET_NO. Older normalized CDR files may not contain a
    target_number, so caller_number is used only as a fallback.
    """

    target_number = normalize_numeric_identifier(
        record.target_number or ""
    )

    if target_number:
        return target_number

    return normalize_numeric_identifier(
        record.caller_number or ""
    )


def get_record_imei(
    record: CDRRecord,
) -> str:
    """Returns the normalized IMEI stored in either model field."""

    return normalize_numeric_identifier(
        record.imei or record.imei_esn or ""
    )


def get_record_imsi(
    record: CDRRecord,
) -> str:
    """Returns the normalized IMSI stored in either model field."""

    return normalize_numeric_identifier(
        record.imsi or record.imsi_min or ""
    )


def subscriber_number_filter(
    normalized_number: str,
):
    """
    SQL condition matching the owner of IMEI/IMSI values.

    TARGET_NO is authoritative when present. caller_number is
    accepted only for older rows where target_number is empty.
    """

    return or_(
        CDRRecord.target_number == normalized_number,
        and_(
            or_(
                CDRRecord.target_number.is_(None),
                CDRRecord.target_number == "",
            ),
            CDRRecord.caller_number == normalized_number,
        ),
    )


def imei_value_filter(
    normalized_imei: str,
):
    """SQL condition matching either normalized IMEI column."""

    return or_(
        CDRRecord.imei == normalized_imei,
        CDRRecord.imei_esn == normalized_imei,
    )


def imsi_value_filter(
    normalized_imsi: str,
):
    """SQL condition matching either normalized IMSI column."""

    return or_(
        CDRRecord.imsi == normalized_imsi,
        CDRRecord.imsi_min == normalized_imsi,
    )


def has_imei_filter():
    """SQL condition requiring an IMEI in either model column."""

    return or_(
        and_(
            CDRRecord.imei.is_not(None),
            CDRRecord.imei != "",
        ),
        and_(
            CDRRecord.imei_esn.is_not(None),
            CDRRecord.imei_esn != "",
        ),
    )


# =========================================================
# Common-contact analysis
# =========================================================

def calculate_common_contacts(
    database: Session,
    case_id: int,
    evidence_id: int,
    request: CommonContactsRequest,
) -> dict[str, Any]:
    """
    Finds third-party numbers connected to multiple targets
    inside one selected evidence file.
    """

    target_numbers: list[str] = []

    for number in request.target_numbers:
        normalized_number = normalize_numeric_identifier(
            number
        )

        if (
            normalized_number
            and normalized_number not in target_numbers
        ):
            target_numbers.append(
                normalized_number
            )

    if len(target_numbers) < 2:
        raise ValueError(
            "At least two unique valid target numbers are required."
        )

    target_number_set = set(
        target_numbers
    )

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
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
            CDRRecord.start_datetime.asc(),
            CDRRecord.id.asc(),
        )
    )

    records = list(
        database.scalars(
            records_query
        ).all()
    )

    contact_statistics: dict[
        str,
        dict[str, dict[str, Any]],
    ] = defaultdict(dict)

    for record in records:
        caller_number = record.caller_number
        receiver_number = record.receiver_number

        target_number: str | None = None
        contact_number: str | None = None
        communication_direction: str | None = None

        if (
            caller_number in target_number_set
            and receiver_number not in target_number_set
        ):
            target_number = caller_number
            contact_number = receiver_number
            communication_direction = "outgoing"

        elif (
            receiver_number in target_number_set
            and caller_number not in target_number_set
        ):
            target_number = receiver_number
            contact_number = caller_number
            communication_direction = "incoming"

        else:
            # Communication directly between selected
            # targets is not a third-party common contact.
            continue

        if not target_number or not contact_number:
            continue

        if (
            target_number
            not in contact_statistics[contact_number]
        ):
            contact_statistics[
                contact_number
            ][
                target_number
            ] = {
                "record_count": 0,
                "outgoing_records": 0,
                "incoming_records": 0,
                "total_duration_seconds": 0,
                "first_contact": None,
                "last_contact": None,
            }

        statistics = contact_statistics[
            contact_number
        ][
            target_number
        ]

        statistics["record_count"] += 1

        if communication_direction == "outgoing":
            statistics["outgoing_records"] += 1
        else:
            statistics["incoming_records"] += 1

        statistics["total_duration_seconds"] += (
            record.duration_seconds or 0
        )

        if statistics["first_contact"] is None:
            statistics["first_contact"] = (
                record.start_datetime
            )

        statistics["last_contact"] = (
            record.start_datetime
        )

    common_contacts: list[dict[str, Any]] = []

    for contact_number, target_map in contact_statistics.items():
        connected_targets = sorted(
            target_map.keys()
        )

        if (
            len(connected_targets)
            < request.minimum_common_targets
        ):
            continue

        target_statistics = []

        total_records = 0
        total_duration_seconds = 0

        first_contact: datetime | None = None
        last_contact: datetime | None = None

        for target_number in connected_targets:
            statistics = target_map[
                target_number
            ]

            total_records += (
                statistics["record_count"]
            )

            total_duration_seconds += (
                statistics["total_duration_seconds"]
            )

            target_first = statistics[
                "first_contact"
            ]

            target_last = statistics[
                "last_contact"
            ]

            if (
                first_contact is None
                or (
                    target_first is not None
                    and target_first < first_contact
                )
            ):
                first_contact = target_first

            if (
                last_contact is None
                or (
                    target_last is not None
                    and target_last > last_contact
                )
            ):
                last_contact = target_last

            target_statistics.append(
                {
                    "target_number": target_number,
                    "record_count": (
                        statistics["record_count"]
                    ),
                    "outgoing_records": (
                        statistics["outgoing_records"]
                    ),
                    "incoming_records": (
                        statistics["incoming_records"]
                    ),
                    "total_duration_seconds": (
                        statistics[
                            "total_duration_seconds"
                        ]
                    ),
                    "first_contact": (
                        statistics["first_contact"]
                    ),
                    "last_contact": (
                        statistics["last_contact"]
                    ),
                }
            )

        common_contacts.append(
            {
                "contact_number": contact_number,
                "connected_target_count": len(
                    connected_targets
                ),
                "connected_target_numbers": (
                    connected_targets
                ),
                "total_records": total_records,
                "total_duration_seconds": (
                    total_duration_seconds
                ),
                "first_contact": first_contact,
                "last_contact": last_contact,
                "target_statistics": (
                    target_statistics
                ),
            }
        )

    common_contacts.sort(
        key=lambda item: (
            -item["connected_target_count"],
            -item["total_records"],
            -item["total_duration_seconds"],
            item["contact_number"],
        )
    )

    return {
        "case_id": case_id,
        "requested_target_numbers": (
            target_numbers
        ),
        "common_contact_count": len(
            common_contacts
        ),
        "common_contacts": common_contacts[
            :request.limit
        ],
    }


# =========================================================
# IMEI analysis
# =========================================================

def calculate_imei_analysis(
    database: Session,
    case_id: int,
    evidence_id: int,
    imei: str,
) -> dict[str, Any] | None:
    """
    Analyses one IMEI inside one selected evidence file.

    In operator CDR rows, the IMEI belongs to TARGET_NO. For
    legacy normalized rows with no target_number, caller_number
    is used as a fallback.
    """

    normalized_imei = normalize_numeric_identifier(
        imei
    )

    if not normalized_imei:
        return None

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            imei_value_filter(normalized_imei),
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

    related_imsis: set[str] = set()
    related_cell_ids: set[str] = set()

    for record in records:
        associated_number = get_record_subscriber_number(
            record
        )

        if associated_number:
            if associated_number not in number_statistics:
                number_statistics[
                    associated_number
                ] = {
                    "record_count": 0,
                    "first_seen": record.start_datetime,
                    "last_seen": record.start_datetime,
                }

            statistics = number_statistics[
                associated_number
            ]

            statistics["record_count"] += 1
            statistics["last_seen"] = (
                record.start_datetime
            )

        related_imsi = get_record_imsi(
            record
        )

        if related_imsi:
            related_imsis.add(
                related_imsi
            )

        for cell_value in (
            record.cell_id,
            record.first_cell_global_id,
            record.last_cell_global_id,
        ):
            if cell_value:
                related_cell_ids.add(
                    cell_value
                )

    associated_numbers = []

    for phone_number, statistics in number_statistics.items():
        associated_numbers.append(
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

    associated_numbers.sort(
        key=lambda item: (
            -item["record_count"],
            item["phone_number"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "imei": normalized_imei,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "association_basis": (
            "For operator CDR rows, the imported IMEI is "
            "associated with TARGET_NO. caller_number is used "
            "only as a fallback for older rows where "
            "target_number is empty."
        ),
        "total_records": len(records),
        "associated_number_count": len(
            associated_numbers
        ),
        "associated_numbers": (
            associated_numbers
        ),
        "related_imsis": sorted(
            related_imsis
        ),
        "related_cell_ids": sorted(
            related_cell_ids
        ),
        "first_seen": (
            records[0].start_datetime
        ),
        "last_seen": (
            records[-1].start_datetime
        ),
    }


# =========================================================
# IMSI analysis
# =========================================================

def calculate_imsi_analysis(
    database: Session,
    case_id: int,
    evidence_id: int,
    imsi: str,
) -> dict[str, Any] | None:
    """
    Analyses one IMSI inside one selected evidence file.

    In operator CDR rows, the IMSI belongs to TARGET_NO. For
    legacy normalized rows with no target_number, caller_number
    is used as a fallback.
    """

    normalized_imsi = normalize_numeric_identifier(
        imsi
    )

    if not normalized_imsi:
        return None

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            imsi_value_filter(normalized_imsi),
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

    related_imeis: set[str] = set()
    related_cell_ids: set[str] = set()

    for record in records:
        associated_number = get_record_subscriber_number(
            record
        )

        if associated_number:
            if associated_number not in number_statistics:
                number_statistics[
                    associated_number
                ] = {
                    "record_count": 0,
                    "first_seen": record.start_datetime,
                    "last_seen": record.start_datetime,
                }

            statistics = number_statistics[
                associated_number
            ]

            statistics["record_count"] += 1
            statistics["last_seen"] = (
                record.start_datetime
            )

        related_imei = get_record_imei(
            record
        )

        if related_imei:
            related_imeis.add(
                related_imei
            )

        for cell_value in (
            record.cell_id,
            record.first_cell_global_id,
            record.last_cell_global_id,
        ):
            if cell_value:
                related_cell_ids.add(
                    cell_value
                )

    associated_numbers = []

    for phone_number, statistics in number_statistics.items():
        associated_numbers.append(
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

    associated_numbers.sort(
        key=lambda item: (
            -item["record_count"],
            item["phone_number"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "imsi": normalized_imsi,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "association_basis": (
            "For operator CDR rows, the imported IMSI is "
            "associated with TARGET_NO. caller_number is used "
            "only as a fallback for older rows where "
            "target_number is empty."
        ),
        "total_records": len(records),
        "associated_number_count": len(
            associated_numbers
        ),
        "associated_numbers": (
            associated_numbers
        ),
        "related_imeis": sorted(
            related_imeis
        ),
        "related_cell_ids": sorted(
            related_cell_ids
        ),
        "first_seen": (
            records[0].start_datetime
        ),
        "last_seen": (
            records[-1].start_datetime
        ),
    }


# =========================================================
# Device-change history
# =========================================================

def calculate_device_history(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str,
) -> dict[str, Any] | None:
    """
    Finds IMEIs owned by one target subscriber inside one
    selected evidence file.

    Operator CDR device identifiers belong to TARGET_NO. The
    caller_number fallback is used only for legacy rows where
    target_number is missing.
    """

    normalized_number = normalize_numeric_identifier(
        phone_number
    )

    if not normalized_number:
        return None

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            subscriber_number_filter(
                normalized_number
            ),
            has_imei_filter(),
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

    device_statistics: dict[
        str,
        dict[str, Any],
    ] = {}

    change_events = []

    previous_imei: str | None = None

    for record in records:
        current_imei = get_record_imei(
            record
        )

        if not current_imei:
            continue

        if current_imei not in device_statistics:
            device_statistics[
                current_imei
            ] = {
                "record_count": 0,
                "first_seen": record.start_datetime,
                "last_seen": record.start_datetime,
            }

        statistics = device_statistics[
            current_imei
        ]

        statistics["record_count"] += 1
        statistics["last_seen"] = (
            record.start_datetime
        )

        if (
            previous_imei is not None
            and previous_imei != current_imei
        ):
            change_events.append(
                {
                    "change_datetime": (
                        record.start_datetime
                    ),
                    "previous_imei": (
                        previous_imei
                    ),
                    "new_imei": (
                        current_imei
                    ),
                    "evidence_id": (
                        record.evidence_id
                    ),
                    "source_row": (
                        record.source_row
                    ),
                }
            )

        previous_imei = current_imei

    devices = []

    for imei_value, statistics in device_statistics.items():
        devices.append(
            {
                "imei": imei_value,
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

    devices.sort(
        key=lambda item: (
            item["first_seen"],
            item["imei"],
        )
    )

    if not devices:
        return None

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "phone_number": normalized_number,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "association_basis": (
            "For operator CDR rows, the imported IMEI is "
            "associated with TARGET_NO. caller_number is used "
            "only as a fallback for older rows where "
            "target_number is empty."
        ),
        "unique_device_count": len(
            devices
        ),
        "total_device_records": sum(
            item["record_count"]
            for item in devices
        ),
        "devices": devices,
        "change_events": change_events,
    }


# =========================================================
# Common-device detection
# =========================================================

def calculate_common_devices(
    database: Session,
    case_id: int,
    evidence_id: int,
    minimum_numbers: int,
    limit: int,
) -> dict[str, Any]:
    """
    Finds an IMEI used by multiple target subscribers inside
    one selected evidence file.

    A number using many different IMEIs is device switching,
    not a common device. A common device exists only when the
    same IMEI is linked to at least minimum_numbers different
    subscriber numbers.
    """

    records_query = (
        select(CDRRecord)
        .where(
            CDRRecord.case_id == case_id,
            CDRRecord.evidence_id == evidence_id,
            has_imei_filter(),
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

    device_statistics: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:
        imei_value = get_record_imei(
            record
        )
        phone_number = get_record_subscriber_number(
            record
        )

        if not imei_value or not phone_number:
            continue

        if imei_value not in device_statistics:
            device_statistics[
                imei_value
            ] = {
                "associated_numbers": set(),
                "total_records": 0,
                "first_seen": record.start_datetime,
                "last_seen": record.start_datetime,
                "related_imsis": set(),
            }

        statistics = device_statistics[
            imei_value
        ]

        statistics[
            "associated_numbers"
        ].add(
            phone_number
        )

        statistics["total_records"] += 1
        statistics["last_seen"] = (
            record.start_datetime
        )

        related_imsi = get_record_imsi(
            record
        )

        if related_imsi:
            statistics[
                "related_imsis"
            ].add(
                related_imsi
            )

    common_devices = []

    for imei_value, statistics in device_statistics.items():
        associated_numbers = sorted(
            statistics["associated_numbers"]
        )

        if len(associated_numbers) < minimum_numbers:
            continue

        common_devices.append(
            {
                "imei": imei_value,
                "associated_number_count": len(
                    associated_numbers
                ),
                "associated_numbers": (
                    associated_numbers
                ),
                "total_records": (
                    statistics["total_records"]
                ),
                "first_seen": (
                    statistics["first_seen"]
                ),
                "last_seen": (
                    statistics["last_seen"]
                ),
                "related_imsis": sorted(
                    statistics["related_imsis"]
                ),
            }
        )

    common_devices.sort(
        key=lambda item: (
            -item["associated_number_count"],
            -item["total_records"],
            item["imei"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {evidence_id}."
        ),
        "association_basis": (
            "For operator CDR rows, IMEI ownership is based "
            "on TARGET_NO. A common device is reported only "
            f"when the same IMEI is linked to at least "
            f"{minimum_numbers} different subscriber numbers. "
            "caller_number is used only as a fallback for "
            "older rows where target_number is empty."
        ),
        "common_device_count": len(
            common_devices
        ),
        "devices": common_devices[
            :limit
        ],
    }


# =========================================================
# Incident-window analysis
# =========================================================

def calculate_incident_window(
    database: Session,
    case_id: int,
    request: IncidentWindowRequest,
) -> dict[str, Any]:
    """
    Returns activity around an incident timestamp
    inside one selected evidence file.
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
        CDRRecord.evidence_id == request.evidence_id,
        CDRRecord.start_datetime >= window_start,
        CDRRecord.start_datetime <= window_end,
    ]

    if request.phone_numbers:
        normalized_numbers = []

        for number in request.phone_numbers:
            cleaned_number = (
                normalize_numeric_identifier(
                    number
                )
            )

            if (
                cleaned_number
                and cleaned_number not in normalized_numbers
            ):
                normalized_numbers.append(
                    cleaned_number
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

    all_records = list(
        database.scalars(
            records_query
        ).all()
    )

    total_matching_records = len(
        all_records
    )

    returned_records = all_records[
        :request.limit
    ]

    events = []

    number_statistics: dict[
        str,
        dict[str, Any],
    ] = {}

    def update_number_statistics(
        phone_number: str,
        event_time: datetime,
        phase: str,
    ) -> None:
        if phone_number not in number_statistics:
            number_statistics[
                phone_number
            ] = {
                "record_count": 0,
                "before_count": 0,
                "at_incident_count": 0,
                "after_count": 0,
                "first_activity": event_time,
                "last_activity": event_time,
            }

        statistics = number_statistics[
            phone_number
        ]

        statistics["record_count"] += 1
        statistics["last_activity"] = (
            event_time
        )

        if phase == "before_incident":
            statistics["before_count"] += 1

        elif phase == "at_incident":
            statistics[
                "at_incident_count"
            ] += 1

        else:
            statistics["after_count"] += 1

    for record in returned_records:
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

        update_number_statistics(
            record.caller_number,
            record.start_datetime,
            phase,
        )

        if record.receiver_number != record.caller_number:
            update_number_statistics(
                record.receiver_number,
                record.start_datetime,
                phase,
            )

        events.append(
            {
                "record_id": record.id,
                "evidence_id": (
                    record.evidence_id
                ),
                "source_row": (
                    record.source_row
                ),
                "caller_number": (
                    record.caller_number
                ),
                "receiver_number": (
                    record.receiver_number
                ),
                "event_type": (
                    record.event_type
                ),
                "direction": (
                    record.direction
                ),
                "start_datetime": (
                    record.start_datetime
                ),
                "duration_seconds": (
                    record.duration_seconds or 0
                ),
                "imei": record.imei,
                "imsi": record.imsi,
                "cell_id": record.cell_id,
                "tower_address": (
                    record.tower_address
                ),
                "relative_seconds": (
                    relative_seconds
                ),
                "phase": phase,
            }
        )

    number_statistic_items = []

    for phone_number, statistics in number_statistics.items():
        number_statistic_items.append(
            {
                "phone_number": phone_number,
                "record_count": (
                    statistics["record_count"]
                ),
                "before_count": (
                    statistics["before_count"]
                ),
                "at_incident_count": (
                    statistics[
                        "at_incident_count"
                    ]
                ),
                "after_count": (
                    statistics["after_count"]
                ),
                "first_activity": (
                    statistics["first_activity"]
                ),
                "last_activity": (
                    statistics["last_activity"]
                ),
            }
        )

    number_statistic_items.sort(
        key=lambda item: (
            -item["record_count"],
            item["phone_number"],
        )
    )

    return {
        "case_id": case_id,
        "evidence_id": request.evidence_id,
        "evidence_scope": (
            "Results are limited to selected "
            f"evidence file ID {request.evidence_id}."
        ),
        "incident_datetime": (
            incident_datetime
        ),
        "window_start": (
            window_start
        ),
        "window_end": (
            window_end
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
        "number_statistics": (
            number_statistic_items
        ),
        "events": events,
    }