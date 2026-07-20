from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.cdr_record import CDRRecord
from app.models.evidence import EvidenceFile
from app.services.operator_cdr_parser import (
    parse_operator_dataframe,
)

from app.schemas.evidence import (
    ColumnMapping,
    ImportRequest,
)


def create_dataframe_preview(
    file_path: Path,
    row_limit: int = 20,
) -> tuple[
    list[str],
    list[dict[str, Any]],
    int,
]:
    """
    Reads the file and returns:

    - Column names
    - First rows
    - Total row count
    """

    dataframe = read_cdr_dataframe(
        file_path
    )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    preview_dataframe = dataframe.head(
        row_limit
    ).copy()

    preview_rows = (
        preview_dataframe
        .fillna("")
        .to_dict(orient="records")
    )

    columns = list(
        dataframe.columns
    )

    total_rows = len(
        dataframe
    )

    return (
        columns,
        preview_rows,
        total_rows,
    )


def clean_text(
    value: Any,
) -> str | None:
    """
    Converts a value to clean text.

    Blank values and NaN values become None.
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    invalid_values = {
        "",
        "nan",
        "none",
        "null",
        "nat",
    }

    if text.lower() in invalid_values:
        return None

    return text


def clean_phone_or_identifier(
    value: Any,
) -> str | None:
    """
    Cleans phone numbers, IMEI and IMSI values.

    Preserves digits and an optional plus sign.
    """

    text = clean_text(
        value
    )

    if text is None:
        return None

    # Excel sometimes changes a number to 9876500001.0
    if (
        text.endswith(".0")
        and text[:-2].isdigit()
    ):
        text = text[:-2]

    allowed_characters = set(
        "+0123456789"
    )

    cleaned_value = "".join(
        character
        for character in text
        if character in allowed_characters
    )

    return cleaned_value or None


def parse_integer(
    value: Any,
    default: int = 0,
) -> int:
    """
    Safely converts a value into an integer.
    """

    text = clean_text(
        value
    )

    if text is None:
        return default

    try:
        integer_value = int(
            float(text)
        )

        return max(
            0,
            integer_value,
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def parse_float(
    value: Any,
) -> float | None:
    """
    Safely converts a value into a floating-point number.
    """

    text = clean_text(
        value
    )

    if text is None:
        return None

    try:
        return float(
            text
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def parse_datetime_value(
    value: Any,
    day_first: bool,
) -> datetime | None:
    """
    Converts a date/time value into a Python datetime.
    """

    text = clean_text(
        value
    )

    if text is None:
        return None

    parsed_datetime = pd.to_datetime(
        text,
        errors="coerce",
        dayfirst=day_first,
    )

    if pd.isna(
        parsed_datetime
    ):
        return None

    python_datetime = (
        parsed_datetime.to_pydatetime()
    )

    # Store a naive datetime for this first version.
    # Timezone handling will be added later.
    if python_datetime.tzinfo is not None:
        python_datetime = (
            python_datetime.replace(
                tzinfo=None
            )
        )

    return python_datetime


def get_row_value(
    row: pd.Series,
    column_name: str | None,
) -> Any:
    """
    Returns a value from a row using a mapped column name.
    """

    if not column_name:
        return None

    return row.get(
        column_name
    )


def create_start_datetime(
    row: pd.Series,
    mapping: ColumnMapping,
    day_first: bool,
) -> datetime | None:
    """
    Creates start datetime from either:

    - One complete start_datetime column
    - Separate event_date and event_time columns
    """

    if mapping.start_datetime:
        value = get_row_value(
            row,
            mapping.start_datetime,
        )

        return parse_datetime_value(
            value,
            day_first,
        )

    date_text = clean_text(
        get_row_value(
            row,
            mapping.event_date,
        )
    )

    time_text = clean_text(
        get_row_value(
            row,
            mapping.event_time,
        )
    )

    combined_datetime_text = " ".join(
        value
        for value in (
            date_text,
            time_text,
        )
        if value
    )

    return parse_datetime_value(
        combined_datetime_text,
        day_first,
    )


def validate_mapping_columns(
    dataframe: pd.DataFrame,
    mapping: ColumnMapping,
) -> None:
    """
    Checks that every mapped column really exists in the file.
    """

    existing_columns = set(
        dataframe.columns
    )

    mapping_values = (
        mapping.model_dump().values()
    )

    requested_columns = {
        value
        for value in mapping_values
        if value is not None
    }

    missing_columns = sorted(
        requested_columns
        - existing_columns
    )

    if missing_columns:
        raise ValueError(
            "Mapped columns not found in the file: "
            + ", ".join(missing_columns)
        )


def import_cdr_records(
    database: Session,
    evidence: EvidenceFile,
    request: ImportRequest,
) -> tuple[int, int, list[str]]:
    """
    Reads an evidence file, normalizes its records,
    and stores them in cdr_records.
    """

    file_path = Path(
        evidence.stored_path
    )

    dataframe = read_cdr_dataframe(
        file_path
    )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    validate_mapping_columns(
        dataframe,
        request.mapping,
    )

    existing_record_count = (
        database.query(CDRRecord)
        .filter(
            CDRRecord.evidence_id
            == evidence.id
        )
        .count()
    )

    if (
        existing_record_count > 0
        and not request.replace_existing
    ):
        raise ValueError(
            "This evidence has already been imported. "
            "Set replace_existing to true to replace "
            "its normalized records."
        )

    if (
        existing_record_count > 0
        and request.replace_existing
    ):
        database.execute(
            delete(CDRRecord).where(
                CDRRecord.evidence_id
                == evidence.id
            )
        )

    normalized_records: list[CDRRecord] = []

    skipped_record_count = 0

    error_messages: list[str] = []

    for dataframe_index, row in dataframe.iterrows():
        # Spreadsheet row 1 contains headings.
        source_row_number = (
            int(dataframe_index) + 2
        )

        caller_number = clean_phone_or_identifier(
            get_row_value(
                row,
                request.mapping.caller_number,
            )
        )

        receiver_number = clean_phone_or_identifier(
            get_row_value(
                row,
                request.mapping.receiver_number,
            )
        )

        start_datetime = create_start_datetime(
            row,
            request.mapping,
            request.day_first,
        )

        required_data_is_invalid = (
            not caller_number
            or not receiver_number
            or start_datetime is None
        )

        if required_data_is_invalid:
            skipped_record_count += 1

            if len(error_messages) < 20:
                error_messages.append(
                    f"Row {source_row_number}: "
                    "missing or invalid caller, receiver, "
                    "or start datetime."
                )

            continue

        event_type = clean_text(
            get_row_value(
                row,
                request.mapping.event_type,
            )
        )

        if event_type is None:
            event_type = "call"

        normalized_record = CDRRecord(
            case_id=evidence.case_id,
            evidence_id=evidence.id,
            source_row=source_row_number,

            caller_number=caller_number,
            receiver_number=receiver_number,

            event_type=event_type.lower(),

            direction=clean_text(
                get_row_value(
                    row,
                    request.mapping.direction,
                )
            ),

            start_datetime=start_datetime,

            end_datetime=parse_datetime_value(
                get_row_value(
                    row,
                    request.mapping.end_datetime,
                ),
                request.day_first,
            ),

            duration_seconds=parse_integer(
                get_row_value(
                    row,
                    request.mapping.duration_seconds,
                )
            ),

            imei=clean_phone_or_identifier(
                get_row_value(
                    row,
                    request.mapping.imei,
                )
            ),

            imsi=clean_phone_or_identifier(
                get_row_value(
                    row,
                    request.mapping.imsi,
                )
            ),

            cell_id=clean_text(
                get_row_value(
                    row,
                    request.mapping.cell_id,
                )
            ),

            lac=clean_text(
                get_row_value(
                    row,
                    request.mapping.lac,
                )
            ),

            latitude=parse_float(
                get_row_value(
                    row,
                    request.mapping.latitude,
                )
            ),

            longitude=parse_float(
                get_row_value(
                    row,
                    request.mapping.longitude,
                )
            ),

            tower_address=clean_text(
                get_row_value(
                    row,
                    request.mapping.tower_address,
                )
            ),

            service_provider=clean_text(
                get_row_value(
                    row,
                    request.mapping.service_provider,
                )
            ),

            roaming=clean_text(
                get_row_value(
                    row,
                    request.mapping.roaming,
                )
            ),
        )

        normalized_records.append(
            normalized_record
        )

    database.add_all(
        normalized_records
    )

    evidence.status = "imported"

    evidence.record_count = len(
        normalized_records
    )

    evidence.imported_at = datetime.now(
        timezone.utc
    )

    database.commit()

    return (
        len(normalized_records),
        skipped_record_count,
        error_messages,
    )

def read_cdr_dataframe(
    file_path: str | Path,
) -> pd.DataFrame:
    """
    Reads CSV, XLS or XLSX while trying to preserve
    phone numbers, IMEI and IMSI as text.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Evidence file not found: {path}"
        )

    extension = path.suffix.lower()

    if extension == ".csv":
        encodings = [
            "utf-8-sig",
            "utf-8",
            "cp1252",
            "latin-1",
        ]

        last_error: Exception | None = None

        for encoding in encodings:
            try:
                return pd.read_csv(
                    path,
                    dtype=str,
                    keep_default_na=False,
                    encoding=encoding,
                )
            except UnicodeDecodeError as error:
                last_error = error

        raise ValueError(
            "The CSV encoding could not be read."
        ) from last_error

    if extension in {
        ".xlsx",
        ".xls",
    }:
        engine = (
            "openpyxl"
            if extension == ".xlsx"
            else "xlrd"
        )

        return pd.read_excel(
            path,
            dtype=str,
            keep_default_na=False,
            engine=engine,
        )

    raise ValueError(
        "Unsupported CDR file type. "
        "Use CSV, XLS or XLSX."
    )


