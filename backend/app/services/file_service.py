from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


ALLOWED_EXTENSIONS = {
    ".csv",
    ".xlsx",
}


ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


def validate_uploaded_file(
    uploaded_file: UploadFile,
) -> str:
    """
    Validates filename extension and MIME type.

    Returns the validated lowercase extension.
    """

    original_filename = Path(
        uploaded_file.filename or ""
    ).name

    extension = Path(
        original_filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Only CSV and XLSX files are supported "
                "in Phase 1A."
            ),
        )

    if (
        uploaded_file.content_type
        and uploaded_file.content_type
        not in ALLOWED_MIME_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported MIME type: "
                f"{uploaded_file.content_type}"
            ),
        )

    return extension


def save_uploaded_file(
    uploaded_file: UploadFile,
    case_id: int,
    extension: str,
) -> Path:
    """
    Saves the original uploaded evidence using a random filename.

    The original evidence is not modified.
    """

    case_storage_directory = (
        settings.storage_directory
        / "originals"
        / f"case_{case_id}"
    )

    case_storage_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    random_filename = (
        f"{uuid4().hex}{extension}"
    )

    destination_path = (
        case_storage_directory
        / random_filename
    )

    maximum_bytes = (
        settings.max_upload_size_mb
        * 1024
        * 1024
    )

    total_written_bytes = 0

    try:
        with destination_path.open("xb") as output_file:
            while True:
                chunk = uploaded_file.file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_written_bytes += len(
                    chunk
                )

                if total_written_bytes > maximum_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            "Maximum upload size is "
                            f"{settings.max_upload_size_mb} MB."
                        ),
                    )

                output_file.write(
                    chunk
                )

    except Exception:
        destination_path.unlink(
            missing_ok=True
        )

        raise

    finally:
        uploaded_file.file.close()

    if total_written_bytes == 0:
        destination_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    return destination_path