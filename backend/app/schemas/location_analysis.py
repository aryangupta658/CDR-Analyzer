

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


# =========================================================
# Tower summary
# =========================================================

class TowerSummaryItem(BaseModel):
    cell_id: str

    first_latitude: float | None
    first_longitude: float | None
    last_latitude: float | None
    last_longitude: float | None

    total_records: int
    unique_number_count: int
    unique_numbers: list[str]

    first_seen: datetime | None
    last_seen: datetime | None


class TowerSummaryResponse(BaseModel):
    case_id: int
    evidence_id: int

    evidence_scope: str

    tower_count: int
    towers: list[TowerSummaryItem]


# =========================================================
# Tower detail
# =========================================================

class TowerNumberUsage(BaseModel):
    phone_number: str

    record_count: int

    first_seen: datetime | None
    last_seen: datetime | None


class TowerEventItem(BaseModel):
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


class TowerDetailResponse(BaseModel):
    case_id: int
    evidence_id: int

    cell_id: str
    lac: str | None

    tower_address: str | None

    latitude: float | None
    longitude: float | None

    total_records: int

    unique_number_count: int
    number_usage: list[TowerNumberUsage]

    first_seen: datetime | None
    last_seen: datetime | None

    events: list[TowerEventItem]


# =========================================================
# Number location history
# =========================================================

class LocationHistoryItem(BaseModel):
    """
    One operator-CDR location record.

    Location, IMEI and IMSI fields belong to TARGET_NO in the
    23-field operator format. They must not be assigned to B_PARTY.
    """

    record_id: int
    evidence_id: int
    source_row: int

    pan_no: str | None

    target_number: str
    call_type: str | None
    connection_type: str | None
    b_party_number: str | None

    start_datetime: datetime
    call_time_raw: str | None
    duration_seconds: int

    first_cell_global_id: str | None
    first_latitude: float | None
    first_longitude: float | None

    last_cell_global_id: str | None
    last_latitude: float | None
    last_longitude: float | None

    imei: str | None
    imsi: str | None

    location_changed: bool


class NumberLocationHistoryResponse(BaseModel):
    case_id: int
    evidence_id: int

    phone_number: str
    evidence_scope: str
    association_basis: str

    total_location_records: int
    unique_tower_count: int
    unique_first_cell_count: int
    unique_last_cell_count: int

    first_seen: datetime | None
    last_seen: datetime | None

    history: list[LocationHistoryItem]


# =========================================================
# Co-location analysis
# =========================================================

class CoLocationRequest(BaseModel):
    target_numbers: list[str] = Field(
        min_length=2,
        max_length=20,
    )

    tolerance_minutes: int = Field(
        default=15,
        ge=0,
        le=1440,
    )

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
    )


class CoLocationNumberEvent(BaseModel):
    phone_number: str

    event_datetime: datetime

    record_id: int
    source_row: int


class CoLocationMatch(BaseModel):
    cell_id: str

    lac: str | None
    tower_address: str | None

    latitude: float | None
    longitude: float | None

    matched_number_count: int
    matched_numbers: list[str]

    window_start: datetime
    window_end: datetime

    events: list[CoLocationNumberEvent]


class CoLocationResponse(BaseModel):
    case_id: int
    evidence_id: int

    evidence_scope: str

    requested_numbers: list[str]
    tolerance_minutes: int

    match_count: int
    matches: list[CoLocationMatch]


# =========================================================
# Incident tower analysis
# =========================================================

class IncidentTowerRequest(BaseModel):
    incident_datetime: datetime

    cell_ids: list[str] = Field(
        min_length=1,
        max_length=50,
    )

    minutes_before: int = Field(
        default=30,
        ge=0,
        le=10080,
    )

    minutes_after: int = Field(
        default=30,
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

    @model_validator(mode="after")
    def clean_cell_ids(self):
        cleaned_cell_ids = []

        for cell_id in self.cell_ids:
            cleaned = cell_id.strip()

            if cleaned and cleaned not in cleaned_cell_ids:
                cleaned_cell_ids.append(cleaned)

        if not cleaned_cell_ids:
            raise ValueError(
                "At least one valid cell ID is required."
            )

        self.cell_ids = cleaned_cell_ids

        return self


class IncidentTowerEvent(BaseModel):
    record_id: int
    evidence_id: int
    source_row: int

    caller_number: str
    receiver_number: str

    start_datetime: datetime

    event_type: str
    direction: str | None

    duration_seconds: int

    cell_id: str
    lac: str | None

    tower_address: str | None

    latitude: float | None
    longitude: float | None

    imei: str | None
    imsi: str | None

    relative_seconds: int
    phase: str


class IncidentTowerResponse(BaseModel):
    case_id: int
    evidence_id: int

    evidence_scope: str

    incident_datetime: datetime
    window_start: datetime
    window_end: datetime

    requested_cell_ids: list[str]
    requested_phone_numbers: list[str] | None

    total_matching_records: int
    returned_record_count: int

    unique_number_count: int
    unique_numbers: list[str]

    events: list[IncidentTowerEvent]