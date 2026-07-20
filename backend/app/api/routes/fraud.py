from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.case import Case
from app.models.evidence import EvidenceFile
from app.schemas.pattern_analysis import (
    PatternAnalysisRequest,
    PatternSummaryResponse,
)
from app.services.pattern_analysis_service import analyse_patterns


router = APIRouter()


def get_case_owned_by_current_user(
    case_id: int,
    database: DatabaseSession,
    current_user: CurrentUser,
) -> Case:
    case = database.get(Case, case_id)

    if case is None or case.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    return case


def get_imported_evidence(
    case_id: int,
    evidence_id: int,
    database: DatabaseSession,
) -> EvidenceFile:
    evidence = database.scalar(
        select(EvidenceFile).where(
            EvidenceFile.id == evidence_id,
            EvidenceFile.case_id == case_id,
        )
    )

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence was not found inside the selected case.",
        )

    if str(evidence.status or "").strip().lower() != "imported":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence must be imported before pattern analysis can run.",
        )

    return evidence


def parse_incident_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Incident date and time is invalid.",
        ) from error


def parse_incident_cell_ids(value: str | None) -> list[str]:
    if not value:
        return []

    return [
        cell_id.strip()
        for cell_id in value.split(",")
        if cell_id.strip()
    ]


@router.post(
    "/cases/{case_id}/pattern-analysis",
    response_model=PatternSummaryResponse,
)
def run_pattern_analysis(
    case_id: int,
    evidence_id: int,
    request: PatternAnalysisRequest,
    database: DatabaseSession,
    current_user: CurrentUser,
):
    get_case_owned_by_current_user(
        case_id,
        database,
        current_user,
    )
    get_imported_evidence(
        case_id,
        evidence_id,
        database,
    )

    return analyse_patterns(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=request.phone_number,
        incident_datetime=request.incident_datetime,
        incident_cell_ids=request.incident_cell_ids,
        include_call_patterns=request.include_call_patterns,
        include_sms_patterns=request.include_sms_patterns,
        include_device_patterns=request.include_device_patterns,
        include_location_patterns=request.include_location_patterns,
        include_roaming_patterns=request.include_roaming_patterns,
        include_forwarding_patterns=request.include_forwarding_patterns,
    )


@router.get(
    "/cases/{case_id}/analysis/numbers/{phone_number}/patterns",
    response_model=PatternSummaryResponse,
)
def read_number_patterns(
    case_id: int,
    phone_number: str,
    database: DatabaseSession,
    current_user: CurrentUser,
    evidence_id: int = Query(..., ge=1),
    incident_datetime: str | None = Query(default=None),
    incident_cell_ids: str | None = Query(default=None),
):
    get_case_owned_by_current_user(
        case_id,
        database,
        current_user,
    )
    get_imported_evidence(
        case_id,
        evidence_id,
        database,
    )

    return analyse_patterns(
        database=database,
        case_id=case_id,
        evidence_id=evidence_id,
        phone_number=phone_number,
        incident_datetime=parse_incident_datetime(incident_datetime),
        incident_cell_ids=parse_incident_cell_ids(incident_cell_ids),
    )