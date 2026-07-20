import re


OPERATOR_CDR_COLUMNS = {
    "pan_no": "PAN_NO",
    "target_number": "TARGET_NO",
    "call_type": "CALL_TYPE",
    "service_type": "TOC",
    "b_party_number": "B_PARTY",
    "lrn_number": "LRN_NO",
    "lrn_translation": "LRN_TSP",
    "call_time": "CALL_TIME",
    "duration": "DURATION",
    "first_cell_global_id": "FIRST_CGI",
    "first_latitude": "FIRST_LAT",
    "first_longitude": "FIRST_LON",
    "last_cell_global_id": "LAST_CGI",
    "last_latitude": "LAST_LAT",
    "last_longitude": "LAST_LON",
    "sms_centre_number": "SMSC_NO",
    "imei_esn": "IMEI",
    "imsi_min": "IMSI",
    "call_forwarding_number": "CALL_FWD",
    "roaming_network_circle": "ROAM_NO",
    "switch_msc_id": "SW4MSCID",
    "in_tg": "IN_TG",
    "out_tg": "OUT_TG",
}


def normalize_header(value: object) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


COLUMN_ALIASES = {
    "pan_no": {
        "pan no",
        "pan number",
        "pan",
        "record no",
        "record number",
        "serial no",
        "serial number",
    },
    "target_number": {
        "target no",
        "target number",
        "target a party number",
        "a party number",
        "a party no",
        "target",
    },
    "call_type": {
        "call type",
        "call type in out",
        "direction",
        "call direction",
    },
    "service_type": {
        "toc",
        "type of communication",
        "communication type",
        "service type",
        "event type",
        "voice sms",
    },
    "connection_type": {
        "type of connection",
        "connection type",
        "prepaid postpaid",
    },
    "b_party_number": {
        "b party",
        "b party no",
        "b party number",
        "b party mobile no",
        "other party number",
        "called number",
    },
    "lrn_number": {
        "lrn no",
        "lrn number",
        "lrn",
        "lrn a b party number",
    },
    "lrn_translation": {
        "lrn tsp",
        "lrn tsp lsa",
        "translation of lrn",
        "translation of lrn tsp lsa",
        "lrn translation",
        "tsp lsa",
    },
    "call_date": {
        "call date",
        "event date",
        "date",
    },
    "call_time": {
        "call time",
        "call datetime",
        "call date time",
        "call initiation time cit",
        "call initiation time",
        "event datetime",
        "event time",
        "cit",
        "time",
    },
    "duration": {
        "duration",
        "call duration",
        "call duration seconds",
        "duration seconds",
        "dur",
        "dur s",
    },
    "first_bts_location": {
        "first bts location",
        "first bts",
        "first cell location",
        "first location",
    },
    "first_cell_global_id": {
        "first cgi",
        "first cell global id",
        "first cell global id mcc mnc lac site id",
        "first cell id",
        "first cell",
    },
    "first_latitude": {
        "first lat",
        "first latitude",
        "first cell latitude",
    },
    "first_longitude": {
        "first lon",
        "first long",
        "first longitude",
        "first cell longitude",
    },
    "last_bts_location": {
        "last bts location",
        "last bts",
        "last cell location",
        "last location",
    },
    "last_cell_global_id": {
        "last cgi",
        "last cell global id",
        "last cell id",
        "last cell",
    },
    "last_latitude": {
        "last lat",
        "last latitude",
        "last cell latitude",
    },
    "last_longitude": {
        "last lon",
        "last long",
        "last longitude",
        "last cell longitude",
    },
    "sms_centre_number": {
        "smsc no",
        "smsc number",
        "smsc",
        "sms centre number",
        "sms center number",
        "sms centre no",
        "sms center no",
    },
    "imei_esn": {
        "imei",
        "imei esn",
        "esn",
    },
    "imsi_min": {
        "imsi",
        "imsi min",
        "min",
    },
    "call_forwarding_number": {
        "call fwd",
        "call fwr",
        "call forward no",
        "call forwarding no",
        "call forwarding number",
        "forwarding number",
        "forwarded number",
    },
    "roaming_network_circle": {
        "roam no",
        "roam",
        "roaming status",
        "roaming network circle",
        "roaming network",
        "roaming circle",
        "roaming nw",
        "circle",
    },
    "switch_msc_id": {
        "sw4mscid",
        "sw4mscd",
        "sw4msc",
        "switch msc id",
        "switch id msc id",
        "switch id",
        "msc id",
        "sw id",
    },
    "in_tg": {
        "in tg",
        "incoming trunk group",
        "originating ioi",
    },
    "out_tg": {
        "out tg",
        "outgoing trunk group",
        "terminating ioi",
    },
}


def resolve_operator_columns(incoming_headers: list[object]) -> dict[str, str]:
    normalized_incoming = {
        normalize_header(header): str(header)
        for header in incoming_headers
        if str(header or "").strip()
    }

    resolved: dict[str, str] = {}

    for internal_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            normalized_alias = normalize_header(alias)
            if normalized_alias in normalized_incoming:
                resolved[internal_name] = normalized_incoming[normalized_alias]
                break

    return resolved


def detect_operator_22_field_format(incoming_headers: list[object]) -> bool:
    """
    Kept under the old function name because the current evidence route imports
    it. It now recognises both the previous operator format and the actual
    23-field format containing PAN_NO and first/last coordinates.
    """
    resolved = resolve_operator_columns(incoming_headers)

    required_fields = {
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

    return required_fields.issubset(resolved.keys())