def get_evidence_file_path(
    evidence: EvidenceFile,
) -> Path:
    """
    Supports common evidence model path field names.
    """

    possible_fields = [
        "stored_path",
        "file_path",
        "storage_path",
        "path",
    ]

    for field_name in possible_fields:
        if not hasattr(
            evidence,
            field_name,
        ):
            continue

        value = getattr(
            evidence,
            field_name,
        )

        if value:
            return Path(
                str(value)
            )

    raise ValueError(
        "The evidence model does not contain "
        "a stored file path."
    )


def update_evidence_import_status(
    evidence: EvidenceFile,
    status_value: str,
    record_count: int | None = None,
) -> None:
    """
    Updates fields only when they exist on the current
    EvidenceFile model.
    """

    if hasattr(
        evidence,
        "status",
    ):
        evidence.status = status_value

    if (
        record_count is not None
        and hasattr(
            evidence,
            "record_count",
        )
    ):
        evidence.record_count = (
            record_count
        )

    if (
        status_value == "imported"
        and hasattr(
            evidence,
            "imported_at",
        )
    ):
        from datetime import datetime

        evidence.imported_at = (
            datetime.now()
        )


def import_operator_cdr_file(
    database: Session,
    case_id: int,
    evidence_id: int,
    replace_existing: bool = False,
) -> dict[str, Any]:
    """
    Imports an operator-style 22-field CDR file.

    The original 22 values are stored while normalized
    values are generated for the current analysis system.
    """

    evidence = database.get(
        EvidenceFile,
        evidence_id,
    )

    if evidence is None:
        raise ValueError(
            "Evidence file not found."
        )

    if evidence.case_id != case_id:
        raise ValueError(
            "Evidence does not belong to "
            "the selected case."
        )

    file_path = get_evidence_file_path(
        evidence
    )

    dataframe = read_cdr_dataframe(
        file_path
    )

    if dataframe.empty:
        raise ValueError(
            "The uploaded CDR file is empty."
        )

    result = parse_operator_dataframe(
        dataframe=dataframe,
        case_id=case_id,
        evidence_id=evidence_id,
    )

    if result["valid_count"] == 0:
        update_evidence_import_status(
            evidence,
            "failed",
            record_count=0,
        )

        database.commit()

        return {
            "case_id": case_id,
            "evidence_id": evidence_id,
            "status": "failed",
            **result,
        }

    try:
        if replace_existing:
            database.execute(
                delete(CDRRecord).where(
                    CDRRecord.case_id
                    == case_id,
                    CDRRecord.evidence_id
                    == evidence_id,
                )
            )

        else:
            existing_record = (
                database.scalars(
                    select(CDRRecord)
                    .where(
                        CDRRecord.case_id
                        == case_id,
                        CDRRecord.evidence_id
                        == evidence_id,
                    )
                    .limit(1)
                ).first()
            )

            if existing_record is not None:
                raise ValueError(
                    "This evidence has already been "
                    "imported. Use replace_existing=True "
                    "to reimport it."
                )

        records = [
            CDRRecord(
                **record_data
            )
            for record_data
            in result["valid_records"]
        ]

        database.add_all(
            records
        )

        update_evidence_import_status(
            evidence,
            "imported",
            record_count=len(records),
        )

        database.commit()

    except Exception:
        database.rollback()

        update_evidence_import_status(
            evidence,
            "failed",
        )

        database.commit()

        raise

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "status": "imported",
        "format": result["format"],
        "total_rows": (
            result["total_rows"]
        ),
        "imported_records": len(
            records
        ),
        "rejected_records": (
            result["rejected_count"]
        ),
        "rejected_rows": (
            result["rejected_rows"][:100]
        ),
        "column_mapping": (
            result["mapping"]
        ),
    }