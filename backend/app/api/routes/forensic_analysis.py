from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
)
from app.models.case import Case
from app.models.evidence import EvidenceFile
from app.schemas.forensic_analysis import (
    CommonContactsRequest,
    CommonContactsResponse,
    CommonDevicesResponse,
    DeviceHistoryResponse,
    IMEIAnalysisResponse,
    IMSIAnalysisResponse,
    IncidentWindowRequest,
    IncidentWindowResponse,
)
from app.services.forensic_analysis_service import (
    calculate_common_contacts,
    calculate_common_devices,
    calculate_device_history,
    calculate_imei_analysis,
    calculate_imsi_analysis,
    calculate_incident_window,
)


router = APIRouter()


# =========================================================
# Ownership helper functions
# =========================================================

def get_owned_case(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> Case:
    """
    Returns a case only when it belongs to
    the currently authenticated investigator.
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


def get_evidence_belonging_to_case(
    case_id: int,
    evidence_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> EvidenceFile:
    """
    Checks that:

    1. The case belongs to the logged-in user.
    2. The evidence exists.
    3. The evidence belongs to the selected case.
    """

    get_owned_case(
        case_id,
        database,
        current_user,
    )

    evidence = database.get(
        EvidenceFile,
        evidence_id,
    )

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found.",
        )

    if evidence.case_id != case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Evidence does not belong to "
                "the selected case."
            ),
        )

    if evidence.status != "imported":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The selected evidence has not been "
                "successfully imported."
            ),
        )

    return evidence


# =========================================================
# Common-contact analysis
# =========================================================

@router.post(
    "/cases/{case_id}/forensics/common-contacts",
    response_model=CommonContactsResponse,
)
def get_common_contacts(
    case_id: int,
    request: CommonContactsRequest,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
        description=(
            "Evidence file whose records should be analysed."
        ),
    ),
):
    """
    Finds third-party contacts shared by selected targets
    inside one evidence file.
    """

    get_evidence_belonging_to_case(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    try:
        return calculate_common_contacts(
            database,
            case_id,
            evidence_id,
            request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


# =========================================================
# IMEI analysis
# =========================================================

@router.get(
    "/cases/{case_id}/forensics/imei/{imei}",
    response_model=IMEIAnalysisResponse,
)
def get_imei_analysis(
    case_id: int,
    imei: str,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
        description=(
            "Evidence file whose IMEI records "
            "should be analysed."
        ),
    ),
):
    """
    Returns IMEI analysis for one evidence file.
    """

    get_evidence_belonging_to_case(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    result = calculate_imei_analysis(
        database,
        case_id,
        evidence_id,
        imei,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "IMEI was not found in the "
                "selected evidence file."
            ),
        )

    return result


# =========================================================
# IMSI analysis
# =========================================================

@router.get(
    "/cases/{case_id}/forensics/imsi/{imsi}",
    response_model=IMSIAnalysisResponse,
)
def get_imsi_analysis(
    case_id: int,
    imsi: str,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
        description=(
            "Evidence file whose IMSI records "
            "should be analysed."
        ),
    ),
):
    """
    Returns IMSI analysis for one evidence file.
    """

    get_evidence_belonging_to_case(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    result = calculate_imsi_analysis(
        database,
        case_id,
        evidence_id,
        imsi,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "IMSI was not found in the "
                "selected evidence file."
            ),
        )

    return result


# =========================================================
# Device-change history
# =========================================================

@router.get(
    "/cases/{case_id}/forensics/"
    "numbers/{phone_number}/device-history",
    response_model=DeviceHistoryResponse,
)
def get_device_history(
    case_id: int,
    phone_number: str,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
        description=(
            "Evidence file whose device records "
            "should be analysed."
        ),
    ),
):
    """
    Lists IMEIs used by one caller number inside
    one selected evidence file.
    """

    get_evidence_belonging_to_case(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    result = calculate_device_history(
        database,
        case_id,
        evidence_id,
        phone_number,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No device records were found for "
                "this number in the selected evidence."
            ),
        )

    return result


# =========================================================
# Common-device detection
# =========================================================

@router.get(
    "/cases/{case_id}/forensics/common-devices",
    response_model=CommonDevicesResponse,
)
def get_common_devices(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
        description=(
            "Evidence file whose records "
            "should be analysed."
        ),
    ),

    minimum_numbers: int = Query(
        default=2,
        ge=2,
        le=100,
        description=(
            "Minimum unique caller numbers associated "
            "with one IMEI."
        ),
    ),

    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    """
    Finds IMEIs associated with multiple numbers
    inside one evidence file.
    """

    get_evidence_belonging_to_case(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    return calculate_common_devices(
        database,
        case_id,
        evidence_id,
        minimum_numbers,
        limit,
    )


# =========================================================
# Incident-window analysis
# =========================================================

@router.post(
    "/cases/{case_id}/forensics/incident-window",
    response_model=IncidentWindowResponse,
)
def get_incident_window(
    case_id: int,
    request: IncidentWindowRequest,
    database: DatabaseSession,
    current_user: CurrentUser,
):
    """
    Finds records around an incident timestamp inside
    one selected evidence file.
    """

    get_evidence_belonging_to_case(
        case_id,
        request.evidence_id,
        database,
        current_user,
    )

    return calculate_incident_window(
        database,
        case_id,
        request,
    )