from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
)
from app.models.case import Case
from app.schemas.case import (
    CaseCreate,
    CaseResponse,
)


router = APIRouter()


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    request: CaseCreate,
    database: DatabaseSession,
    current_user: CurrentUser,
):
    """
    Creates a new forensic case for the current investigator.
    """

    normalized_case_number = request.case_number.strip()

    existing_case_query = select(Case).where(
        Case.case_number == normalized_case_number
    )

    existing_case = database.scalar(
        existing_case_query
    )

    if existing_case:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A case with this case number already exists.",
        )

    new_case = Case(
        case_number=normalized_case_number,
        title=request.title.strip(),
        description=request.description,
        status="new",
        created_by=current_user.id,
    )

    database.add(new_case)
    database.commit()
    database.refresh(new_case)

    return new_case


@router.get(
    "",
    response_model=list[CaseResponse],
)
def list_cases(
    database: DatabaseSession,
    current_user: CurrentUser,
):
    """
    Returns cases created by the logged-in investigator.
    """

    cases_query = (
        select(Case)
        .where(
            Case.created_by == current_user.id
        )
        .order_by(
            Case.created_at.desc()
        )
    )

    cases = database.scalars(
        cases_query
    ).all()

    return list(cases)


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
)
def get_case(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
):
    """
    Returns one case only when it belongs to the current user.
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