from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any, Callable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord


# =========================================================
# Large-dataset production-oriented thresholds
# =========================================================

CALL_THRESHOLDS = {
    "CALL_VOLUME_1H": {
        "threshold": 60,
        "window_minutes": 60,
        "risk_points": 25,
        "severity": "high",
    },

    "CALL_BURST_5M": {
        "threshold": 20,
        "window_minutes": 5,
        "risk_points": 30,
        "severity": "high",
    },

    "SHORT_CALLS_1H": {
        "threshold": 30,
        "window_minutes": 60,
        "maximum_duration": 10,
        "risk_points": 25,
        "severity": "high",
    },

    "ZERO_DURATION_CALLS_1D": {
        "threshold": 40,
        "window_minutes": 1440,
        "risk_points": 20,
        "severity": "medium",
    },

    "UNIQUE_CALL_CONTACTS_1H": {
        "threshold": 40,
        "window_minutes": 60,
        "risk_points": 30,
        "severity": "high",
    },

    "NIGHT_CALLS_1D": {
        "threshold": 30,
        "window_minutes": 1440,
        "risk_points": 15,
        "severity": "medium",
    },
}


SMS_THRESHOLDS = {
    "SMS_VOLUME_1H": {
        "threshold": 150,
        "window_minutes": 60,
        "risk_points": 30,
        "severity": "high",
    },

    "SMS_BURST_5M": {
        "threshold": 40,
        "window_minutes": 5,
        "risk_points": 35,
        "severity": "critical",
    },

    "UNIQUE_SMS_RECIPIENTS_1H": {
        "threshold": 80,
        "window_minutes": 60,
        "risk_points": 35,
        "severity": "critical",
    },

    "NIGHT_SMS_1D": {
        "threshold": 60,
        "window_minutes": 1440,
        "risk_points": 20,
        "severity": "medium",
    },
}


DEVICE_THRESHOLDS = {
    "IMEI_PER_IMSI_1D": {
        "threshold": 3,
        "window_minutes": 1440,
        "risk_points": 30,
        "severity": "high",
    },

    "IMSI_PER_IMEI_1D": {
        "threshold": 6,
        "window_minutes": 1440,
        "risk_points": 40,
        "severity": "critical",
    },
}


OTHER_THRESHOLDS = {
    "ROAMING_ACTIVITY_1D": {
        "threshold": 100,
        "window_minutes": 1440,
        "risk_points": 15,
        "severity": "medium",
    },

    "FORWARDED_CALLS_1D": {
        "threshold": 20,
        "window_minutes": 1440,
        "risk_points": 25,
        "severity": "high",
    },
}


DISCLAIMER = (
    "Fraud alerts are generated from communication metadata "
    "and behavioural rules. They indicate unusual activity "
    "requiring investigator review and do not independently "
    "prove fraud or criminal conduct."
)


# =========================================================
# Value normalization
# =========================================================

def clean_text(
    value: Any,
) -> str:
    return str(
        value or ""
    ).strip()


def normalize_phone_number(
    value: Any,
) -> str:
    text = clean_text(
        value
    )

    return "".join(
        character
        for character in text
        if character
        in "+0123456789"
    )


def normalize_event_type(
    record: CDRRecord,
) -> str:
    value = clean_text(
        getattr(
            record,
            "event_type",
            None,
        )
        or getattr(
            record,
            "service_type",
            None,
        )
    ).lower()

    if "sms" in value:
        return "sms"

    if (
        "voice" in value
        or "call" in value
    ):
        return "call"

    return value or "other"


def normalize_direction(
    record: CDRRecord,
) -> str:
    value = clean_text(
        getattr(
            record,
            "direction",
            None,
        )
        or getattr(
            record,
            "call_type",
            None,
        )
    ).lower()

    if value in {
        "out",
        "outgoing",
        "mo",
        "originating",
    }:
        return "outgoing"

    if value in {
        "in",
        "incoming",
        "mt",
        "terminating",
    }:
        return "incoming"

    if value.startswith("out"):
        return "outgoing"

    if value.startswith("in"):
        return "incoming"

    return "unknown"


def detect_roaming(
    record: CDRRecord,
) -> bool:
    value = getattr(
        record,
        "roaming",
        None,
    )

    if isinstance(
        value,
        bool,
    ):
        return value

    text = clean_text(
        value
        or getattr(
            record,
            "roaming_network_circle",
            None,
        )
    ).lower()

    return (
        "roam" in text
        or text in {
            "true",
            "yes",
            "1",
        }
    )


