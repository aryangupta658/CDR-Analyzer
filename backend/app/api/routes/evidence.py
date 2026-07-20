from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
)
from app.core.cdr_columns import (
    detect_operator_22_field_format,
)
from app.models.case import Case
from app.models.evidence import EvidenceFile
from app.schemas.evidence import (
    EvidenceResponse,
    EvidenceUploadResponse,
    ImportRequest,
    ImportResponse,
)
from app.services.cdr_import_service import (
    create_dataframe_preview,
    import_cdr_records,
    import_operator_cdr_file,
    read_cdr_dataframe,
)
from app.services.file_service import (
    save_uploaded_file,
    validate_uploaded_file,
)
from app.services.hash_service import (
    calculate_sha256,
)


router = APIRouter()


# =========================================================
# Ownership helpers
# =========================================================

def get_case_owned_by_current_user(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> Case:
    """
    Returns a case only when it belongs to the
    currently logged-in investigator.
    """

    case = database.get(
        Case,
        case_id,
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    if case.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    return case


def get_evidence_owned_by_current_user(
    evidence_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> EvidenceFile:
    """
    Returns evidence only when its case belongs
    to the logged-in investigator.
    """

    evidence_query = (
        select(EvidenceFile)
        .join(
            Case,
            EvidenceFile.case_id == Case.id,
        )
        .where(
            EvidenceFile.id == evidence_id,
            Case.created_by == current_user.id,
        )
    )

    evidence = database.scalar(
        evidence_query
    )

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    return evidence


# =========================================================
# Evidence path and format helpers
# =========================================================

def get_stored_evidence_path(
    evidence: EvidenceFile,
) -> Path:
    """
    Returns the stored evidence path and verifies
    that the uploaded file exists.
    """

    stored_path_value = getattr(
        evidence,
        "stored_path",
        None,
    )

    if not stored_path_value:
        raise ValueError(
            "The evidence file does not have "
            "a valid stored path."
        )

    stored_path = Path(
        str(stored_path_value)
    )

    if not stored_path.exists():
        raise FileNotFoundError(
            "The uploaded evidence file could "
            f"not be found at: {stored_path}"
        )

    return stored_path


def is_operator_22_field_evidence(
    evidence: EvidenceFile,
) -> bool:
    """
    Detects whether an uploaded file uses the
    supported operator-style 22-field CDR format.
    """

    stored_path = get_stored_evidence_path(
        evidence
    )

    dataframe = read_cdr_dataframe(
        stored_path
    )

    if dataframe.empty:
        raise ValueError(
            "The uploaded CDR file is empty."
        )

    return detect_operator_22_field_format(
        list(dataframe.columns)
    )


def convert_operator_errors(
    rejected_rows: list[dict[str, Any]],
) -> list[str]:
    """
    Converts structured rejected-row errors into
    the list of strings expected by ImportResponse.
    """

    messages: list[str] = []

    for rejected_row in rejected_rows:
        source_row = rejected_row.get(
            "source_row",
            "Unknown",
        )

        errors = rejected_row.get(
            "errors",
            [],
        )

        if isinstance(errors, list):
            error_text = "; ".join(
                str(error)
                for error in errors
            )
        else:
            error_text = str(errors)

        messages.append(
            f"Row {source_row}: {error_text}"
        )

    return messages


# =========================================================
# Upload evidence
# =========================================================

@router.post(
    "/cases/{case_id}/evidence/upload",
    response_model=EvidenceUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_evidence(
    case_id: int,

    file: Annotated[
        UploadFile,
        File(
            description=(
                "Upload a CSV, XLS or XLSX CDR file."
            )
        ),
    ],

    database: DatabaseSession,
    current_user: CurrentUser,
):
    """
    Uploads an original CDR evidence file.

    Steps:

    1. Verify case ownership.
    2. Validate the uploaded file.
    3. Save the original file.
    4. Calculate SHA-256.
    5. Read columns and preview rows.
    6. Save evidence metadata.
    """

    get_case_owned_by_current_user(
        case_id,
        database,
        current_user,
    )

    extension = validate_uploaded_file(
        file
    )

    # Positional arguments are required by your
    # current save_uploaded_file function.
    stored_path = save_uploaded_file(
        file,
        case_id,
        extension,
    )

    try:
        file_size = (
            stored_path.stat().st_size
        )

        sha256_hash = calculate_sha256(
            stored_path
        )

        (
            columns,
            preview_rows,
            total_rows,
        ) = create_dataframe_preview(
            stored_path
        )

    except Exception as error:
        stored_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Could not read the uploaded "
                f"CDR file: {error}"
            ),
        ) from error

    original_filename = Path(
        file.filename or "evidence"
    ).name

    evidence = EvidenceFile(
        case_id=case_id,
        uploaded_by=current_user.id,

        original_filename=original_filename,
        stored_filename=stored_path.name,
        stored_path=str(
            stored_path.resolve()
        ),

        extension=extension,
        mime_type=file.content_type,
        file_size=file_size,
        sha256_hash=sha256_hash,

        status="uploaded",
        record_count=0,
    )

    try:
        database.add(
            evidence
        )

        database.commit()

        database.refresh(
            evidence
        )

    except Exception as error:
        database.rollback()

        stored_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Could not save evidence metadata: "
                f"{error}"
            ),
        ) from error

    return EvidenceUploadResponse(
        evidence=evidence,
        columns=columns,
        preview=preview_rows,
        total_rows_detected=total_rows,
    )


