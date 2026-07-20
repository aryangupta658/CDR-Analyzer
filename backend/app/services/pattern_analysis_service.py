from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import date, datetime, timedelta
from hashlib import sha256
from math import asin, cos, radians, sin, sqrt
from typing import Any, Callable, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord


DISCLAIMER = (
    "The displayed items are behavioural and technical patterns found in CDR "
    "metadata. They show why a number may deserve investigator review, but they "
    "do not independently prove fraud, criminal conduct, or involvement in an "
    "incident."
)


# =========================================================
# Normalisation helpers
# =========================================================


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_phone(value: Any) -> str:
    return "".join(character for character in clean_text(value) if character in "+0123456789")


def valid_coordinate(latitude: Any, longitude: Any) -> tuple[float, float] | None:
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return None

    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon

    return None


def normalize_event_type(record: CDRRecord) -> str:
    value = clean_text(
        record.event_type or record.service_type or record.connection_type
    ).lower()

    if "sms" in value:
        return "sms"

    if "call" in value or "voice" in value:
        return "call"

    call_type = clean_text(record.call_type).lower()
    if "sms" in call_type:
        return "sms"

    if call_type in {"mo", "mt", "incoming", "outgoing", "in", "out"}:
        return "call"

    return "other"


def normalize_direction(record: CDRRecord, phone_number: str) -> str:
    caller = normalize_phone(record.caller_number)
    receiver = normalize_phone(record.receiver_number)

    if caller and caller == phone_number:
        return "outgoing"

    if receiver and receiver == phone_number:
        return "incoming"

    value = clean_text(record.direction or record.call_type).lower()

    if value in {"out", "outgoing", "mo", "sms-mo", "originating"}:
        return "outgoing"

    if value in {"in", "incoming", "mt", "sms-mt", "terminating"}:
        return "incoming"

    if value.startswith("out"):
        return "outgoing"

    if value.startswith("in"):
        return "incoming"

    return "unknown"


def detect_roaming(record: CDRRecord) -> bool:
    if isinstance(record.roaming, bool):
        return record.roaming

    value = clean_text(record.roaming_network_circle).lower()
    return value not in {"", "home", "false", "0", "no", "none", "nan"}


def roaming_network(record: CDRRecord) -> str:
    value = clean_text(record.roaming_network_circle)
    if value.lower() in {"", "home", "false", "0", "no", "none", "nan"}:
        return ""
    return value


def record_imei(record: CDRRecord) -> str:
    return clean_text(record.imei or record.imei_esn)


def record_imsi(record: CDRRecord) -> str:
    return clean_text(record.imsi or record.imsi_min)


def record_cell(record: CDRRecord) -> str:
    return clean_text(record.cell_id or record.first_cell_global_id)


def record_last_cell(record: CDRRecord) -> str:
    return clean_text(record.last_cell_global_id or record.cell_id)


def record_start_coordinate(record: CDRRecord) -> tuple[float, float] | None:
    coordinate = valid_coordinate(record.first_latitude, record.first_longitude)
    if coordinate is not None:
        return coordinate
    return valid_coordinate(record.latitude, record.longitude)


def record_end_coordinate(record: CDRRecord) -> tuple[float, float] | None:
    coordinate = valid_coordinate(record.last_latitude, record.last_longitude)
    if coordinate is not None:
        return coordinate
    return record_start_coordinate(record)


def related_number(record: CDRRecord, phone_number: str) -> str:
    caller = normalize_phone(record.caller_number)
    receiver = normalize_phone(record.receiver_number)
    target = normalize_phone(record.target_number)
    b_party = normalize_phone(record.b_party_number)

    if caller == phone_number:
        return receiver

    if receiver == phone_number:
        return caller

    if target == phone_number:
        return b_party

    if b_party == phone_number:
        return target

    return ""


def record_matches_number(record: CDRRecord, phone_number: str) -> bool:
    return phone_number in {
        normalize_phone(record.caller_number),
        normalize_phone(record.receiver_number),
        normalize_phone(record.target_number),
        normalize_phone(record.b_party_number),
    }


def record_to_event(record: CDRRecord, phone_number: str) -> dict[str, Any] | None:
    if record.start_datetime is None:
        return None

    target_number = normalize_phone(record.target_number)

    # IMEI, IMSI, tower, roaming and forwarding fields belong to the target
    # subscriber in an operator CDR. They must not be assigned to the B-party
    # merely because that B-party appears in caller_number or receiver_number.
    technical_metadata_belongs_to_number = (
        not target_number or target_number == phone_number
    )

    return {
        "record_id": record.id,
        "timestamp": record.start_datetime,
        "event_type": normalize_event_type(record),
        "direction": normalize_direction(record, phone_number),
        "duration": max(0, int(record.duration_seconds or 0)),
        "contact": related_number(record, phone_number),
        "imei": (
            record_imei(record)
            if technical_metadata_belongs_to_number
            else ""
        ),
        "imsi": (
            record_imsi(record)
            if technical_metadata_belongs_to_number
            else ""
        ),
        "cell_id": (
            record_cell(record)
            if technical_metadata_belongs_to_number
            else ""
        ),
        "last_cell_id": (
            record_last_cell(record)
            if technical_metadata_belongs_to_number
            else ""
        ),
        "start_coordinate": (
            record_start_coordinate(record)
            if technical_metadata_belongs_to_number
            else None
        ),
        "end_coordinate": (
            record_end_coordinate(record)
            if technical_metadata_belongs_to_number
            else None
        ),
        "roaming": (
            detect_roaming(record)
            if technical_metadata_belongs_to_number
            else False
        ),
        "roaming_network": (
            roaming_network(record)
            if technical_metadata_belongs_to_number
            else ""
        ),
        "forwarding": (
            normalize_phone(record.call_forwarding_number)
            if technical_metadata_belongs_to_number
            else ""
        ),
        "target_number": target_number,
    }


# =========================================================
# Pattern response helpers
# =========================================================


def pattern_id(
    rule_code: str,
    phone_number: str,
    window_start: datetime | None,
    observed_value: Any,
) -> str:
    raw_value = f"{rule_code}|{phone_number}|{window_start}|{observed_value}"
    return sha256(raw_value.encode("utf-8")).hexdigest()[:20]


def suspicious_description(reason: str) -> str:
    cleaned = reason.strip().rstrip(".")
    if not cleaned:
        return "This number shows a communication pattern that deserves review."
    return f"This number looks suspicious because {cleaned[:1].lower() + cleaned[1:]}."


def make_pattern(
    *,
    rule_code: str,
    title: str,
    category: str,
    scope: str,
    phone_number: str,
    observed_value: Any,
    comparison_value: Any = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    reason: str,
    explanation: str,
    events: Iterable[dict[str, Any]] = (),
    related_numbers: Iterable[str] = (),
    imeis: Iterable[str] = (),
    imsis: Iterable[str] = (),
    cell_ids: Iterable[str] = (),
) -> dict[str, Any]:
    event_list = list(events)

    return {
        "pattern_id": pattern_id(
            rule_code,
            phone_number,
            window_start,
            observed_value,
        ),
        "rule_code": rule_code,
        "title": title,
        "category": category,
        "scope": scope,
        "phone_number": phone_number,
        "observed_value": observed_value,
        "comparison_value": comparison_value,
        "window_start": window_start,
        "window_end": window_end,
        "description": suspicious_description(reason),
        "explanation": explanation,
        "related_numbers": sorted(
            {normalize_phone(value) for value in related_numbers if normalize_phone(value)}
        )[:100],
        "imeis": sorted({clean_text(value) for value in imeis if clean_text(value)}),
        "imsis": sorted({clean_text(value) for value in imsis if clean_text(value)}),
        "cell_ids": sorted({clean_text(value) for value in cell_ids if clean_text(value)}),
        "source_record_ids": sorted(
            {
                int(event["record_id"])
                for event in event_list
                if event.get("record_id") is not None
            }
        )[:500],
    }


def strongest_window(
    events: list[dict[str, Any]],
    minutes: int,
    predicate: Callable[[dict[str, Any]], bool],
) -> list[dict[str, Any]]:
    filtered = [event for event in events if predicate(event)]
    queue: deque[dict[str, Any]] = deque()
    strongest: list[dict[str, Any]] = []
    maximum_delta = timedelta(minutes=minutes)

    for event in filtered:
        queue.append(event)

        while queue and event["timestamp"] - queue[0]["timestamp"] > maximum_delta:
            queue.popleft()

        if len(queue) > len(strongest):
            strongest = list(queue)

    return strongest