def get_forwarding_number(
    record: CDRRecord,
) -> str | None:
    value = clean_text(
        getattr(
            record,
            "call_forwarding_number",
            None,
        )
    )

    if not value:
        return None

    if value.lower() in {
        "not forwarded",
        "not forward",
        "na",
        "n/a",
        "none",
        "null",
        "-",
    }:
        return None

    normalized = normalize_phone_number(
        value
    )

    return normalized or value


# =========================================================
# Convert CDR database rows to fraud-analysis events
# =========================================================

def convert_record_to_event(
    record: CDRRecord,
) -> dict[str, Any] | None:
    if record.start_datetime is None:
        return None

    caller_number = (
        normalize_phone_number(
            record.caller_number
        )
    )

    receiver_number = (
        normalize_phone_number(
            record.receiver_number
        )
    )

    target_number = (
        normalize_phone_number(
            getattr(
                record,
                "target_number",
                None,
            )
        )
    )

    direction = normalize_direction(
        record
    )

    if target_number:
        phone_number = target_number

        if direction == "outgoing":
            contact_number = (
                receiver_number
            )

        elif direction == "incoming":
            contact_number = (
                caller_number
            )

        else:
            contact_number = (
                receiver_number
                or caller_number
            )

    else:
        phone_number = caller_number
        contact_number = receiver_number

    if not phone_number:
        return None

    imei = clean_text(
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
    ) or None

    imsi = clean_text(
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
    ) or None

    cell_id = clean_text(
        getattr(
            record,
            "cell_id",
            None,
        )
        or getattr(
            record,
            "first_cell_global_id",
            None,
        )
    ) or None

    return {
        "record_id": int(
            record.id
        ),

        "timestamp": (
            record.start_datetime
        ),

        "phone_number": (
            phone_number
        ),

        "contact_number": (
            contact_number
            or None
        ),

        "direction": direction,

        "event_type": (
            normalize_event_type(
                record
            )
        ),

        "duration_seconds": int(
            record.duration_seconds
            or 0
        ),

        "imei": imei,
        "imsi": imsi,
        "cell_id": cell_id,

        "roaming": (
            detect_roaming(
                record
            )
        ),

        "forwarding_number": (
            get_forwarding_number(
                record
            )
        ),
    }


# =========================================================
# Sliding window helpers
# =========================================================

def create_sliding_windows(
    events: list[
        dict[str, Any]
    ],
    window_minutes: int,
):
    queue: deque[
        dict[str, Any]
    ] = deque()

    duration = timedelta(
        minutes=window_minutes
    )

    for event in events:
        queue.append(
            event
        )

        while (
            queue
            and event["timestamp"]
            - queue[0]["timestamp"]
            > duration
        ):
            queue.popleft()

        yield list(
            queue
        )


def find_matching_windows(
    events: list[
        dict[str, Any]
    ],

    threshold: int,
    window_minutes: int,

    predicate: Callable[
        [dict[str, Any]],
        bool,
    ],

    distinct_function: Callable[
        [dict[str, Any]],
        Any,
    ] | None = None,
) -> list[
    tuple[
        list[dict[str, Any]],
        int,
    ]
]:
    eligible_events = [
        event
        for event in events
        if predicate(event)
    ]

    matches: list[
        tuple[
            list[dict[str, Any]],
            int,
        ]
    ] = []

    last_alert_end: datetime | None = None

    for current_window in create_sliding_windows(
        eligible_events,
        window_minutes,
    ):
        if distinct_function:
            observed_count = len(
                {
                    distinct_function(
                        event
                    )
                    for event
                    in current_window
                    if distinct_function(
                        event
                    )
                }
            )
        else:
            observed_count = len(
                current_window
            )

        if observed_count < threshold:
            continue

        current_end = (
            current_window[-1][
                "timestamp"
            ]
        )

        # Prevent many repeated alerts for one
        # continuing burst.
        if (
            last_alert_end is not None
            and current_end
            - last_alert_end
            < timedelta(
                minutes=window_minutes
            )
        ):
            continue

        matches.append(
            (
                current_window,
                observed_count,
            )
        )

        last_alert_end = (
            current_end
        )

    return matches


# =========================================================
# Alert creation
# =========================================================

