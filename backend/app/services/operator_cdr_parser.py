import math
import re
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.core.cdr_columns import detect_operator_22_field_format, resolve_operator_columns


EMPTY_VALUES = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "nan",
    "-",
    "--",
    "not available",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            value = int(value)

    text = str(value).strip()
    if text.lower() in EMPTY_VALUES:
        return None

    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]

    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?[eE][+-]?\d+", text):
        try:
            text = format(float(text), ".0f")
        except ValueError:
            pass

    return text


def clean_phone_number(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None

    has_plus = text.startswith("+")
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None

    return f"+{digits}" if has_plus else digits


def clean_identifier(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return re.sub(r"\s+", "", text)


def normalize_direction(value: Any) -> str:
    text = (clean_text(value) or "").strip().lower()
    compact = re.sub(r"[^a-z0-9]+", "", text)

    outgoing_values = {
        "out",
        "outgoing",
        "mo",
        "mobileoriginated",
        "originating",
        "orig",
        "o",
        "smsmo",
        "smso",
    }
    incoming_values = {
        "in",
        "incoming",
        "mt",
        "mobileterminated",
        "terminating",
        "term",
        "i",
        "smsmt",
        "smsi",
    }

    if compact in outgoing_values or compact.endswith("mo"):
        return "outgoing"
    if compact in incoming_values or compact.endswith("mt"):
        return "incoming"
    if text.startswith("out"):
        return "outgoing"
    if text.startswith("in"):
        return "incoming"
    return "unknown"


def normalize_event_type(service_value: Any, call_type_value: Any = None) -> str:
    service_text = (clean_text(service_value) or "").strip().lower()
    call_type_text = (clean_text(call_type_value) or "").strip().lower()
    combined = f"{service_text} {call_type_text}"

    if "sms" in combined:
        return "sms"
    if "mms" in combined:
        return "mms"
    if "voice" in combined or "call" in combined or call_type_text in {"mo", "mt"}:
        return "call"
    if "data" in combined:
        return "data"
    return service_text or "other"


def parse_datetime_value(value: Any, day_first: bool = True) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().replace(tzinfo=None)
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    text = clean_text(value)
    if not text:
        return None

    iso_like = bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", text))
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=False if iso_like else day_first)
    if pd.isna(parsed):
        return None

    result = parsed.to_pydatetime()
    if result.tzinfo is not None:
        result = result.replace(tzinfo=None)
    return result


def combine_date_and_time(date_value: Any, time_value: Any) -> datetime | None:
    if date_value is None or clean_text(date_value) is None:
        return parse_datetime_value(time_value, day_first=True)

    date_text = clean_text(date_value)
    time_text = clean_text(time_value)
    if not date_text:
        return parse_datetime_value(time_value, day_first=True)
    if not time_text:
        return parse_datetime_value(date_value, day_first=True)

    return parse_datetime_value(f"{date_text} {time_text}", day_first=True)


def parse_duration(value: Any) -> int:
    text = clean_text(value)
    if not text:
        return 0
    try:
        return max(0, int(float(text)))
    except (TypeError, ValueError):
        return 0


def parse_float(value: Any) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        result = float(text)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def parse_cell_global_id(value: Any) -> dict[str, str | None]:
    text = clean_text(value)
    result = {"full_value": text, "mcc": None, "mnc": None, "lac": None, "site_id": None}
    if not text:
        return result

    parts = [part.strip() for part in re.split(r"[/|,;]+", text) if part.strip()]
    if len(parts) < 4:
        parts = [part.strip() for part in re.split(r"\s+", text) if part.strip()]

    if len(parts) >= 4:
        result["mcc"] = parts[0]
        result["mnc"] = parts[1]
        result["lac"] = parts[2]
        result["site_id"] = "/".join(parts[3:])

    return result


def extract_provider(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return re.split(r"[-/|]", text, maxsplit=1)[0].strip()


def detect_roaming(value: Any) -> bool:
    text = (clean_text(value) or "").strip().lower()
    return text in {"roam", "roaming", "yes", "y", "true", "1"} or "roam" in text


def get_mapped_value(row: pd.Series, mapping: dict[str, str], internal_field: str) -> Any:
    source_column = mapping.get(internal_field)
    if not source_column:
        return None
    return row.get(source_column)


def parse_operator_cdr_row(
    row: pd.Series,
    mapping: dict[str, str],
    case_id: int,
    evidence_id: int,
    source_row: int,
) -> dict[str, Any]:
    pan_no = clean_identifier(get_mapped_value(row, mapping, "pan_no"))
    target_number = clean_phone_number(get_mapped_value(row, mapping, "target_number"))
    b_party_number = clean_phone_number(get_mapped_value(row, mapping, "b_party_number"))

    call_type_raw = clean_text(get_mapped_value(row, mapping, "call_type"))
    service_type_raw = clean_text(get_mapped_value(row, mapping, "service_type"))
    direction = normalize_direction(call_type_raw)
    event_type = normalize_event_type(service_type_raw, call_type_raw)

    call_date_value = get_mapped_value(row, mapping, "call_date")
    call_time_value = get_mapped_value(row, mapping, "call_time")
    start_datetime = combine_date_and_time(call_date_value, call_time_value)

    duration_seconds = parse_duration(get_mapped_value(row, mapping, "duration"))
    end_datetime = (
        start_datetime + timedelta(seconds=duration_seconds)
        if start_datetime is not None
        else None
    )

    if direction == "incoming":
        caller_number = b_party_number
        receiver_number = target_number
    else:
        caller_number = target_number
        receiver_number = b_party_number

    first_cell_value = clean_text(get_mapped_value(row, mapping, "first_cell_global_id"))
    last_cell_value = clean_text(get_mapped_value(row, mapping, "last_cell_global_id"))
    first_cell_parts = parse_cell_global_id(first_cell_value)

    first_latitude = parse_float(get_mapped_value(row, mapping, "first_latitude"))
    first_longitude = parse_float(get_mapped_value(row, mapping, "first_longitude"))
    last_latitude = parse_float(get_mapped_value(row, mapping, "last_latitude"))
    last_longitude = parse_float(get_mapped_value(row, mapping, "last_longitude"))

    imei_value = clean_identifier(get_mapped_value(row, mapping, "imei_esn"))
    imsi_value = clean_identifier(get_mapped_value(row, mapping, "imsi_min"))
    lrn_tsp = clean_text(get_mapped_value(row, mapping, "lrn_translation"))
    roaming_value = clean_text(get_mapped_value(row, mapping, "roaming_network_circle"))
    first_bts_location = clean_text(get_mapped_value(row, mapping, "first_bts_location"))
    last_bts_location = clean_text(get_mapped_value(row, mapping, "last_bts_location"))

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "source_row": source_row,

        "caller_number": caller_number,
        "receiver_number": receiver_number,
        "event_type": event_type,
        "direction": direction,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "duration_seconds": duration_seconds,
        "imei": imei_value,
        "imsi": imsi_value,
        "cell_id": first_cell_value,
        "lac": first_cell_parts["lac"],
        "latitude": first_latitude,
        "longitude": first_longitude,
        "tower_address": first_bts_location,
        "service_provider": extract_provider(lrn_tsp),
        "roaming": detect_roaming(roaming_value),

        "pan_no": pan_no,
        "target_number": target_number,
        "call_type": call_type_raw,
        "connection_type": clean_text(get_mapped_value(row, mapping, "connection_type")),
        "b_party_number": b_party_number,
        "lrn_number": clean_identifier(get_mapped_value(row, mapping, "lrn_number")),
        "lrn_translation": lrn_tsp,
        "call_date_raw": clean_text(call_date_value),
        "call_time_raw": clean_text(call_time_value),
        "first_bts_location": first_bts_location,
        "first_cell_global_id": first_cell_value,
        "first_latitude": first_latitude,
        "first_longitude": first_longitude,
        "last_bts_location": last_bts_location,
        "last_cell_global_id": last_cell_value,
        "last_latitude": last_latitude,
        "last_longitude": last_longitude,
        "sms_centre_number": clean_identifier(
            get_mapped_value(row, mapping, "sms_centre_number")
        ),
        "service_type": service_type_raw,
        "imei_esn": imei_value,
        "imsi_min": imsi_value,
        "call_forwarding_number": clean_phone_number(
            get_mapped_value(row, mapping, "call_forwarding_number")
        ),
        "roaming_network_circle": roaming_value,
        "switch_msc_id": clean_text(get_mapped_value(row, mapping, "switch_msc_id")),
        "in_tg": clean_text(get_mapped_value(row, mapping, "in_tg")),
        "out_tg": clean_text(get_mapped_value(row, mapping, "out_tg")),
    }


def validate_operator_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not record["target_number"]:
        errors.append("Target number is missing.")
    if not record["b_party_number"]:
        errors.append("B-party number is missing.")
    if record["direction"] == "unknown":
        errors.append("CALL_TYPE must be MO, MT, SMS-MO or SMS-MT.")
    if record["start_datetime"] is None:
        errors.append("CALL_TIME is missing or invalid.")
    if record["event_type"] not in {"call", "sms", "mms", "data", "other"}:
        errors.append("TOC/type of communication is invalid.")
    return errors


def parse_operator_dataframe(
    dataframe: pd.DataFrame,
    case_id: int,
    evidence_id: int,
) -> dict[str, Any]:
    headers = list(dataframe.columns)
    if not detect_operator_22_field_format(headers):
        mapping = resolve_operator_columns(headers)
        missing = sorted(
            {
                "target_number",
                "call_type",
                "service_type",
                "b_party_number",
                "call_time",
                "duration",
                "first_cell_global_id",
                "last_cell_global_id",
                "imei_esn",
                "imsi_min",
            }
            - set(mapping)
        )
        raise ValueError(
            "The uploaded file does not match the supported operator CDR format. "
            f"Missing recognised fields: {', '.join(missing)}"
        )

    mapping = resolve_operator_columns(headers)
    valid_records: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    for index, row in dataframe.iterrows():
        source_row = int(index) + 2
        try:
            record = parse_operator_cdr_row(
                row=row,
                mapping=mapping,
                case_id=case_id,
                evidence_id=evidence_id,
                source_row=source_row,
            )
            validation_errors = validate_operator_record(record)
            if validation_errors:
                rejected_rows.append({"source_row": source_row, "errors": validation_errors})
                continue
            valid_records.append(record)
        except (TypeError, ValueError, OverflowError) as error:
            rejected_rows.append({"source_row": source_row, "errors": [str(error)]})

    return {
        "format": "operator_23_field",
        "mapping": mapping,
        "total_rows": len(dataframe),
        "valid_records": valid_records,
        "valid_count": len(valid_records),
        "rejected_rows": rejected_rows,
        "rejected_count": len(rejected_rows),
    }
