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
from app.schemas.location_analysis import (
    CoLocationRequest,
    CoLocationResponse,
    IncidentTowerRequest,
    IncidentTowerResponse,
    NumberLocationHistoryResponse,
    TowerDetailResponse,
    TowerSummaryResponse,
)
from app.services.location_analysis_service import (
    calculate_co_location,
    calculate_incident_tower_analysis,
    calculate_number_location_history,
    calculate_tower_detail,
    calculate_tower_summary,
)


router = APIRouter()


# =========================================================
# Ownership validation
# =========================================================

def get_owned_case(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> Case:
    case = database.get(
        Case,
        case_id,
    )

    if (
        case is None
        or case.created_by != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    return case


def get_imported_evidence(
    case_id: int,
    evidence_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> EvidenceFile:
    get_owned_case(
        case_id,
        database,
        current_user,
    )

    evidence = database.get(
        EvidenceFile,
        evidence_id,
    )

    if (
        evidence is None
        or evidence.case_id != case_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Evidence was not found in "
                "the selected case."
            ),
        )

    if evidence.status != "imported":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The selected evidence has not "
                "been imported."
            ),
        )

    return evidence


# =========================================================
# Tower summary
# =========================================================

@router.get(
    "/cases/{case_id}/locations/towers",
    response_model=TowerSummaryResponse,
)
def get_tower_summary(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
    ),

    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):
    get_imported_evidence(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    return calculate_tower_summary(
        database,
        case_id,
        evidence_id,
        search,
        limit,
    )


# =========================================================
# Tower detail
# =========================================================

@router.get(
    "/cases/{case_id}/locations/towers/{cell_id}",
    response_model=TowerDetailResponse,
)
def get_tower_detail(
    case_id: int,
    cell_id: str,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
    ),

    event_limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):
    get_imported_evidence(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    result = calculate_tower_detail(
        database,
        case_id,
        evidence_id,
        cell_id,
        event_limit,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Cell tower was not found in "
                "the selected evidence."
            ),
        )

    return result


# =========================================================
# Number location history
# =========================================================

@router.get(
    "/cases/{case_id}/locations/"
    "numbers/{phone_number}/history",
    response_model=NumberLocationHistoryResponse,
)
def get_number_location_history(
    case_id: int,
    phone_number: str,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
    ),

    limit: int = Query(
        default=1000,
        ge=1,
        le=5000,
    ),
):
    get_imported_evidence(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    result = calculate_number_location_history(
        database,
        case_id,
        evidence_id,
        phone_number,
        limit,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No tower history was found for "
                "this number in the selected evidence."
            ),
        )

    return result


# =========================================================
# Co-location analysis
# =========================================================

@router.post(
    "/cases/{case_id}/locations/co-location",
    response_model=CoLocationResponse,
)
def get_co_location_analysis(
    case_id: int,
    request: CoLocationRequest,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
    ),
):
    get_imported_evidence(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    try:
        return calculate_co_location(
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
# Incident tower analysis
# =========================================================

@router.post(
    "/cases/{case_id}/locations/incident-tower",
    response_model=IncidentTowerResponse,
)
def get_incident_tower_analysis(
    case_id: int,
    request: IncidentTowerRequest,
    database: DatabaseSession,
    current_user: CurrentUser,

    evidence_id: int = Query(
        ...,
        ge=1,
    ),
):
    get_imported_evidence(
        case_id,
        evidence_id,
        database,
        current_user,
    )

    return calculate_incident_tower_analysis(
        database,
        case_id,
        evidence_id,
        request,
    )