def generate_alert_id(
    rule_code: str,
    phone_number: str,
    window_start: datetime,
    window_end: datetime,
    record_ids: list[int],
) -> str:
    value = "|".join(
        [
            rule_code,
            phone_number,
            window_start.isoformat(),
            window_end.isoformat(),
            ",".join(
                str(record_id)
                for record_id
                in record_ids
            ),
        ]
    )

    return sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()[:20]


def create_alert(
    *,
    rule_code: str,
    rule_name: str,
    category: str,
    severity: str,
    risk_points: int,

    case_id: int,
    evidence_id: int,
    phone_number: str,

    events: list[
        dict[str, Any]
    ],

    observed_value: int | float | str,
    threshold_value: int | float | str,

    description: str,
    explanation: str,
) -> dict[str, Any]:
    window_start = min(
        event["timestamp"]
        for event in events
    )

    window_end = max(
        event["timestamp"]
        for event in events
    )

    record_ids = sorted(
        {
            int(
                event["record_id"]
            )
            for event in events
        }
    )

    return {
        "alert_id": (
            generate_alert_id(
                rule_code,
                phone_number,
                window_start,
                window_end,
                record_ids,
            )
        ),

        "rule_code": rule_code,
        "rule_name": rule_name,
        "category": category,
        "severity": severity,
        "risk_points": risk_points,

        "case_id": case_id,
        "evidence_id": evidence_id,
        "phone_number": phone_number,

        "window_start": window_start,
        "window_end": window_end,

        "observed_value": (
            observed_value
        ),

        "threshold_value": (
            threshold_value
        ),

        "description": description,
        "explanation": explanation,

        "related_numbers": sorted(
            {
                event[
                    "contact_number"
                ]
                for event in events
                if event[
                    "contact_number"
                ]
            }
        )[:100],

        "imeis": sorted(
            {
                event["imei"]
                for event in events
                if event["imei"]
            }
        ),

        "imsis": sorted(
            {
                event["imsi"]
                for event in events
                if event["imsi"]
            }
        ),

        "cell_ids": sorted(
            {
                event["cell_id"]
                for event in events
                if event["cell_id"]
            }
        )[:100],

        "source_record_ids": (
            record_ids[:500]
        ),
    }


def run_count_rule(
    *,
    events: list[
        dict[str, Any]
    ],

    configuration: dict[
        str,
        Any,
    ],

    rule_code: str,
    rule_name: str,
    category: str,

    case_id: int,
    evidence_id: int,
    phone_number: str,

    predicate: Callable[
        [dict[str, Any]],
        bool,
    ],

    description: str,

    distinct_function: Callable[
        [dict[str, Any]],
        Any,
    ] | None = None,
) -> list[
    dict[str, Any]
]:
    threshold = int(
        configuration[
            "threshold"
        ]
    )

    window_minutes = int(
        configuration[
            "window_minutes"
        ]
    )

    matched_windows = (
        find_matching_windows(
            events=events,
            threshold=threshold,
            window_minutes=(
                window_minutes
            ),
            predicate=predicate,
            distinct_function=(
                distinct_function
            ),
        )
    )

    alerts: list[
        dict[str, Any]
    ] = []

    for (
        matching_events,
        observed_count,
    ) in matched_windows:
        alerts.append(
            create_alert(
                rule_code=rule_code,
                rule_name=rule_name,
                category=category,

                severity=configuration[
                    "severity"
                ],

                risk_points=int(
                    configuration[
                        "risk_points"
                    ]
                ),

                case_id=case_id,
                evidence_id=evidence_id,
                phone_number=(
                    phone_number
                ),

                events=matching_events,

                observed_value=(
                    observed_count
                ),

                threshold_value=(
                    threshold
                ),

                description=(
                    description
                ),

                explanation=(
                    f"Observed "
                    f"{observed_count} "
                    f"matching records in a "
                    f"{window_minutes}-minute "
                    f"window. The configured "
                    f"threshold is {threshold}."
                ),
            )
        )

    return alerts


# =========================================================
# Call fraud rules
# =========================================================