# =========================================================
# List case evidence
# =========================================================

@router.get(
    "/cases/{case_id}/evidence",
    response_model=list[EvidenceResponse],
)
def list_case_evidence(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
):
    """
    Returns evidence files belonging to one case.
    """

    get_case_owned_by_current_user(
        case_id,
        database,
        current_user,
    )

    evidence_query = (
        select(EvidenceFile)
        .where(
            EvidenceFile.case_id == case_id
        )
        .order_by(
            EvidenceFile.uploaded_at.desc()
        )
    )

    evidence_files = database.scalars(
        evidence_query
    ).all()

    return list(
        evidence_files
    )


# =========================================================
# Import evidence
# =========================================================

@router.post(
    "/evidence/{evidence_id}/import",
    response_model=ImportResponse,
)
def import_evidence(
    evidence_id: int,
    request: ImportRequest,
    database: DatabaseSession,
    current_user: CurrentUser,
):
    """
    Imports and normalizes an uploaded CDR file.

    Operator-style 22-field files are detected
    automatically.

    Other supported files continue to use the existing
    manual column-mapping importer.
    """

    evidence = get_evidence_owned_by_current_user(
        evidence_id,
        database,
        current_user,
    )

    evidence_status = str(
        evidence.status or ""
    ).strip().lower()

    if evidence_status == "imported":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This evidence has already been "
                "imported. Upload the file again as "
                "new evidence to import it again."
            ),
        )

    try:
        operator_format = (
            is_operator_22_field_evidence(
                evidence
            )
        )

        if operator_format:
            operator_result = (
                import_operator_cdr_file(
                    database=database,
                    case_id=evidence.case_id,
                    evidence_id=evidence.id,
                    replace_existing=False,
                )
            )

            imported_records = int(
                operator_result.get(
                    "imported_records",
                    0,
                )
            )

            skipped_records = int(
                operator_result.get(
                    "rejected_records",
                    0,
                )
            )

            error_messages = (
                convert_operator_errors(
                    operator_result.get(
                        "rejected_rows",
                        [],
                    )
                )
            )

        else:
            # Positional arguments are safer because
            # your current service may use different
            # parameter names.
            (
                imported_records,
                skipped_records,
                error_messages,
            ) = import_cdr_records(
                database,
                evidence,
                request,
            )

    except FileNotFoundError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ValueError as error:
        database.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        database.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Evidence import failed: "
                f"{error}"
            ),
        ) from error

    return ImportResponse(
        evidence_id=evidence.id,
        imported_records=imported_records,
        skipped_records=skipped_records,
        errors=error_messages,
    )