def ratio_percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator * 100 / denominator, 1)


def unique_days(events: list[dict[str, Any]]) -> int:
    return max(1, len({event["timestamp"].date() for event in events}))


def group_events_by_day(
    events: list[dict[str, Any]],
) -> dict[date, list[dict[str, Any]]]:
    grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[event["timestamp"].date()].append(event)
    return grouped


def unique_contacts_per_day(events: list[dict[str, Any]]) -> float:
    grouped = group_events_by_day(events)
    if not grouped:
        return 0.0

    counts = [
        len({event["contact"] for event in day_events if event["contact"]})
        for day_events in grouped.values()
    ]
    return sum(counts) / len(counts)


# =========================================================
# Location helpers
# =========================================================


def haversine_km(
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    first_latitude, first_longitude = first
    second_latitude, second_longitude = second

    latitude_delta = radians(second_latitude - first_latitude)
    longitude_delta = radians(second_longitude - first_longitude)

    first_latitude_radians = radians(first_latitude)
    second_latitude_radians = radians(second_latitude)

    value = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude_radians)
        * cos(second_latitude_radians)
        * sin(longitude_delta / 2) ** 2
    )

    return 6371.0 * 2 * asin(sqrt(value))


def rapid_movement_details(
    events: list[dict[str, Any]],
    minimum_distance_km: float = 50.0,
    minimum_speed_kmh: float = 300.0,
) -> list[dict[str, Any]]:
    movements: list[dict[str, Any]] = []

    for event in events:
        start_coordinate = event.get("start_coordinate")
        end_coordinate = event.get("end_coordinate")
        duration_seconds = int(event.get("duration") or 0)

        if start_coordinate and end_coordinate and duration_seconds > 0:
            distance = haversine_km(start_coordinate, end_coordinate)
            speed = distance / (duration_seconds / 3600)

            if distance >= minimum_distance_km and speed >= minimum_speed_kmh:
                movements.append(
                    {
                        "speed": speed,
                        "distance": distance,
                        "events": [event],
                        "start": event["timestamp"],
                        "end": event["timestamp"] + timedelta(seconds=duration_seconds),
                    }
                )

    previous_event: dict[str, Any] | None = None

    for event in events:
        if previous_event is None:
            previous_event = event
            continue

        first_coordinate = previous_event.get("end_coordinate")
        second_coordinate = event.get("start_coordinate")
        seconds = (event["timestamp"] - previous_event["timestamp"]).total_seconds()

        if first_coordinate and second_coordinate and seconds > 0:
            distance = haversine_km(first_coordinate, second_coordinate)
            speed = distance / (seconds / 3600)

            if distance >= minimum_distance_km and speed >= minimum_speed_kmh:
                movements.append(
                    {
                        "speed": speed,
                        "distance": distance,
                        "events": [previous_event, event],
                        "start": previous_event["timestamp"],
                        "end": event["timestamp"],
                    }
                )

        previous_event = event

    return movements


# =========================================================
# Short-window rules
# =========================================================