def detect_call_fraud(
    events: list[
        dict[str, Any]
    ],
    case_id: int,
    evidence_id: int,
    phone_number: str,
) -> list[
    dict[str, Any]
]:
    alerts: list[
        dict[str, Any]
    ] = []

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                CALL_THRESHOLDS[
                    "CALL_VOLUME_1H"
                ]
            ),

            rule_code=(
                "CALL_VOLUME_1H"
            ),

            rule_name=(
                "High call volume"
            ),

            category="call_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=lambda event: (
                event[
                    "event_type"
                ]
                == "call"
            ),

            description=(
                "A high number of voice "
                "calls occurred within "
                "one hour."
            ),
        )
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                CALL_THRESHOLDS[
                    "CALL_BURST_5M"
                ]
            ),

            rule_code=(
                "CALL_BURST_5M"
            ),

            rule_name=(
                "Rapid call burst"
            ),

            category="call_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=lambda event: (
                event[
                    "event_type"
                ]
                == "call"
            ),

            description=(
                "Calls occurred at an "
                "unusually high short-term "
                "rate."
            ),
        )
    )

    short_configuration = (
        CALL_THRESHOLDS[
            "SHORT_CALLS_1H"
        ]
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                short_configuration
            ),

            rule_code="SHORT_CALLS_1H",

            rule_name=(
                "Repeated short calls"
            ),

            category="call_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=lambda event: (
                event[
                    "event_type"
                ]
                == "call"
                and event[
                    "duration_seconds"
                ]
                <= short_configuration[
                    "maximum_duration"
                ]
            ),

            description=(
                "Many voice calls lasted "
                "ten seconds or less."
            ),
        )
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                CALL_THRESHOLDS[
                    "ZERO_DURATION_CALLS_1D"
                ]
            ),

            rule_code=(
                "ZERO_DURATION_CALLS_1D"
            ),

            rule_name=(
                "Excessive zero-duration calls"
            ),

            category="call_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=lambda event: (
                event[
                    "event_type"
                ]
                == "call"
                and event[
                    "duration_seconds"
                ]
                == 0
            ),

            description=(
                "Many zero-duration voice "
                "calls occurred within "
                "24 hours. SMS records are "
                "not included."
            ),
        )
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                CALL_THRESHOLDS[
                    "UNIQUE_CALL_CONTACTS_1H"
                ]
            ),

            rule_code=(
                "UNIQUE_CALL_CONTACTS_1H"
            ),

            rule_name=(
                "Many unique call contacts"
            ),

            category="call_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=lambda event: (
                event[
                    "event_type"
                ]
                == "call"
            ),

            distinct_function=(
                lambda event: event[
                    "contact_number"
                ]
            ),

            description=(
                "The number communicated "
                "with many unique contacts "
                "within one hour."
            ),
        )
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                CALL_THRESHOLDS[
                    "NIGHT_CALLS_1D"
                ]
            ),

            rule_code="NIGHT_CALLS_1D",

            rule_name=(
                "High night-time call activity"
            ),

            category="call_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=lambda event: (
                event[
                    "event_type"
                ]
                == "call"
                and 0
                <= event[
                    "timestamp"
                ].hour
                < 5
            ),

            description=(
                "High voice-call activity "
                "occurred between midnight "
                "and 05:00."
            ),
        )
    )

    return alerts


# =========================================================
# SMS fraud rules
# =========================================================

def detect_sms_fraud(
    events: list[
        dict[str, Any]
    ],
    case_id: int,
    evidence_id: int,
    phone_number: str,
) -> list[
    dict[str, Any]
]:
    alerts: list[
        dict[str, Any]
    ] = []

    def outgoing_sms(
        event: dict[
            str,
            Any,
        ],
    ) -> bool:
        return (
            event[
                "event_type"
            ]
            == "sms"
            and event[
                "direction"
            ]
            == "outgoing"
        )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                SMS_THRESHOLDS[
                    "SMS_VOLUME_1H"
                ]
            ),

            rule_code="SMS_VOLUME_1H",

            rule_name=(
                "High outgoing SMS volume"
            ),

            category="sms_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=outgoing_sms,

            description=(
                "A high number of outgoing "
                "SMS records occurred within "
                "one hour."
            ),
        )
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                SMS_THRESHOLDS[
                    "SMS_BURST_5M"
                ]
            ),

            rule_code="SMS_BURST_5M",

            rule_name=(
                "Rapid SMS burst"
            ),

            category="sms_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=outgoing_sms,

            description=(
                "Outgoing SMS messages "
                "occurred at a very high "
                "short-term rate."
            ),
        )
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                SMS_THRESHOLDS[
                    "UNIQUE_SMS_RECIPIENTS_1H"
                ]
            ),

            rule_code=(
                "UNIQUE_SMS_RECIPIENTS_1H"
            ),

            rule_name=(
                "Many unique SMS recipients"
            ),

            category="sms_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=outgoing_sms,

            distinct_function=(
                lambda event: event[
                    "contact_number"
                ]
            ),

            description=(
                "Outgoing SMS messages were "
                "sent to many different "
                "recipients within one hour."
            ),
        )
    )

    alerts.extend(
        run_count_rule(
            events=events,

            configuration=(
                SMS_THRESHOLDS[
                    "NIGHT_SMS_1D"
                ]
            ),

            rule_code="NIGHT_SMS_1D",

            rule_name=(
                "High night-time SMS activity"
            ),

            category="sms_fraud",

            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,

            predicate=lambda event: (
                outgoing_sms(event)
                and 0
                <= event[
                    "timestamp"
                ].hour
                < 5
            ),

            description=(
                "High outgoing SMS activity "
                "occurred between midnight "
                "and 05:00."
            ),
        )
    )

    return alerts


