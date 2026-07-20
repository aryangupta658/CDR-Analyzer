from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# =========================================================
# Common-contact analysis
# =========================================================

class CommonContactsRequest(BaseModel):
    """
    Numbers that should be compared with one another.

    Example:
    ["9876500001", "9876500002", "9876500003"]
    """

    target_numbers: list[str] = Field(
        min_length=2,
        max_length=20,
    )

    minimum_common_targets: int = Field(
        default=2,
        ge=2,
        le=20,
    )

    limit: int = Field(
        default=100,
        ge=1,
        le=500,
    )

    @model_validator(mode="after")
    def validate_minimum_common_targets(self):
        if self.minimum_common_targets > len(self.target_numbers):
            raise ValueError(
                "minimum_common_targets cannot be greater "
                "than the number of target numbers."
            )

        return self


class TargetContactStatistic(BaseModel):
    """
    Relationship between one target number
    and one common contact.
    """

    target_number: str

    record_count: int
    outgoing_records: int
    incoming_records: int

    total_duration_seconds: int

    first_contact: datetime | None
    last_contact: datetime | None


class CommonContactItem(BaseModel):
    """
    A third-party number connected to multiple target numbers.
    """

    contact_number: str

    connected_target_count: int
    connected_target_numbers: list[str]

    total_records: int
    total_duration_seconds: int

    first_contact: datetime | None
    last_contact: datetime | None

    target_statistics: list[TargetContactStatistic]


class CommonContactsResponse(BaseModel):
    case_id: int

    requested_target_numbers: list[str]

    common_contact_count: int
    common_contacts: list[CommonContactItem]


# =========================================================
# Shared identifier usage
# =========================================================

class IdentifierNumberUsage(BaseModel):
    """
    One phone number associated with an IMEI or IMSI
    inside one selected evidence file.
    """

    phone_number: str

    record_count: int

    first_seen: datetime | None
    last_seen: datetime | None


# =========================================================
# IMEI analysis
# =========================================================

class IMEIAnalysisResponse(BaseModel):
    """
    IMEI analysis limited to one evidence file.
    """

    case_id: int
    evidence_id: int

    imei: str

    evidence_scope: str
    association_basis: str

    total_records: int

    associated_number_count: int
    associated_numbers: list[IdentifierNumberUsage]

    related_imsis: list[str]
    related_cell_ids: list[str]

    first_seen: datetime | None
    last_seen: datetime | None


# =========================================================
# IMSI analysis
# =========================================================

class IMSIAnalysisResponse(BaseModel):
    """
    IMSI analysis limited to one evidence file.
    """

    case_id: int
    evidence_id: int

    imsi: str

    evidence_scope: str
    association_basis: str

    total_records: int

    associated_number_count: int
    associated_numbers: list[IdentifierNumberUsage]

    related_imeis: list[str]
    related_cell_ids: list[str]

    first_seen: datetime | None
    last_seen: datetime | None


# =========================================================
# Device-change history
# =========================================================

class DeviceUsageItem(BaseModel):
    """
    One IMEI observed for one phone number.
    """

    imei: str

    record_count: int

    first_seen: datetime
    last_seen: datetime


class DeviceChangeEvent(BaseModel):
    """
    First observed switch from one IMEI to another.
    """

    change_datetime: datetime

    previous_imei: str
    new_imei: str

    evidence_id: int
    source_row: int


class DeviceHistoryResponse(BaseModel):
    """
    Device history for one number inside one evidence file.
    """

    case_id: int
    evidence_id: int
    phone_number: str

    evidence_scope: str
    association_basis: str

    unique_device_count: int
    total_device_records: int

    devices: list[DeviceUsageItem]
    change_events: list[DeviceChangeEvent]


# =========================================================
# Common-device detection
# =========================================================

class CommonDeviceItem(BaseModel):
    """
    One IMEI associated with multiple phone numbers.
    """

    imei: str

    associated_number_count: int
    associated_numbers: list[str]

    total_records: int

    first_seen: datetime | None
    last_seen: datetime | None

    related_imsis: list[str]


class CommonDevicesResponse(BaseModel):
    """
    Common-device results for one selected evidence file.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str
    association_basis: str

    common_device_count: int

    devices: list[CommonDeviceItem]


# =========================================================
# Incident-window analysis
# =========================================================

class IncidentWindowRequest(BaseModel):
    """
    Defines an incident timestamp and time window.

    phone_numbers is optional.

    When it is omitted, every record in the selected
    evidence file and time window is considered.
    """

    evidence_id: int = Field(
        ge=1,
    )

    incident_datetime: datetime

    minutes_before: int = Field(
        default=60,
        ge=0,
        le=10080,
    )

    minutes_after: int = Field(
        default=60,
        ge=0,
        le=10080,
    )

    phone_numbers: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    limit: int = Field(
        default=1000,
        ge=1,
        le=5000,
    )


class IncidentEventItem(BaseModel):
    """
    One communication record found in the incident window.
    """

    record_id: int
    evidence_id: int
    source_row: int

    caller_number: str
    receiver_number: str

    event_type: str
    direction: str | None

    start_datetime: datetime
    duration_seconds: int

    imei: str | None
    imsi: str | None

    cell_id: str | None
    tower_address: str | None

    relative_seconds: int

    phase: Literal[
        "before_incident",
        "at_incident",
        "after_incident",
    ]


class IncidentNumberStatistic(BaseModel):
    """
    Activity summary for one phone number inside
    the incident window.
    """

    phone_number: str

    record_count: int

    before_count: int
    at_incident_count: int
    after_count: int

    first_activity: datetime | None
    last_activity: datetime | None


class IncidentWindowResponse(BaseModel):
    """
    Incident-window response for one selected evidence file.
    """

    case_id: int
    evidence_id: int

    evidence_scope: str

    incident_datetime: datetime

    window_start: datetime
    window_end: datetime

    requested_phone_numbers: list[str] | None

    total_matching_records: int
    returned_record_count: int

    number_statistics: list[IncidentNumberStatistic]

    events: list[IncidentEventItem]