def short_window_patterns(
    phone_number: str,
    events: list[dict[str, Any]],
    options: dict[str, bool],
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []

    if options["calls"]:
        call_burst = strongest_window(
            events,
            5,
            lambda event: event["event_type"] == "call",
        )

        if len(call_burst) >= 10:
            patterns.append(
                make_pattern(
                    rule_code="CALL_BURST_5M",
                    title="Rapid call burst",
                    category="call",
                    scope="short_window",
                    phone_number=phone_number,
                    observed_value=f"{len(call_burst)} calls in 5 minutes",
                    comparison_value="10 or more calls",
                    window_start=call_burst[0]["timestamp"],
                    window_end=call_burst[-1]["timestamp"],
                    reason="many calls occurred inside a five-minute period",
                    explanation=(
                        "Rapid calling can represent coordination, automated calling, repeated "
                        "retrying, or legitimate emergency activity."
                    ),
                    events=call_burst,
                    related_numbers=(event["contact"] for event in call_burst),
                )
            )

        call_hour = strongest_window(
            events,
            60,
            lambda event: event["event_type"] == "call",
        )
        call_hour_contacts = {
            event["contact"] for event in call_hour if event["contact"]
        }

        if len(call_hour_contacts) >= 20:
            patterns.append(
                make_pattern(
                    rule_code="UNIQUE_CALL_CONTACTS_1H",
                    title="Many call contacts in one hour",
                    category="contact",
                    scope="short_window",
                    phone_number=phone_number,
                    observed_value=f"{len(call_hour_contacts)} unique contacts",
                    comparison_value="20 or more contacts",
                    window_start=call_hour[0]["timestamp"],
                    window_end=call_hour[-1]["timestamp"],
                    reason="it communicated with many different contacts in one hour",
                    explanation=(
                        "A high-diversity hour may represent bulk outreach, coordination, "
                        "business calling, or another unusual activity period."
                    ),
                    events=call_hour,
                    related_numbers=call_hour_contacts,
                )
            )

        if len(call_hour) >= 10:
            short_calls = [event for event in call_hour if event["duration"] <= 10]
            short_ratio = ratio_percent(len(short_calls), len(call_hour))

            if short_ratio >= 60:
                patterns.append(
                    make_pattern(
                        rule_code="SHORT_CALL_RATIO_1H",
                        title="Short-call concentration in one hour",
                        category="call",
                        scope="short_window",
                        phone_number=phone_number,
                        observed_value=f"{short_ratio}% short calls",
                        comparison_value="60% or more",
                        window_start=call_hour[0]["timestamp"],
                        window_end=call_hour[-1]["timestamp"],
                        reason="most calls in its busiest hour lasted ten seconds or less",
                        explanation=(
                            "Repeated short calls may reflect call testing, failed attempts, "
                            "automated dialling, or a legitimate rapid-contact situation."
                        ),
                        events=short_calls,
                    )
                )

            zero_calls = [event for event in call_hour if event["duration"] == 0]
            zero_ratio = ratio_percent(len(zero_calls), len(call_hour))

            if zero_ratio >= 30:
                patterns.append(
                    make_pattern(
                        rule_code="ZERO_CALL_RATIO_1H",
                        title="Zero-duration call concentration in one hour",
                        category="call",
                        scope="short_window",
                        phone_number=phone_number,
                        observed_value=f"{zero_ratio}% zero-duration calls",
                        comparison_value="30% or more",
                        window_start=call_hour[0]["timestamp"],
                        window_end=call_hour[-1]["timestamp"],
                        reason="many voice calls in one hour had zero duration",
                        explanation=(
                            "The rule excludes SMS records. The pattern can result from failed "
                            "calls, repeated attempts, network behaviour, or automated activity."
                        ),
                        events=zero_calls,
                    )
                )

    if options["sms"]:
        sms_burst = strongest_window(
            events,
            5,
            lambda event: (
                event["event_type"] == "sms"
                and event["direction"] == "outgoing"
            ),
        )

        if len(sms_burst) >= 15:
            patterns.append(
                make_pattern(
                    rule_code="SMS_BURST_5M",
                    title="Rapid outgoing SMS burst",
                    category="sms",
                    scope="short_window",
                    phone_number=phone_number,
                    observed_value=f"{len(sms_burst)} outgoing SMS in 5 minutes",
                    comparison_value="15 or more SMS",
                    window_start=sms_burst[0]["timestamp"],
                    window_end=sms_burst[-1]["timestamp"],
                    reason="many outgoing messages were sent inside five minutes",
                    explanation=(
                        "A rapid outgoing message burst can indicate automated messaging, "
                        "coordination, alerts, or legitimate bulk communication."
                    ),
                    events=sms_burst,
                    related_numbers=(event["contact"] for event in sms_burst),
                )
            )

    if options["devices"]:
        device_day = strongest_window(
            events,
            24 * 60,
            lambda event: bool(event["imei"] or event["imsi"]),
        )

        imeis = {event["imei"] for event in device_day if event["imei"]}
        imsis = {event["imsi"] for event in device_day if event["imsi"]}

        if len(imeis) >= 3:
            patterns.append(
                make_pattern(
                    rule_code="IMEI_CHANGE_24H",
                    title="Several devices used within 24 hours",
                    category="device",
                    scope="short_window",
                    phone_number=phone_number,
                    observed_value=f"{len(imeis)} unique IMEIs",
                    comparison_value="3 or more IMEIs",
                    window_start=device_day[0]["timestamp"],
                    window_end=device_day[-1]["timestamp"],
                    reason="several handset identities appeared within 24 hours",
                    explanation=(
                        "A legitimate handset replacement is possible, but repeated device "
                        "switching in one day deserves review."
                    ),
                    events=device_day,
                    imeis=imeis,
                )
            )

        if len(imsis) >= 3:
            patterns.append(
                make_pattern(
                    rule_code="IMSI_CHANGE_24H",
                    title="Several SIM identities used within 24 hours",
                    category="device",
                    scope="short_window",
                    phone_number=phone_number,
                    observed_value=f"{len(imsis)} unique IMSIs",
                    comparison_value="3 or more IMSIs",
                    window_start=device_day[0]["timestamp"],
                    window_end=device_day[-1]["timestamp"],
                    reason="several subscriber identities appeared within 24 hours",
                    explanation=(
                        "Dual-SIM use can be normal, but frequent SIM switching in one day "
                        "is a useful technical pattern for investigation."
                    ),
                    events=device_day,
                    imsis=imsis,
                )
            )

    return patterns


# =========================================================
# Full-evidence rules
# =========================================================


def full_evidence_patterns(
    phone_number: str,
    events: list[dict[str, Any]],
    evidence_days: int,
    options: dict[str, bool],
    device_to_target_numbers: dict[str, set[str]],
) -> list[dict[str, Any]]:
    if not events:
        return []

    patterns: list[dict[str, Any]] = []
    evidence_start = events[0]["timestamp"]
    evidence_end = events[-1]["timestamp"]
    days = max(1, evidence_days)

    calls = [event for event in events if event["event_type"] == "call"]
    outgoing_sms = [
        event
        for event in events
        if event["event_type"] == "sms"
        and event["direction"] == "outgoing"
    ]
    outgoing_events = [
        event for event in events if event["direction"] == "outgoing"
    ]
    incoming_events = [
        event for event in events if event["direction"] == "incoming"
    ]

    contact_counts = Counter(
        event["contact"] for event in events if event["contact"]
    )
    unique_contacts = set(contact_counts)

    if options["calls"] and calls:
        calls_per_day = round(len(calls) / days, 1)

        if calls_per_day >= 75:
            patterns.append(
                make_pattern(
                    rule_code="CALLS_PER_DAY",
                    title="High average call activity",
                    category="call",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{calls_per_day} calls per day",
                    comparison_value="75 or more calls per day",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="its average call count is high across the complete evidence period",
                    explanation=(
                        "The rule uses the evidence duration, so it works for three-day, "
                        "seven-day, eight-day, and longer CDR files."
                    ),
                    events=calls,
                )
            )

        short_calls = [event for event in calls if event["duration"] <= 10]
        short_ratio = ratio_percent(len(short_calls), len(calls))

        if len(calls) >= 20 and short_ratio >= 60:
            patterns.append(
                make_pattern(
                    rule_code="SHORT_CALL_RATIO",
                    title="High short-call ratio",
                    category="call",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{short_ratio}% short calls",
                    comparison_value="60% or more",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="more than sixty percent of its voice calls lasted ten seconds or less",
                    explanation=(
                        "A ratio-based rule detects repeated short-call behaviour even when "
                        "the calls are distributed over several days."
                    ),
                    events=short_calls,
                )
            )

        zero_calls = [event for event in calls if event["duration"] == 0]
        zero_ratio = ratio_percent(len(zero_calls), len(calls))

        if len(calls) >= 20 and zero_ratio >= 30:
            patterns.append(
                make_pattern(
                    rule_code="ZERO_DURATION_RATIO",
                    title="High zero-duration voice-call ratio",
                    category="call",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{zero_ratio}% zero-duration calls",
                    comparison_value="30% or more",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="a large percentage of its voice calls had zero duration",
                    explanation=(
                        "SMS records are excluded. Zero-duration calls may represent failed "
                        "attempts, repeated retrying, network behaviour, or automation."
                    ),
                    events=zero_calls,
                )
            )

    if options["sms"] and outgoing_sms:
        sms_per_day = round(len(outgoing_sms) / days, 1)

        if sms_per_day >= 30:
            patterns.append(
                make_pattern(
                    rule_code="SMS_PER_DAY",
                    title="High average outgoing SMS activity",
                    category="sms",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{sms_per_day} outgoing SMS per day",
                    comparison_value="30 or more outgoing SMS per day",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="its average outgoing message count is high across the complete evidence period",
                    explanation=(
                        "Outgoing SMS is evaluated separately because incoming OTP and "
                        "promotional messages may not be controlled by the subscriber."
                    ),
                    events=outgoing_sms,
                    related_numbers=(event["contact"] for event in outgoing_sms),
                )
            )

    if len(unique_contacts) > 100:
        patterns.append(
            make_pattern(
                rule_code="UNIQUE_CONTACTS_FULL",
                title="Very large contact set",
                category="contact",
                scope="full_evidence",
                phone_number=phone_number,
                observed_value=f"{len(unique_contacts)} unique contacts",
                comparison_value="More than 100 contacts",
                window_start=evidence_start,
                window_end=evidence_end,
                reason="it communicated with more than one hundred different contacts",
                explanation=(
                    "A very broad contact set can indicate mass outreach, campaign activity, "
                    "coordination, or legitimate professional use."
                ),
                events=events,
                related_numbers=unique_contacts,
            )
        )

    if len(unique_contacts) >= 20:
        one_time_contacts = {
            contact for contact, count in contact_counts.items() if count == 1
        }
        one_time_ratio = ratio_percent(
            len(one_time_contacts),
            len(unique_contacts),
        )

        if one_time_ratio >= 70:
            patterns.append(
                make_pattern(
                    rule_code="ONE_TIME_CONTACT_RATIO",
                    title="Mostly one-time contacts",
                    category="contact",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{one_time_ratio}% one-time contacts",
                    comparison_value="70% or more",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="most of its contacts appeared only once in the evidence",
                    explanation=(
                        "A high one-time-contact percentage may represent bulk outreach or a "
                        "rapidly changing contact pool."
                    ),
                    events=events,
                    related_numbers=one_time_contacts,
                )
            )

    if len(events) >= 30:
        outgoing_ratio = ratio_percent(len(outgoing_events), len(events))
        incoming_ratio = ratio_percent(len(incoming_events), len(events))

        if outgoing_ratio >= 90:
            patterns.append(
                make_pattern(
                    rule_code="HIGH_OUTGOING_RATIO",
                    title="Very high outgoing communication ratio",
                    category="call",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{outgoing_ratio}% outgoing",
                    comparison_value="90% or more",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="more than ninety percent of its communication was outgoing",
                    explanation=(
                        "A strongly outgoing profile can be relevant to mass outreach, "
                        "coordination, telemarketing, or normal business activity."
                    ),
                    events=outgoing_events,
                )
            )

        if incoming_ratio >= 90:
            patterns.append(
                make_pattern(
                    rule_code="HIGH_INCOMING_RATIO",
                    title="Very high incoming communication ratio",
                    category="call",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{incoming_ratio}% incoming",
                    comparison_value="90% or more",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="more than ninety percent of its communication was incoming",
                    explanation=(
                        "A strongly incoming profile may indicate a collection number, "
                        "helpline, campaign receiver, or another unusual communication role."
                    ),
                    events=incoming_events,
                )
            )

    night_events = [
        event for event in events if 0 <= event["timestamp"].hour < 5
    ]
    night_ratio = ratio_percent(len(night_events), len(events))

    if len(events) >= 20 and night_ratio >= 40:
        patterns.append(
            make_pattern(
                rule_code="NIGHT_ACTIVITY_RATIO",
                title="High night-time activity",
                category="call",
                scope="full_evidence",
                phone_number=phone_number,
                observed_value=f"{night_ratio}% activity between 12 AM and 5 AM",
                comparison_value="40% or more",
                window_start=evidence_start,
                window_end=evidence_end,
                reason="more than forty percent of its communication occurred between midnight and 5 AM",
                explanation=(
                    "Night work and international communication may be legitimate, but a "
                    "strong night-time concentration deserves review."
                ),
                events=night_events,
                related_numbers=(event["contact"] for event in night_events),
            )
        )

    events_by_day = group_events_by_day(events)

    if len(events_by_day) >= 2:
        peak_day, peak_events = max(
            events_by_day.items(),
            key=lambda item: len(item[1]),
        )
        other_counts = [
            len(day_events)
            for current_day, day_events in events_by_day.items()
            if current_day != peak_day
        ]
        baseline_average = (
            sum(other_counts) / len(other_counts) if other_counts else 0.0
        )

        if (
            len(peak_events) >= 20
            and baseline_average > 0
            and len(peak_events) >= baseline_average * 3
        ):
            patterns.append(
                make_pattern(
                    rule_code="SUDDEN_DAILY_SPIKE",
                    title="Sudden daily activity spike",
                    category="call",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{len(peak_events)} records on {peak_day}",
                    comparison_value=f"Other-day average {baseline_average:.1f}",
                    window_start=peak_events[0]["timestamp"],
                    window_end=peak_events[-1]["timestamp"],
                    reason="one evidence day had at least three times its usual daily activity",
                    explanation=(
                        "A sudden spike can represent coordination, an emergency, automated "
                        "use, or another event-linked behavioural change."
                    ),
                    events=peak_events,
                    related_numbers=(event["contact"] for event in peak_events),
                )
            )

    if options["devices"]:
        imeis = {event["imei"] for event in events if event["imei"]}
        imsis = {event["imsi"] for event in events if event["imsi"]}

        if len(imeis) > 3:
            patterns.append(
                make_pattern(
                    rule_code="IMEI_COUNT_FULL",
                    title="Frequent device changes across evidence",
                    category="device",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{len(imeis)} unique IMEIs",
                    comparison_value="More than 3 IMEIs",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="it used more than three different handset identities in the selected evidence",
                    explanation=(
                        "One handset replacement can be normal. Repeated changes across a "
                        "short evidence period deserve investigator review."
                    ),
                    events=events,
                    imeis=imeis,
                )
            )

        if len(imsis) > 3:
            patterns.append(
                make_pattern(
                    rule_code="IMSI_COUNT_FULL",
                    title="Frequent SIM identity changes across evidence",
                    category="device",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{len(imsis)} unique IMSIs",
                    comparison_value="More than 3 IMSIs",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="it used more than three different subscriber identities in the selected evidence",
                    explanation=(
                        "Dual-SIM use may explain two identities, while repeated subscriber "
                        "identity changes in a short file are more unusual."
                    ),
                    events=events,
                    imsis=imsis,
                )
            )

        imsi_to_imeis: dict[str, set[str]] = defaultdict(set)
        imei_to_imsis: dict[str, set[str]] = defaultdict(set)

        for event in events:
            if event["imsi"] and event["imei"]:
                imsi_to_imeis[event["imsi"]].add(event["imei"])
                imei_to_imsis[event["imei"]].add(event["imsi"])

        for imsi, associated_imeis in imsi_to_imeis.items():
            if len(associated_imeis) > 3:
                matching_events = [
                    event for event in events if event["imsi"] == imsi
                ]
                patterns.append(
                    make_pattern(
                        rule_code="MANY_IMEIS_FOR_IMSI",
                        title="One IMSI used with many IMEIs",
                        category="device",
                        scope="full_evidence",
                        phone_number=phone_number,
                        observed_value=f"{len(associated_imeis)} IMEIs for one IMSI",
                        comparison_value="More than 3 IMEIs",
                        window_start=matching_events[0]["timestamp"],
                        window_end=matching_events[-1]["timestamp"],
                        reason="one subscriber identity was used with more than three different devices",
                        explanation=(
                            "This can indicate repeated handset switching, SIM sharing, device "
                            "testing, or legitimate repair and replacement activity."
                        ),
                        events=matching_events,
                        imeis=associated_imeis,
                        imsis=[imsi],
                    )
                )

        for imei, associated_imsis in imei_to_imsis.items():
            if len(associated_imsis) > 3:
                matching_events = [
                    event for event in events if event["imei"] == imei
                ]
                patterns.append(
                    make_pattern(
                        rule_code="MANY_IMSIS_FOR_IMEI",
                        title="One IMEI used with many IMSIs",
                        category="device",
                        scope="full_evidence",
                        phone_number=phone_number,
                        observed_value=f"{len(associated_imsis)} IMSIs for one IMEI",
                        comparison_value="More than 3 IMSIs",
                        window_start=matching_events[0]["timestamp"],
                        window_end=matching_events[-1]["timestamp"],
                        reason="one device identity was used with more than three different SIM identities",
                        explanation=(
                            "This can indicate repeated SIM switching, device sharing, testing, "
                            "or a legitimate multi-user device."
                        ),
                        events=matching_events,
                        imeis=[imei],
                        imsis=associated_imsis,
                    )
                )

        for imei in imeis:
            related_targets = device_to_target_numbers.get(imei, set())
            if len(related_targets) > 3:
                matching_events = [
                    event for event in events if event["imei"] == imei
                ]
                patterns.append(
                    make_pattern(
                        rule_code="DEVICE_SHARED_BY_TARGETS",
                        title="One device shared by many target numbers",
                        category="device",
                        scope="full_evidence",
                        phone_number=phone_number,
                        observed_value=f"{len(related_targets)} target numbers on one IMEI",
                        comparison_value="More than 3 target numbers",
                        window_start=matching_events[0]["timestamp"],
                        window_end=matching_events[-1]["timestamp"],
                        reason="its device identity was also associated with several target numbers in the evidence",
                        explanation=(
                            "A shared device can be legitimate, but one IMEI linked with many "
                            "target numbers is a useful cross-number pattern."
                        ),
                        events=matching_events,
                        related_numbers=related_targets,
                        imeis=[imei],
                    )
                )

    if options["forwarding"]:
        forwarded_events = [event for event in events if event["forwarding"]]
        forwarding_base = max(1, len(incoming_events))
        forwarding_ratio = ratio_percent(
            len(forwarded_events),
            forwarding_base,
        )

        if len(forwarded_events) >= 5 and forwarding_ratio >= 30:
            patterns.append(
                make_pattern(
                    rule_code="FORWARDING_RATIO_FULL",
                    title="High call-forwarding percentage",
                    category="forwarding",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{len(forwarded_events)} records ({forwarding_ratio}%)",
                    comparison_value="30% or more of incoming activity",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="call forwarding appeared in a high percentage of its incoming activity",
                    explanation=(
                        "This may be normal business routing, but a high forwarding proportion "
                        "should be reviewed with account context."
                    ),
                    events=forwarded_events,
                    related_numbers=(
                        event["forwarding"] for event in forwarded_events
                    ),
                )
            )

    if options["roaming"]:
        roaming_events = [event for event in events if event["roaming"]]
        roaming_ratio = ratio_percent(len(roaming_events), len(events))

        if len(events) >= 20 and roaming_ratio >= 30:
            patterns.append(
                make_pattern(
                    rule_code="ROAMING_RATIO_FULL",
                    title="High roaming activity percentage",
                    category="roaming",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=f"{roaming_ratio}% roaming records",
                    comparison_value="30% or more",
                    window_start=evidence_start,
                    window_end=evidence_end,
                    reason="a substantial percentage of its records were marked as roaming",
                    explanation=(
                        "Travel may be legitimate. The pattern is displayed as network context "
                        "and not as proof of wrongdoing."
                    ),
                    events=roaming_events,
                )
            )

        roaming_by_day: dict[date, set[str]] = defaultdict(set)
        roaming_day_events: dict[date, list[dict[str, Any]]] = defaultdict(list)

        for event in roaming_events:
            network = clean_text(event["roaming_network"])
            if network:
                current_day = event["timestamp"].date()
                roaming_by_day[current_day].add(network)
                roaming_day_events[current_day].append(event)

        for current_day, networks in roaming_by_day.items():
            if len(networks) >= 2:
                day_events = roaming_day_events[current_day]
                patterns.append(
                    make_pattern(
                        rule_code="MULTIPLE_ROAMING_NETWORKS_DAY",
                        title="Multiple roaming networks in one day",
                        category="roaming",
                        scope="full_evidence",
                        phone_number=phone_number,
                        observed_value=f"{len(networks)} roaming networks on {current_day}",
                        comparison_value="2 or more networks",
                        window_start=day_events[0]["timestamp"],
                        window_end=day_events[-1]["timestamp"],
                        reason="it appeared on multiple roaming networks during the same day",
                        explanation=(
                            "This can indicate genuine travel, rapid network transitions, or "
                            "a data-quality issue that deserves verification."
                        ),
                        events=day_events,
                    )
                )

    if options["location"]:
        movements = rapid_movement_details(events)

        if movements:
            strongest = max(movements, key=lambda item: item["speed"])
            movement_events = [
                event
                for movement in movements
                for event in movement["events"]
            ]
            cells = {
                value
                for event in movement_events
                for value in (event["cell_id"], event["last_cell_id"])
                if value
            }

            patterns.append(
                make_pattern(
                    rule_code="RAPID_LOCATION_MOVEMENT",
                    title="Rapid or impossible location movement",
                    category="location",
                    scope="full_evidence",
                    phone_number=phone_number,
                    observed_value=(
                        f"{strongest['speed']:.1f} km/h across "
                        f"{strongest['distance']:.1f} km"
                    ),
                    comparison_value="More than 300 km/h across at least 50 km",
                    window_start=strongest["start"],
                    window_end=strongest["end"],
                    reason="its tower coordinates imply unusually rapid movement",
                    explanation=(
                        "The pattern may indicate rapid travel, inaccurate tower coordinates, "
                        "clock differences, or another data-quality issue. Coordinates should "
                        "be verified before drawing a conclusion."
                    ),
                    events=movement_events,
                    cell_ids=cells,
                )
            )

    return patterns


# =========================================================
# Incident-comparison rules
# =========================================================


def incident_patterns(
    phone_number: str,
    events: list[dict[str, Any]],
    incident_datetime: datetime,
    incident_cell_ids: set[str],
    evidence_end: datetime | None,
    options: dict[str, bool],
) -> list[dict[str, Any]]:
    if not events:
        return []

    patterns: list[dict[str, Any]] = []

    day_start = incident_datetime.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    day_end = day_start + timedelta(days=1)

    immediate_start = incident_datetime - timedelta(hours=2)
    immediate_end = incident_datetime + timedelta(hours=2)

    baseline_exclusion_start = incident_datetime - timedelta(hours=24)
    baseline_exclusion_end = incident_datetime + timedelta(hours=24)

    incident_day = [
        event for event in events if day_start <= event["timestamp"] < day_end
    ]
    immediate = [
        event
        for event in events
        if immediate_start <= event["timestamp"] <= immediate_end
    ]
    baseline = [
        event
        for event in events
        if not (
            baseline_exclusion_start
            <= event["timestamp"]
            <= baseline_exclusion_end
        )
    ]

    baseline_days = unique_days(baseline)

    incident_calls = [
        event for event in incident_day if event["event_type"] == "call"
    ]
    baseline_calls = [
        event for event in baseline if event["event_type"] == "call"
    ]
    baseline_call_average = len(baseline_calls) / baseline_days

    if options["calls"] and len(incident_calls) >= 10:
        call_multiple = len(incident_calls) / max(1.0, baseline_call_average)

        if call_multiple >= 2:
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_CALL_SPIKE",
                    title="Incident-day call spike",
                    category="call",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=(
                        f"{len(incident_calls)} calls "
                        f"({call_multiple:.1f}× baseline)"
                    ),
                    comparison_value=(
                        f"Baseline average {baseline_call_average:.1f} calls/day"
                    ),
                    window_start=day_start,
                    window_end=day_end,
                    reason="its call activity increased sharply on the selected incident day",
                    explanation=(
                        "The comparison uses the number's own non-incident behaviour, so it can "
                        "detect a meaningful change even when the absolute count is not extreme."
                    ),
                    events=incident_calls,
                    related_numbers=(
                        event["contact"] for event in incident_calls
                    ),
                )
            )

        immediate_calls = [
            event for event in immediate if event["event_type"] == "call"
        ]
        baseline_hourly_calls = len(baseline_calls) / max(1, baseline_days * 24)
        expected_four_hours = baseline_hourly_calls * 4

        if (
            len(immediate_calls) >= 10
            and len(immediate_calls) >= max(10, expected_four_hours * 3)
        ):
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_CALL_BURST",
                    title="Immediate call burst around incident",
                    category="call",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=(
                        f"{len(immediate_calls)} calls within 2 hours before and after"
                    ),
                    comparison_value=(
                        f"Expected about {expected_four_hours:.1f} from baseline"
                    ),
                    window_start=immediate_start,
                    window_end=immediate_end,
                    reason="many calls occurred immediately before and after the incident time",
                    explanation=(
                        "This can represent coordination, warnings, emergency communication, "
                        "or another incident-linked burst."
                    ),
                    events=immediate_calls,
                    related_numbers=(
                        event["contact"] for event in immediate_calls
                    ),
                )
            )

    baseline_sms = [
        event
        for event in baseline
        if event["event_type"] == "sms"
        and event["direction"] == "outgoing"
    ]
    incident_sms = [
        event
        for event in incident_day
        if event["event_type"] == "sms"
        and event["direction"] == "outgoing"
    ]

    if options["sms"] and len(incident_sms) >= 10:
        baseline_sms_average = len(baseline_sms) / baseline_days
        sms_multiple = len(incident_sms) / max(1.0, baseline_sms_average)

        if sms_multiple >= 2:
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_SMS_SPIKE",
                    title="Incident-day outgoing SMS spike",
                    category="sms",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=(
                        f"{len(incident_sms)} SMS "
                        f"({sms_multiple:.1f}× baseline)"
                    ),
                    comparison_value=(
                        f"Baseline average {baseline_sms_average:.1f} SMS/day"
                    ),
                    window_start=day_start,
                    window_end=day_end,
                    reason="its outgoing message activity increased sharply on the incident day",
                    explanation=(
                        "The pattern can identify incident-linked messaging even when the "
                        "absolute total is not extremely high."
                    ),
                    events=incident_sms,
                    related_numbers=(
                        event["contact"] for event in incident_sms
                    ),
                )
            )

    baseline_incoming = [
        event for event in baseline if event["direction"] == "incoming"
    ]
    baseline_outgoing = [
        event for event in baseline if event["direction"] == "outgoing"
    ]
    incident_incoming = [
        event for event in incident_day if event["direction"] == "incoming"
    ]
    incident_outgoing = [
        event for event in incident_day if event["direction"] == "outgoing"
    ]

    if len(baseline) >= 10 and len(incident_day) >= 10:
        baseline_outgoing_ratio = ratio_percent(
            len(baseline_outgoing),
            len(baseline),
        )
        incident_outgoing_ratio = ratio_percent(
            len(incident_outgoing),
            len(incident_day),
        )
        outgoing_change = incident_outgoing_ratio - baseline_outgoing_ratio

        baseline_incoming_ratio = ratio_percent(
            len(baseline_incoming),
            len(baseline),
        )
        incident_incoming_ratio = ratio_percent(
            len(incident_incoming),
            len(incident_day),
        )
        incoming_change = incident_incoming_ratio - baseline_incoming_ratio

        if abs(outgoing_change) >= 35 or abs(incoming_change) >= 35:
            if abs(outgoing_change) >= abs(incoming_change):
                direction = "outgoing"
                incident_ratio = incident_outgoing_ratio
                baseline_ratio = baseline_outgoing_ratio
                ratio_change = outgoing_change
            else:
                direction = "incoming"
                incident_ratio = incident_incoming_ratio
                baseline_ratio = baseline_incoming_ratio
                ratio_change = incoming_change

            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_DIRECTION_CHANGE",
                    title=f"Incident-day {direction} ratio change",
                    category="call",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=(
                        f"{incident_ratio}% {direction} on incident day"
                    ),
                    comparison_value=(
                        f"Baseline {baseline_ratio}% "
                        f"({abs(ratio_change):.1f} percentage-point change)"
                    ),
                    window_start=day_start,
                    window_end=day_end,
                    reason=f"its {direction} communication ratio changed sharply on the incident day",
                    explanation=(
                        "A large incoming or outgoing ratio change can show that the number "
                        "adopted a different communication role near the incident."
                    ),
                    events=incident_day,
                )
            )

    baseline_contacts = {
        event["contact"] for event in baseline if event["contact"]
    }
    incident_contacts = {
        event["contact"] for event in incident_day if event["contact"]
    }

    if len(incident_contacts) >= 10:
        baseline_daily_contacts = unique_contacts_per_day(baseline)
        contact_multiple = len(incident_contacts) / max(1.0, baseline_daily_contacts)

        if contact_multiple >= 2:
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_CONTACT_INCREASE",
                    title="Incident-day unique-contact increase",
                    category="contact",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=(
                        f"{len(incident_contacts)} unique contacts "
                        f"({contact_multiple:.1f}× baseline)"
                    ),
                    comparison_value=(
                        f"Baseline average {baseline_daily_contacts:.1f} contacts/day"
                    ),
                    window_start=day_start,
                    window_end=day_end,
                    reason="it communicated with far more unique contacts on the incident day than on normal days",
                    explanation=(
                        "A sudden increase in contact diversity can indicate coordination, "
                        "mass notification, emergency activity, or another event-linked change."
                    ),
                    events=incident_day,
                    related_numbers=incident_contacts,
                )
            )

        new_contacts = incident_contacts - baseline_contacts
        new_contact_ratio = ratio_percent(
            len(new_contacts),
            len(incident_contacts),
        )

        if new_contact_ratio >= 50:
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_NEW_CONTACTS",
                    title="High percentage of new incident-day contacts",
                    category="contact",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{new_contact_ratio}% new contacts",
                    comparison_value="50% or more",
                    window_start=day_start,
                    window_end=day_end,
                    reason="at least half of its incident-day contacts were not seen in the baseline period",
                    explanation=(
                        "A sudden new contact set may be important to an investigation, while "
                        "legitimate events can also create temporary contact changes."
                    ),
                    events=incident_day,
                    related_numbers=new_contacts,
                )
            )

    contacts_before_immediate = {
        event["contact"]
        for event in events
        if event["timestamp"] < immediate_start and event["contact"]
    }
    immediate_contact_counts = Counter(
        event["contact"] for event in immediate if event["contact"]
    )
    first_time_repeated_contacts = {
        contact
        for contact, count in immediate_contact_counts.items()
        if count >= 3 and contact not in contacts_before_immediate
    }

    if first_time_repeated_contacts:
        matching_events = [
            event
            for event in immediate
            if event["contact"] in first_time_repeated_contacts
        ]
        patterns.append(
            make_pattern(
                rule_code="FIRST_CONTACT_NEAR_INCIDENT",
                title="First-time repeated contact near incident",
                category="contact",
                scope="incident",
                phone_number=phone_number,
                observed_value=(
                    f"{len(first_time_repeated_contacts)} new repeated contact(s)"
                ),
                comparison_value="First observed near incident and contacted at least 3 times",
                window_start=immediate_start,
                window_end=immediate_end,
                reason="it repeatedly communicated with previously unseen contacts near the incident time",
                explanation=(
                    "A first-time contact near an incident is useful relationship evidence, "
                    "but the purpose of the communication must be verified separately."
                ),
                events=matching_events,
                related_numbers=first_time_repeated_contacts,
            )
        )

    historical_before = [
        event
        for event in events
        if event["timestamp"] < incident_datetime - timedelta(hours=6)
    ]
    device_window = [
        event
        for event in events
        if incident_datetime - timedelta(hours=6)
        <= event["timestamp"]
        <= incident_datetime + timedelta(hours=2)
    ]

    historical_imeis = {
        event["imei"] for event in historical_before if event["imei"]
    }
    historical_imsis = {
        event["imsi"] for event in historical_before if event["imsi"]
    }
    near_imeis = {
        event["imei"] for event in device_window if event["imei"]
    }
    near_imsis = {
        event["imsi"] for event in device_window if event["imsi"]
    }
    new_imeis = near_imeis - historical_imeis
    new_imsis = near_imsis - historical_imsis

    if options["devices"] and historical_imeis and new_imeis:
        patterns.append(
            make_pattern(
                rule_code="INCIDENT_IMEI_CHANGE",
                title="New device identity near incident",
                category="device",
                scope="incident",
                phone_number=phone_number,
                observed_value=f"{len(new_imeis)} new IMEI value(s)",
                comparison_value="Not observed in earlier evidence",
                window_start=incident_datetime - timedelta(hours=6),
                window_end=incident_datetime + timedelta(hours=2),
                reason="a previously unseen device identity appeared near the incident",
                explanation=(
                    "A handset replacement may be legitimate, but a change close to the "
                    "incident is useful technical context."
                ),
                events=device_window,
                imeis=new_imeis,
            )
        )

    if options["devices"] and historical_imsis and new_imsis:
        patterns.append(
            make_pattern(
                rule_code="INCIDENT_IMSI_CHANGE",
                title="New SIM identity near incident",
                category="device",
                scope="incident",
                phone_number=phone_number,
                observed_value=f"{len(new_imsis)} new IMSI value(s)",
                comparison_value="Not observed in earlier evidence",
                window_start=incident_datetime - timedelta(hours=6),
                window_end=incident_datetime + timedelta(hours=2),
                reason="a previously unseen subscriber identity appeared near the incident",
                explanation=(
                    "A SIM replacement or dual-SIM use may be legitimate, but a new identity "
                    "close to the incident deserves review."
                ),
                events=device_window,
                imsis=new_imsis,
            )
        )

    if options["devices"] and new_imeis and new_imsis:
        patterns.append(
            make_pattern(
                rule_code="INCIDENT_IMEI_IMSI_CHANGE",
                title="IMEI and IMSI both changed near incident",
                category="device",
                scope="incident",
                phone_number=phone_number,
                observed_value=(
                    f"{len(new_imeis)} new IMEI and {len(new_imsis)} new IMSI"
                ),
                comparison_value="Both were absent from earlier evidence",
                window_start=incident_datetime - timedelta(hours=6),
                window_end=incident_datetime + timedelta(hours=2),
                reason="both its device identity and subscriber identity changed near the incident",
                explanation=(
                    "A combined device and SIM change is stronger investigative context than "
                    "either change alone, although legitimate replacement remains possible."
                ),
                events=device_window,
                imeis=new_imeis,
                imsis=new_imsis,
            )
        )

    if options["location"]:
        baseline_cells = {
            cell
            for event in baseline
            for cell in (event["cell_id"], event["last_cell_id"])
            if cell
        }
        immediate_cells = {
            cell
            for event in immediate
            for cell in (event["cell_id"], event["last_cell_id"])
            if cell
        }
        new_cells = immediate_cells - baseline_cells

        if baseline_cells and new_cells:
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_NEW_CELL",
                    title="New tower used around incident",
                    category="location",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{len(new_cells)} new tower(s)",
                    comparison_value="Not observed in baseline",
                    window_start=immediate_start,
                    window_end=immediate_end,
                    reason="it used towers near the incident time that were not present in its baseline activity",
                    explanation=(
                        "A new tower can indicate travel or a changed activity area. Tower "
                        "coordinates and coverage should be verified."
                    ),
                    events=immediate,
                    cell_ids=new_cells,
                )
            )

        if incident_cell_ids:
            matching_tower_events = [
                event
                for event in immediate
                if event["cell_id"] in incident_cell_ids
                or event["last_cell_id"] in incident_cell_ids
            ]

            if matching_tower_events:
                matched_cells = {
                    cell
                    for event in matching_tower_events
                    for cell in (event["cell_id"], event["last_cell_id"])
                    if cell in incident_cell_ids
                }
                patterns.append(
                    make_pattern(
                        rule_code="INCIDENT_TOWER_PRESENCE",
                        title="Activity at an incident tower",
                        category="location",
                        scope="incident",
                        phone_number=phone_number,
                        observed_value=(
                            f"{len(matching_tower_events)} record(s) at selected incident tower(s)"
                        ),
                        comparison_value="Within 2 hours before or after incident",
                        window_start=immediate_start,
                        window_end=immediate_end,
                        reason="its records matched one or more incident cell IDs near the selected time",
                        explanation=(
                            "A tower match indicates possible network presence in the tower's "
                            "coverage area. It does not prove exact physical location."
                        ),
                        events=matching_tower_events,
                        cell_ids=matched_cells,
                    )
                )

        location_window = [
            event
            for event in events
            if incident_datetime - timedelta(hours=6)
            <= event["timestamp"]
            <= incident_datetime + timedelta(hours=6)
        ]
        movements = rapid_movement_details(location_window)

        if movements:
            strongest = max(movements, key=lambda item: item["speed"])
            movement_events = [
                event
                for movement in movements
                for event in movement["events"]
            ]
            movement_cells = {
                cell
                for event in movement_events
                for cell in (event["cell_id"], event["last_cell_id"])
                if cell
            }
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_RAPID_MOVEMENT",
                    title="Rapid location movement near incident",
                    category="location",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=(
                        f"{strongest['speed']:.1f} km/h across "
                        f"{strongest['distance']:.1f} km"
                    ),
                    comparison_value="More than 300 km/h across at least 50 km",
                    window_start=strongest["start"],
                    window_end=strongest["end"],
                    reason="its tower coordinates imply unusually rapid movement near the incident",
                    explanation=(
                        "This may indicate rapid travel or inaccurate tower, time, or coordinate "
                        "data. The underlying records should be verified."
                    ),
                    events=movement_events,
                    cell_ids=movement_cells,
                )
            )

    if options["forwarding"]:
        baseline_forwarding = {
            event["forwarding"] for event in baseline if event["forwarding"]
        }
        incident_forwarding = {
            event["forwarding"]
            for event in incident_day
            if event["forwarding"]
        }
        new_forwarding = incident_forwarding - baseline_forwarding

        if new_forwarding:
            forwarding_events = [
                event
                for event in incident_day
                if event["forwarding"] in new_forwarding
            ]
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_FORWARDING_CHANGE",
                    title="Call forwarding activated near incident",
                    category="forwarding",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{len(new_forwarding)} new destination(s)",
                    comparison_value="Not observed in baseline",
                    window_start=day_start,
                    window_end=day_end,
                    reason="new call-forwarding destinations appeared on the incident day",
                    explanation=(
                        "This may be legitimate routing, but a forwarding change near an "
                        "incident is useful investigative context."
                    ),
                    events=forwarding_events,
                    related_numbers=new_forwarding,
                )
            )

    if options["roaming"]:
        baseline_roaming = any(event["roaming"] for event in baseline)
        incident_roaming = [
            event for event in incident_day if event["roaming"]
        ]
        baseline_networks = {
            event["roaming_network"]
            for event in baseline
            if event["roaming_network"]
        }
        incident_networks = {
            event["roaming_network"]
            for event in incident_day
            if event["roaming_network"]
        }
        new_networks = incident_networks - baseline_networks

        if incident_roaming and (not baseline_roaming or new_networks):
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_ROAMING_CHANGE",
                    title="Roaming state changed near incident",
                    category="roaming",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{len(incident_roaming)} roaming record(s)",
                    comparison_value=(
                        "No roaming in baseline"
                        if not baseline_roaming
                        else f"{len(new_networks)} new roaming network(s)"
                    ),
                    window_start=day_start,
                    window_end=day_end,
                    reason="its roaming state or roaming network changed on the incident day",
                    explanation=(
                        "Travel may be legitimate, but a new roaming state helps explain a "
                        "network or location change near the incident."
                    ),
                    events=incident_roaming,
                )
            )

    if options["calls"] and len(incident_calls) >= 10 and baseline_calls:
        baseline_short_ratio = ratio_percent(
            len([event for event in baseline_calls if event["duration"] <= 10]),
            len(baseline_calls),
        )
        incident_short_events = [
            event for event in incident_calls if event["duration"] <= 10
        ]
        incident_short_ratio = ratio_percent(
            len(incident_short_events),
            len(incident_calls),
        )

        if (
            incident_short_ratio >= 60
            and incident_short_ratio - baseline_short_ratio >= 30
        ):
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_SHORT_CALL_INCREASE",
                    title="Short-call ratio increased near incident",
                    category="call",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{incident_short_ratio}% short calls",
                    comparison_value=f"Baseline {baseline_short_ratio}%",
                    window_start=day_start,
                    window_end=day_end,
                    reason="its short-call percentage rose sharply on the incident day",
                    explanation=(
                        "A sudden increase in short calls can represent repeated retrying, "
                        "rapid coordination, automated dialling, or legitimate urgency."
                    ),
                    events=incident_short_events,
                )
            )

        baseline_zero_ratio = ratio_percent(
            len([event for event in baseline_calls if event["duration"] == 0]),
            len(baseline_calls),
        )
        incident_zero_events = [
            event for event in incident_calls if event["duration"] == 0
        ]
        incident_zero_ratio = ratio_percent(
            len(incident_zero_events),
            len(incident_calls),
        )

        if (
            incident_zero_ratio >= 30
            and incident_zero_ratio - baseline_zero_ratio >= 20
        ):
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_ZERO_CALL_INCREASE",
                    title="Zero-duration call ratio increased near incident",
                    category="call",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{incident_zero_ratio}% zero-duration calls",
                    comparison_value=f"Baseline {baseline_zero_ratio}%",
                    window_start=day_start,
                    window_end=day_end,
                    reason="its zero-duration voice-call percentage rose sharply on the incident day",
                    explanation=(
                        "This can indicate failed attempts, repeated retrying, network issues, "
                        "or another incident-linked call pattern."
                    ),
                    events=incident_zero_events,
                )
            )

    post_end = incident_datetime + timedelta(minutes=30)
    post_incident_outgoing = [
        event
        for event in events
        if incident_datetime <= event["timestamp"] <= post_end
        and event["direction"] == "outgoing"
    ]

    if len(post_incident_outgoing) >= 10:
        patterns.append(
            make_pattern(
                rule_code="POST_INCIDENT_BURST",
                title="Post-incident communication burst",
                category="call",
                scope="incident",
                phone_number=phone_number,
                observed_value=(
                    f"{len(post_incident_outgoing)} outgoing records in 30 minutes"
                ),
                comparison_value="10 or more outgoing records",
                window_start=incident_datetime,
                window_end=post_end,
                reason="many outgoing communications occurred immediately after the incident time",
                explanation=(
                    "This may represent notification, coordination, emergency communication, "
                    "or another response to the incident."
                ),
                events=post_incident_outgoing,
                related_numbers=(
                    event["contact"] for event in post_incident_outgoing
                ),
            )
        )

    if evidence_end and evidence_end >= incident_datetime + timedelta(hours=12):
        activity_first_two_hours = [
            event
            for event in events
            if incident_datetime
            <= event["timestamp"]
            <= incident_datetime + timedelta(hours=2)
        ]
        activity_after_two_hours = [
            event
            for event in events
            if event["timestamp"] > incident_datetime + timedelta(hours=2)
        ]

        if activity_first_two_hours and not activity_after_two_hours:
            patterns.append(
                make_pattern(
                    rule_code="INCIDENT_SUDDEN_INACTIVITY",
                    title="Sudden inactivity after incident",
                    category="call",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value="No activity after the first two post-incident hours",
                    comparison_value="At least 12 hours of later evidence exists",
                    window_start=incident_datetime,
                    window_end=evidence_end,
                    reason="it became inactive shortly after the incident even though later evidence was available",
                    explanation=(
                        "A phone may be switched off, a SIM may be removed, coverage may be "
                        "lost, or the number may be abandoned."
                    ),
                    events=activity_first_two_hours,
                )
            )

    if options["devices"]:
        before_incident = [
            event for event in events if event["timestamp"] < incident_datetime
        ]
        after_incident = [
            event
            for event in events
            if incident_datetime < event["timestamp"] <= incident_datetime + timedelta(hours=24)
        ]
        later_after_incident = [
            event for event in events if event["timestamp"] > incident_datetime
        ]

        old_imeis = {event["imei"] for event in before_incident if event["imei"]}
        old_imsis = {event["imsi"] for event in before_incident if event["imsi"]}
        after_imeis = {event["imei"] for event in after_incident if event["imei"]}
        after_imsis = {event["imsi"] for event in after_incident if event["imsi"]}
        later_imeis = {
            event["imei"] for event in later_after_incident if event["imei"]
        }
        later_imsis = {
            event["imsi"] for event in later_after_incident if event["imsi"]
        }

        replacement_imeis = after_imeis - old_imeis
        replacement_imsis = after_imsis - old_imsis
        old_imei_disappeared = bool(old_imeis) and not (old_imeis & later_imeis)
        old_imsi_disappeared = bool(old_imsis) and not (old_imsis & later_imsis)

        if replacement_imeis and old_imei_disappeared:
            patterns.append(
                make_pattern(
                    rule_code="DEVICE_REPLACED_AFTER_INCIDENT",
                    title="Device replaced after incident",
                    category="device",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{len(replacement_imeis)} new post-incident IMEI value(s)",
                    comparison_value="Earlier IMEI values did not reappear",
                    window_start=incident_datetime,
                    window_end=incident_datetime + timedelta(hours=24),
                    reason="a new device appeared after the incident and the earlier device did not reappear",
                    explanation=(
                        "A legitimate replacement is possible, but a complete post-incident "
                        "device change is useful investigative context."
                    ),
                    events=after_incident,
                    imeis=replacement_imeis,
                )
            )

        if replacement_imsis and old_imsi_disappeared:
            patterns.append(
                make_pattern(
                    rule_code="SIM_REPLACED_AFTER_INCIDENT",
                    title="SIM identity replaced after incident",
                    category="device",
                    scope="incident",
                    phone_number=phone_number,
                    observed_value=f"{len(replacement_imsis)} new post-incident IMSI value(s)",
                    comparison_value="Earlier IMSI values did not reappear",
                    window_start=incident_datetime,
                    window_end=incident_datetime + timedelta(hours=24),
                    reason="a new SIM identity appeared after the incident and the earlier identity did not reappear",
                    explanation=(
                        "A legitimate SIM replacement is possible, but the timing should be "
                        "reviewed with subscriber and account information."
                    ),
                    events=after_incident,
                    imsis=replacement_imsis,
                )
            )

    return patterns