# =========================================================
# Device rules
# =========================================================

def detect_device_anomalies(
    events: list[
        dict[str, Any]
    ],
    case_id: int,
    evidence_id: int,
    phone_number: str,
) -> list[
    dict[str, Any]
]:
    alerts: list[
        dict[str, Any]
    ] = []

    configuration = (
        DEVICE_THRESHOLDS[
            "IMEI_PER_IMSI_1D"
        ]
    )

    for current_window in create_sliding_windows(
        events,
        configuration[
            "window_minutes"
        ],
    ):
        imsi_to_imeis: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for event in current_window:
            if (
                event["imsi"]
                and event["imei"]
            ):
                imsi_to_imeis[
                    event["imsi"]
                ].add(
                    event["imei"]
                )

        maximum_imeis = max(
            (
                len(imei_values)
                for imei_values
                in imsi_to_imeis.values()
            ),
            default=0,
        )

        if (
            maximum_imeis
            >= configuration[
                "threshold"
            ]
        ):
            alerts.append(
                create_alert(
                    rule_code=(
                        "IMEI_PER_IMSI_1D"
                    ),

                    rule_name=(
                        "One SIM used in "
                        "multiple devices"
                    ),

                    category=(
                        "device_anomaly"
                    ),

                    severity=configuration[
                        "severity"
                    ],

                    risk_points=configuration[
                        "risk_points"
                    ],

                    case_id=case_id,
                    evidence_id=evidence_id,
                    phone_number=phone_number,

                    events=current_window,

                    observed_value=(
                        maximum_imeis
                    ),

                    threshold_value=(
                        configuration[
                            "threshold"
                        ]
                    ),

                    description=(
                        "One IMSI was associated "
                        "with multiple IMEI "
                        "values within 24 hours."
                    ),

                    explanation=(
                        f"Maximum IMEIs associated "
                        f"with one IMSI: "
                        f"{maximum_imeis}."
                    ),
                )
            )

            break

    configuration = (
        DEVICE_THRESHOLDS[
            "IMSI_PER_IMEI_1D"
        ]
    )

    for current_window in create_sliding_windows(
        events,
        configuration[
            "window_minutes"
        ],
    ):
        imei_to_imsis: dict[
            str,
            set[str],
        ] = defaultdict(set)

        for event in current_window:
            if (
                event["imei"]
                and event["imsi"]
            ):
                imei_to_imsis[
                    event["imei"]
                ].add(
                    event["imsi"]
                )

        maximum_imsis = max(
            (
                len(imsi_values)
                for imsi_values
                in imei_to_imsis.values()
            ),
            default=0,
        )

        if (
            maximum_imsis
            >= configuration[
                "threshold"
            ]
        ):
            alerts.append(
                create_alert(
                    rule_code=(
                        "IMSI_PER_IMEI_1D"
                    ),

                    rule_name=(
                        "One device used with "
                        "many SIMs"
                    ),

                    category=(
                        "device_anomaly"
                    ),

                    severity=configuration[
                        "severity"
                    ],

                    risk_points=configuration[
                        "risk_points"
                    ],

                    case_id=case_id,
                    evidence_id=evidence_id,
                    phone_number=phone_number,

                    events=current_window,

                    observed_value=(
                        maximum_imsis
                    ),

                    threshold_value=(
                        configuration[
                            "threshold"
                        ]
                    ),

                    description=(
                        "One IMEI was associated "
                        "with many IMSI values "
                        "within 24 hours."
                    ),

                    explanation=(
                        f"Maximum IMSIs associated "
                        f"with one IMEI: "
                        f"{maximum_imsis}."
                    ),
                )
            )

            break

    return alerts


