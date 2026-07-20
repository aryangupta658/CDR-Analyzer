from datetime import date, datetime

from pydantic import BaseModel, Field


# =========================================================
# Evidence-level summary
# =========================================================

class CaseSummaryResponse(BaseModel):
    """
    High-level analysis summary for one evidence file
    belonging to one investigation case.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str

    total_records: int

    total_calls: int
    total_sms: int
    total_other_events: int

    outgoing_records: int
    incoming_records: int

    unique_numbers: int
    unique_imeis: int
    unique_imsis: int
    unique_cell_ids: int

    total_duration_seconds: int
    average_duration_seconds: float

    first_activity: datetime | None
    last_activity: datetime | None


# =========================================================
# Number list
# =========================================================

class NumberListItem(BaseModel):
    """
    One phone number found in the selected evidence file.
    """

    phone_number: str

    total_records: int
    outgoing_records: int
    incoming_records: int

    total_duration_seconds: int

    first_activity: datetime | None
    last_activity: datetime | None


class NumberListResponse(BaseModel):
    """
    Paginated list of phone numbers from one evidence file.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str

    total_numbers: int
    offset: int
    limit: int

    numbers: list[NumberListItem]


# =========================================================
# Single-number analysis
# =========================================================

class NumberAnalysisResponse(BaseModel):
    """
    Detailed profile of one phone number inside
    one selected evidence file.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str

    phone_number: str

    total_records: int

    outgoing_records: int
    incoming_records: int

    outgoing_calls: int
    incoming_calls: int

    sms_sent: int
    sms_received: int

    missed_or_zero_duration_calls: int

    unique_contacts: int
    unique_imeis: int
    unique_imsis: int
    unique_cell_ids: int

    imei_values: list[str] = Field(default_factory=list)
    imsi_values: list[str] = Field(default_factory=list)

    total_duration_seconds: int
    average_duration_seconds: float

    first_activity: datetime | None
    last_activity: datetime | None


# =========================================================
# Top contacts
# =========================================================

class TopContactItem(BaseModel):
    """
    Communication summary between the selected number
    and one contact.
    """

    contact_number: str

    total_records: int

    outgoing_records: int
    incoming_records: int

    total_duration_seconds: int
    average_duration_seconds: float

    first_contact: datetime | None
    last_contact: datetime | None


class TopContactsResponse(BaseModel):
    """
    Most frequently contacted numbers inside
    one selected evidence file.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str

    phone_number: str

    contacts: list[TopContactItem]


# =========================================================
# Direct-contact communication timeline
# =========================================================

class ContactTimelineRecord(BaseModel):
    """
    One chronological CDR record exchanged between
    the analysed number and one selected contact.
    """

    record_id: int
    source_row: int | None = None

    start_datetime: datetime | None = None
    end_datetime: datetime | None = None

    direction: str
    event_type: str | None = None

    caller_number: str | None = None
    receiver_number: str | None = None
    duration_seconds: int = 0

    pan_no: str | None = None
    target_number: str | None = None
    call_type: str | None = None
    connection_type: str | None = None
    b_party_number: str | None = None

    lrn_number: str | None = None
    lrn_translation: str | None = None

    first_cell_global_id: str | None = None
    first_latitude: float | None = None
    first_longitude: float | None = None

    last_cell_global_id: str | None = None
    last_latitude: float | None = None
    last_longitude: float | None = None

    sms_centre_number: str | None = None

    imei: str | None = None
    imsi: str | None = None

    call_forwarding_number: str | None = None

    roaming: bool | None = None
    roaming_network_circle: str | None = None

    switch_msc_id: str | None = None
    in_tg: str | None = None
    out_tg: str | None = None


class ContactTimelineResponse(BaseModel):
    """
    Complete chronological communication history between
    one analysed number and one selected direct contact.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str

    phone_number: str
    contact_number: str

    total_records: int
    outgoing_records: int
    incoming_records: int

    first_contact: datetime | None = None
    last_contact: datetime | None = None

    records: list[ContactTimelineRecord]


# =========================================================
# Activity by hour
# =========================================================

class HourlyActivityItem(BaseModel):
    """
    Activity count for one hour of the day.
    """

    hour: int = Field(
        ge=0,
        le=23,
    )

    record_count: int
    total_duration_seconds: int


class CallsByHourResponse(BaseModel):
    """
    Activity grouped by hour for one analysed number.

    phone_number remains optional so older evidence-wide callers continue
    to work, while Number Analysis can show number-specific activity.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str
    phone_number: str | None = None

    activity: list[HourlyActivityItem]


# =========================================================
# Activity by date
# =========================================================

class DailyActivityItem(BaseModel):
    """
    Activity count for one calendar date.
    """

    activity_date: date

    record_count: int
    total_duration_seconds: int


class CallsByDateResponse(BaseModel):
    """
    Activity grouped by date for one analysed number.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str
    phone_number: str | None = None

    activity: list[DailyActivityItem]




class ContactNetworkNode(BaseModel):
    phone_number: str

    is_selected: bool = False

    total_records: int = 0
    outgoing_records: int = 0
    incoming_records: int = 0
    call_records: int = 0
    sms_records: int = 0

    total_duration_seconds: int = 0

    contact_count: int = 0
    weighted_degree: int = 0

    first_activity: datetime | None = None
    last_activity: datetime | None = None

    is_hub: bool = False
    is_bridge: bool = False


class ContactNetworkEdge(BaseModel):
    source: str
    target: str

    total_records: int = 0
    total_calls: int = 0
    total_sms: int = 0
    total_duration_seconds: int = 0

    source_to_target_records: int = 0
    target_to_source_records: int = 0

    first_contact: datetime | None = None
    last_contact: datetime | None = None


class ContactNetworkResponse(BaseModel):
    case_id: int
    evidence_id: int

    selected_number: str
    selected_number_found: bool

    node_count: int
    edge_count: int
    total_records_used: int
    connected_component_count: int

    nodes: list[ContactNetworkNode]
    edges: list[ContactNetworkEdge]