# =========================================================
# Summary and database entry point
# =========================================================


def build_summary(
    *,
    case_id: int,
    evidence_id: int,
    events_by_number: dict[str, list[dict[str, Any]]],
    patterns: list[dict[str, Any]],
    evidence_start: datetime | None,
    evidence_end: datetime | None,
    evidence_days: int,
    incident_datetime: datetime | None,
    incident_cell_ids: set[str],
) -> dict[str, Any]:
    patterns_by_number: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for pattern in patterns:
        patterns_by_number[pattern["phone_number"]].append(pattern)

    categories = [
        "call",
        "sms",
        "device",
        "contact",
        "location",
        "roaming",
        "forwarding",
    ]

    number_summaries: list[dict[str, Any]] = []

    for phone_number in sorted(events_by_number):
        number_patterns = patterns_by_number.get(phone_number, [])

        summary = {
            "phone_number": phone_number,
            "total_patterns": len(number_patterns),
            "short_window_patterns": sum(
                pattern["scope"] == "short_window"
                for pattern in number_patterns
            ),
            "full_evidence_patterns": sum(
                pattern["scope"] == "full_evidence"
                for pattern in number_patterns
            ),
            "incident_patterns": sum(
                pattern["scope"] == "incident"
                for pattern in number_patterns
            ),
        }

        for category in categories:
            summary[f"{category}_patterns"] = sum(
                pattern["category"] == category
                for pattern in number_patterns
            )

        number_summaries.append(summary)

    result: dict[str, Any] = {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "analysed_numbers": len(events_by_number),
        "evidence_start": evidence_start,
        "evidence_end": evidence_end,
        "evidence_days": evidence_days,
        "incident_datetime": incident_datetime,
        "incident_cell_ids": sorted(incident_cell_ids),
        "incident_rules_applied": incident_datetime is not None,
        "total_patterns": len(patterns),
        "short_window_patterns": sum(
            pattern["scope"] == "short_window" for pattern in patterns
        ),
        "full_evidence_patterns": sum(
            pattern["scope"] == "full_evidence" for pattern in patterns
        ),
        "incident_patterns": sum(
            pattern["scope"] == "incident" for pattern in patterns
        ),
        "number_summaries": sorted(
            number_summaries,
            key=lambda item: (
                -item["total_patterns"],
                item["phone_number"],
            ),
        ),
        "patterns": sorted(
            patterns,
            key=lambda item: (
                item["phone_number"],
                {
                    "incident": 0,
                    "short_window": 1,
                    "full_evidence": 2,
                }.get(item["scope"], 3),
                item["window_start"] or datetime.min,
                item["rule_code"],
            ),
        ),
        "disclaimer": DISCLAIMER,
    }

    for category in categories:
        result[f"{category}_patterns"] = sum(
            pattern["category"] == category for pattern in patterns
        )

    return result