# =========================================================
# Roaming and forwarding rules
# =========================================================

def detect_other_anomalies(
    events: list[
        dict[str, Any]
    ],

    case_id: int,
    evidence_id: int,
    phone_number: str,

    include_roaming_rules: bool,
    include_forwarding_rules: bool,
) -> list[
    dict[str, Any]
]:
    alerts: list[
        dict[str, Any]
    ] = []

    if include_roaming_rules:
        alerts.extend(
            run_count_rule(
                events=events,

                configuration=(
                    OTHER_THRESHOLDS[
                        "ROAMING_ACTIVITY_1D"
                    ]
                ),

                rule_code=(
                    "ROAMING_ACTIVITY_1D"
                ),

                rule_name=(
                    "High roaming activity"
                ),

                category=(
                    "roaming_anomaly"
                ),

                case_id=case_id,
                evidence_id=evidence_id,
                phone_number=phone_number,

                predicate=lambda event: (
                    event["roaming"]
                ),

                description=(
                    "A high volume of CDR "
                    "activity occurred while "
                    "the subscriber was marked "
                    "as roaming."
                ),
            )
        )

    if include_forwarding_rules:
        alerts.extend(
            run_count_rule(
                events=events,

                configuration=(
                    OTHER_THRESHOLDS[
                        "FORWARDED_CALLS_1D"
                    ]
                ),

                rule_code=(
                    "FORWARDED_CALLS_1D"
                ),

                rule_name=(
                    "High call-forwarding activity"
                ),

                category=(
                    "forwarding_anomaly"
                ),

                case_id=case_id,
                evidence_id=evidence_id,
                phone_number=phone_number,

                predicate=lambda event: (
                    event[
                        "event_type"
                    ]
                    == "call"
                    and event[
                        "forwarding_number"
                    ]
                    is not None
                ),

                description=(
                    "Many forwarded voice "
                    "calls occurred within "
                    "24 hours."
                ),
            )
        )

    return alerts


# =========================================================
# Risk scoring
# =========================================================

def calculate_risk_level(
    risk_score: int,
) -> str:
    if risk_score >= 75:
        return "critical"

    if risk_score >= 50:
        return "high"

    if risk_score >= 25:
        return "medium"

    return "low"


# =========================================================
# Main fraud analysis function
# =========================================================

