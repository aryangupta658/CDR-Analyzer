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

from app.schemas.analysis import (
    CallsByDateResponse,
    CallsByHourResponse,
    CaseSummaryResponse,
    ContactNetworkResponse,
    ContactTimelineResponse,
    NumberAnalysisResponse,
    NumberListResponse,
    TopContactsResponse,
)

from app.services.analysis_service import (
    calculate_case_summary,
    get_contact_timeline,
    get_number_analysis,
    get_numbers,
    get_top_contacts,
)
from app.services.graph import build_contact_network
from app.services.number_activity_service import (
    get_calls_by_date,
    get_calls_by_hour,
)


router = APIRouter()


# =========================================================
# Case and evidence validation
# =========================================================

def get_owned_case(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> Case:
    """
    Finds a case and confirms that it belongs
    to the currently authenticated investigator.
    """

    case = database.get(
        Case,
        case_id,
    )

    if case is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Case not found.",
        )

    if case.created_by != current_user.id:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Case not found.",
        )

    return case


def get_imported_evidence(
    case_id: int,
    evidence_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> tuple[Case, EvidenceFile]:
    """
    Confirms that:

    1. The case belongs to the current user.
    2. The evidence exists.
    3. The evidence belongs to the selected case.
    4. The evidence has been imported.
    """

    case = get_owned_case(
        case_id=case_id,
        database=database,
        current_user=current_user,
    )

    evidence = database.get(
        EvidenceFile,
        evidence_id,
    )

    if evidence is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Evidence not found.",
        )

    if evidence.case_id != case_id:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Evidence was not found inside "
                "the selected case."
            ),
        )

    evidence_status = str(
        evidence.status or ""
    ).strip().lower()

    if evidence_status != "imported":
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "The selected evidence has not "
                "been imported."
            ),
        )

    return case, evidence


# =========================================================
# Case/evidence summary
# =========================================================

@router.get(
    "/cases/{case_id}/analysis/summary",
    response_model=CaseSummaryResponse,
)
def read_case_summary(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(
        ...,
        ge=1,
        description=(
            "Imported evidence ID whose CDR "
            "records should be analysed."
        ),
    ),
):
    """
    Returns summary statistics for one imported
    evidence file in one case.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    return calculate_case_summary(
        database,
        case_id,
        evidence_id,
    )


# =========================================================
# Number listing
# =========================================================

@router.get(
    "/cases/{case_id}/analysis/numbers",
    response_model=NumberListResponse,
)
def read_numbers(
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
        max_length=50,
        description=(
            "Optional partial phone-number search."
        ),
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
):
    """
    Returns unique phone numbers appearing in
    caller or receiver fields for the selected
    evidence file.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    cleaned_search = (
        search.strip()
        if search
        else None
    )

    return get_numbers(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        search=cleaned_search,
        offset=offset,
        limit=limit,
    )


# =========================================================
# Hourly activity
# =========================================================

@router.get(
    "/cases/{case_id}/analysis/calls-by-hour",
    response_model=CallsByHourResponse,
)
def read_calls_by_hour(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(
        ...,
        ge=1,
    ),
    phone_number: str | None = Query(
        default=None,
        description=(
            "Optional analysed number. When supplied, only records where "
            "this number is the caller or receiver are included."
        ),
    ),
):
    """
    Groups activity by hour. Number Analysis supplies phone_number so the
    chart describes the analysed number rather than the complete evidence.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    try:
        return get_calls_by_hour(
            database=database,
            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


# =========================================================
# Daily activity
# =========================================================

@router.get(
    "/cases/{case_id}/analysis/calls-by-date",
    response_model=CallsByDateResponse,
)
def read_calls_by_date(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(
        ...,
        ge=1,
    ),
    phone_number: str | None = Query(
        default=None,
        description=(
            "Optional analysed number. When supplied, only records where "
            "this number is the caller or receiver are included."
        ),
    ),
):
    """
    Groups activity by date for the analysed number when supplied.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    try:
        return get_calls_by_date(
            database=database,
            case_id=case_id,
            evidence_id=evidence_id,
            phone_number=phone_number,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


# =========================================================
# Top contacts for one number
# =========================================================

@router.get(
    (
        "/cases/{case_id}/analysis/"
        "numbers/{phone_number}/top-contacts"
    ),
    response_model=TopContactsResponse,
)
def read_top_contacts(
    case_id: int,
    phone_number: str,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(
        ...,
        ge=1,
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
):
    """
    Returns the strongest contacts of one phone
    number within the selected evidence file.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    cleaned_phone_number = (
        phone_number.strip()
    )

    if not cleaned_phone_number:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Phone number is required.",
        )

    return get_top_contacts(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=cleaned_phone_number,
        limit=limit,
    )


# =========================================================
# Direct-contact communication timeline
# =========================================================

@router.get(
    (
        "/cases/{case_id}/analysis/"
        "numbers/{phone_number}/contacts/"
        "{contact_number}/timeline"
    ),
    response_model=ContactTimelineResponse,
)
def read_contact_timeline(
    case_id: int,
    phone_number: str,
    contact_number: str,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(
        ...,
        ge=1,
    ),
):
    """
    Returns every direct CDR record exchanged between the
    selected number and one clicked top contact.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    cleaned_phone_number = phone_number.strip()
    cleaned_contact_number = contact_number.strip()

    if not cleaned_phone_number:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Phone number is required.",
        )

    if not cleaned_contact_number:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Contact number is required.",
        )

    result = get_contact_timeline(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=cleaned_phone_number,
        contact_number=cleaned_contact_number,
    )

    if result is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "No direct communication records were "
                "found between these two numbers in the "
                "selected evidence file."
            ),
        )

    return result


# =========================================================
# Full-evidence communication graph
# =========================================================

@router.get(
    (
        "/cases/{case_id}/analysis/"
        "numbers/{phone_number}/network"
    ),
    response_model=ContactNetworkResponse,
)
def read_contact_network(
    case_id: int,
    phone_number: str,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(
        ...,
        ge=1,
        description=(
            "Imported evidence file used to build the complete "
            "communication graph."
        ),
    ),
):
    """
    Returns a complete graph built from every valid caller/receiver pair in
    the selected CDR evidence.

    The phone number in the URL is highlighted in the graph, but it does not
    limit which records or relationships are returned. No relationship-depth
    or Level 1/2/3 rule is applied.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    cleaned_phone_number = phone_number.strip()

    if not cleaned_phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected phone number is required.",
        )

    try:
        return build_contact_network(
            database=database,
            case_id=case_id,
            evidence_id=evidence_id,
            selected_number=cleaned_phone_number,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


# =========================================================
# Complete profile for one number
# =========================================================

@router.get(
    (
        "/cases/{case_id}/analysis/"
        "numbers/{phone_number}"
    ),
    response_model=NumberAnalysisResponse,
)
def read_number_analysis(
    case_id: int,
    phone_number: str,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(
        ...,
        ge=1,
    ),
):
    """
    Returns the complete selected-evidence
    profile of one phone number.
    """

    get_imported_evidence(
        case_id=case_id,
        evidence_id=evidence_id,
        database=database,
        current_user=current_user,
    )

    cleaned_phone_number = (
        phone_number.strip()
    )

    if not cleaned_phone_number:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail="Phone number is required.",
        )

    result = get_number_analysis(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=cleaned_phone_number,
    )

 

    return result