def analyse_patterns(
    database: Session,
    case_id: int,
    evidence_id: int,
    phone_number: str | None = None,
    incident_datetime: datetime | None = None,
    incident_cell_ids: Iterable[str] = (),
    include_call_patterns: bool = True,
    include_sms_patterns: bool = True,
    include_device_patterns: bool = True,
    include_location_patterns: bool = True,
    include_roaming_patterns: bool = True,
    include_forwarding_patterns: bool = True,
) -> dict[str, Any]:
    records = list(
        database.scalars(
            select(CDRRecord)
            .where(
                CDRRecord.case_id == case_id,
                CDRRecord.evidence_id == evidence_id,
            )
            .order_by(
                CDRRecord.start_datetime.asc(),
                CDRRecord.id.asc(),
            )
        ).all()
    )

    timestamps = [
        record.start_datetime
        for record in records
        if record.start_datetime is not None
    ]
    evidence_start = min(timestamps) if timestamps else None
    evidence_end = max(timestamps) if timestamps else None
    evidence_days = (
        max(
            1,
            (evidence_end.date() - evidence_start.date()).days + 1,
        )
        if evidence_start and evidence_end
        else 0
    )

    normalized_number = normalize_phone(phone_number)
    numbers: set[str] = set()

    if normalized_number:
        numbers.add(normalized_number)
    else:
        # Analyse every phone number present anywhere in the selected CDR,
        # including target numbers and B-party/contact numbers.
        for record in records:
            for candidate in (
                record.caller_number,
                record.receiver_number,
                record.target_number,
                record.b_party_number,
            ):
                cleaned_number = normalize_phone(candidate)
                if cleaned_number:
                    numbers.add(cleaned_number)

    device_to_target_numbers: dict[str, set[str]] = defaultdict(set)

    for record in records:
        imei = record_imei(record)
        target = normalize_phone(record.target_number)

        if imei and target:
            device_to_target_numbers[imei].add(target)

    events_by_number: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for current_number in numbers:
        events_by_number[current_number] = []

    # Build all number timelines in one pass. A set prevents one CDR row from
    # being added twice when the same number appears in multiple source fields.
    for record in records:
        associated_numbers = {
            normalize_phone(record.caller_number),
            normalize_phone(record.receiver_number),
            normalize_phone(record.target_number),
            normalize_phone(record.b_party_number),
        }
        associated_numbers.discard("")

        for current_number in associated_numbers.intersection(numbers):
            event = record_to_event(record, current_number)
            if event is not None:
                events_by_number[current_number].append(event)

    events_by_number = {
        current_number: sorted(
            events,
            key=lambda event: (
                event["timestamp"],
                event["record_id"],
            ),
        )
        for current_number, events in events_by_number.items()
        if events
    }

    options = {
        "calls": include_call_patterns,
        "sms": include_sms_patterns,
        "devices": include_device_patterns,
        "location": include_location_patterns,
        "roaming": include_roaming_patterns,
        "forwarding": include_forwarding_patterns,
    }

    normalized_incident_cells = {
        clean_text(cell_id)
        for cell_id in incident_cell_ids
        if clean_text(cell_id)
    }

    patterns: list[dict[str, Any]] = []

    for current_number, events in events_by_number.items():
        patterns.extend(
            short_window_patterns(
                current_number,
                events,
                options,
            )
        )
        patterns.extend(
            full_evidence_patterns(
                current_number,
                events,
                evidence_days,
                options,
                device_to_target_numbers,
            )
        )

        if incident_datetime is not None:
            patterns.extend(
                incident_patterns(
                    current_number,
                    events,
                    incident_datetime,
                    normalized_incident_cells,
                    evidence_end,
                    options,
                )
            )

    return build_summary(
        case_id=case_id,
        evidence_id=evidence_id,
        events_by_number=events_by_number,
        patterns=patterns,
        evidence_start=evidence_start,
        evidence_end=evidence_end,
        evidence_days=evidence_days,
        incident_datetime=incident_datetime,
        incident_cell_ids=normalized_incident_cells,
    )