def analyse_fraud_rules(
    database: Session,
    case_id: int,
    evidence_id: int,

    phone_number: str | None = None,

    include_call_rules: bool = True,
    include_sms_rules: bool = True,
    include_device_rules: bool = True,
    include_roaming_rules: bool = True,
    include_forwarding_rules: bool = True,
) -> dict[str, Any]:
    query = select(
        CDRRecord
    ).where(
        CDRRecord.case_id == case_id,
        CDRRecord.evidence_id
        == evidence_id,
    )

    if phone_number:
        normalized_number = (
            normalize_phone_number(
                phone_number
            )
        )

        query = query.where(
            or_(
                CDRRecord.caller_number
                == normalized_number,

                CDRRecord.receiver_number
                == normalized_number,

                CDRRecord.target_number
                == normalized_number,

                CDRRecord.b_party_number
                == normalized_number,
            )
        )

    query = query.order_by(
        CDRRecord.start_datetime.asc(),
        CDRRecord.id.asc(),
    )

    records = list(
        database.scalars(
            query
        ).all()
    )

    events: list[
        dict[str, Any]
    ] = []

    for record in records:
        event = convert_record_to_event(
            record
        )

        if event is not None:
            events.append(
                event
            )

    events.sort(
        key=lambda event: (
            event[
                "phone_number"
            ],
            event[
                "timestamp"
            ],
            event[
                "record_id"
            ],
        )
    )

    events_by_number: dict[
        str,
        list[
            dict[str, Any]
        ],
    ] = defaultdict(list)

    for event in events:
        events_by_number[
            event[
                "phone_number"
            ]
        ].append(
            event
        )

    alerts: list[
        dict[str, Any]
    ] = []

    for (
        current_number,
        number_events,
    ) in events_by_number.items():
        if include_call_rules:
            alerts.extend(
                detect_call_fraud(
                    number_events,
                    case_id,
                    evidence_id,
                    current_number,
                )
            )

        if include_sms_rules:
            alerts.extend(
                detect_sms_fraud(
                    number_events,
                    case_id,
                    evidence_id,
                    current_number,
                )
            )

        if include_device_rules:
            alerts.extend(
                detect_device_anomalies(
                    number_events,
                    case_id,
                    evidence_id,
                    current_number,
                )
            )

        alerts.extend(
            detect_other_anomalies(
                events=number_events,

                case_id=case_id,
                evidence_id=evidence_id,
                phone_number=current_number,

                include_roaming_rules=(
                    include_roaming_rules
                ),

                include_forwarding_rules=(
                    include_forwarding_rules
                ),
            )
        )

    # De-duplicate alerts using stable alert IDs.
    alerts = list(
        {
            alert[
                "alert_id"
            ]: alert
            for alert in alerts
        }.values()
    )

    alerts.sort(
        key=lambda alert: (
            -int(
                alert[
                    "risk_points"
                ]
            ),

            alert[
                "window_start"
            ],

            alert[
                "phone_number"
            ],
        )
    )

    alerts_by_number: dict[
        str,
        list[
            dict[str, Any]
        ],
    ] = defaultdict(list)

    for alert in alerts:
        alerts_by_number[
            alert[
                "phone_number"
            ]
        ].append(
            alert
        )

    number_risks: list[
        dict[str, Any]
    ] = []

    for current_number in sorted(
        events_by_number.keys()
    ):
        current_alerts = (
            alerts_by_number.get(
                current_number,
                [],
            )
        )

        total_risk_score = min(
            100,
            sum(
                int(
                    alert[
                        "risk_points"
                    ]
                )
                for alert
                in current_alerts
            ),
        )

        category_counts: dict[
            str,
            int,
        ] = defaultdict(int)

        for alert in current_alerts:
            category_counts[
                alert["category"]
            ] += 1

        number_risks.append(
            {
                "phone_number": (
                    current_number
                ),

                "total_risk_score": (
                    total_risk_score
                ),

                "risk_level": (
                    calculate_risk_level(
                        total_risk_score
                    )
                ),

                "total_alerts": len(
                    current_alerts
                ),

                "call_alerts": (
                    category_counts[
                        "call_fraud"
                    ]
                ),

                "sms_alerts": (
                    category_counts[
                        "sms_fraud"
                    ]
                ),

                "device_alerts": (
                    category_counts[
                        "device_anomaly"
                    ]
                ),

                "roaming_alerts": (
                    category_counts[
                        "roaming_anomaly"
                    ]
                ),

                "forwarding_alerts": (
                    category_counts[
                        "forwarding_anomaly"
                    ]
                ),
            }
        )

    number_risks.sort(
        key=lambda risk: (
            -risk[
                "total_risk_score"
            ],
            risk[
                "phone_number"
            ],
        )
    )

    severity_counts: dict[
        str,
        int,
    ] = defaultdict(int)

    category_counts: dict[
        str,
        int,
    ] = defaultdict(int)

    for alert in alerts:
        severity_counts[
            alert[
                "severity"
            ]
        ] += 1

        category_counts[
            alert[
                "category"
            ]
        ] += 1

    highest_risk_score = (
        number_risks[0][
            "total_risk_score"
        ]
        if number_risks
        else 0
    )

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,

        "analysed_numbers": len(
            events_by_number
        ),

        "total_alerts": len(
            alerts
        ),

        "low_alerts": (
            severity_counts[
                "low"
            ]
        ),

        "medium_alerts": (
            severity_counts[
                "medium"
            ]
        ),

        "high_alerts": (
            severity_counts[
                "high"
            ]
        ),

        "critical_alerts": (
            severity_counts[
                "critical"
            ]
        ),

        "call_alerts": (
            category_counts[
                "call_fraud"
            ]
        ),

        "sms_alerts": (
            category_counts[
                "sms_fraud"
            ]
        ),

        "device_alerts": (
            category_counts[
                "device_anomaly"
            ]
        ),

        "roaming_alerts": (
            category_counts[
                "roaming_anomaly"
            ]
        ),

        "forwarding_alerts": (
            category_counts[
                "forwarding_anomaly"
            ]
        ),

        "highest_risk_score": (
            highest_risk_score
        ),

        "highest_risk_level": (
            calculate_risk_level(
                highest_risk_score
            )
        ),

        "number_risks": (
            number_risks
        ),

        "alerts": alerts,

        "disclaimer": DISCLAIMER,
    }