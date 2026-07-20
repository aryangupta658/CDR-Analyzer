from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class EvidenceResponse(BaseModel):
    """
    Evidence metadata returned by the API.
    """

    id: int
    case_id: int
    original_filename: str
    extension: str
    mime_type: str | None
    file_size: int
    sha256_hash: str
    status: str
    record_count: int
    uploaded_at: datetime
    imported_at: datetime | None

    model_config = ConfigDict(
        from_attributes=True
    )


class EvidenceUploadResponse(BaseModel):
    """
    Response after evidence upload.

    It contains:
    - Evidence metadata
    - File columns
    - First rows
    - Total detected rows
    """

    evidence: EvidenceResponse
    columns: list[str]
    preview: list[dict[str, Any]]
    total_rows_detected: int


class ColumnMapping(BaseModel):
    """
    Maps uploaded provider columns to standard database fields.

    The value of each property is the actual column name
    in the uploaded CSV or XLSX file.
    """

    caller_number: str
    receiver_number: str

    start_datetime: str | None = None

    event_date: str | None = None
    event_time: str | None = None

    end_datetime: str | None = None

    duration_seconds: str | None = None
    event_type: str | None = None
    direction: str | None = None

    imei: str | None = None
    imsi: str | None = None

    cell_id: str | None = None
    lac: str | None = None

    latitude: str | None = None
    longitude: str | None = None

    tower_address: str | None = None
    service_provider: str | None = None
    roaming: str | None = None

    @model_validator(mode="after")
    def validate_start_datetime_fields(self):
        """
        The file must have either:

        1. One complete start_datetime column

        OR

        2. An event_date column, optionally with event_time.
        """

        if not self.start_datetime and not self.event_date:
            raise ValueError(
                "Provide either start_datetime or event_date."
            )

        return self


class ImportRequest(BaseModel):
    """
    Request for importing and normalizing evidence.
    """

    mapping: ColumnMapping

    day_first: bool = True

    replace_existing: bool = False


class ImportResponse(BaseModel):
    """
    Result returned after import.
    """

    evidence_id: int
    imported_records: int
    skipped_records: int

    errors: list[str] = Field(
        default_factory=list
    )