from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PatternScope = Literal[
    "short_window",
    "full_evidence",
    "incident",
]


class PatternAnalysisRequest(BaseModel):
    phone_number: str | None = Field(
        default=None,
        description=(
            "Optional phone number. Leave empty to analyse every phone number "
            "present inside the selected evidence file."
        ),
    )
    incident_datetime: datetime | None = Field(
        default=None,
        description=(
            "Optional incident date and time. Incident comparison rules are "
            "applied only when this value is supplied."
        ),
    )
    incident_cell_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Optional CGI or cell IDs associated with the incident. They are "
            "used only when incident rules are enabled."
        ),
    )
    include_call_patterns: bool = True
    include_sms_patterns: bool = True
    include_device_patterns: bool = True
    include_location_patterns: bool = True
    include_roaming_patterns: bool = True
    include_forwarding_patterns: bool = True


class PatternItemResponse(BaseModel):
    pattern_id: str
    rule_code: str
    title: str
    category: str
    scope: PatternScope
    phone_number: str

    observed_value: int | float | str
    comparison_value: int | float | str | None = None

    window_start: datetime | None = None
    window_end: datetime | None = None

    description: str
    explanation: str

    related_numbers: list[str] = Field(default_factory=list)
    imeis: list[str] = Field(default_factory=list)
    imsis: list[str] = Field(default_factory=list)
    cell_ids: list[str] = Field(default_factory=list)
    source_record_ids: list[int] = Field(default_factory=list)


class NumberPatternSummaryResponse(BaseModel):
    phone_number: str
    total_patterns: int
    short_window_patterns: int
    full_evidence_patterns: int
    incident_patterns: int
    call_patterns: int
    sms_patterns: int
    device_patterns: int
    contact_patterns: int
    location_patterns: int
    roaming_patterns: int
    forwarding_patterns: int


class PatternSummaryResponse(BaseModel):
    case_id: int
    evidence_id: int
    analysed_numbers: int

    evidence_start: datetime | None = None
    evidence_end: datetime | None = None
    evidence_days: int

    incident_datetime: datetime | None = None
    incident_cell_ids: list[str] = Field(default_factory=list)
    incident_rules_applied: bool

    total_patterns: int
    short_window_patterns: int
    full_evidence_patterns: int
    incident_patterns: int

    call_patterns: int
    sms_patterns: int
    device_patterns: int
    contact_patterns: int
    location_patterns: int
    roaming_patterns: int
    forwarding_patterns: int

    number_summaries: list[NumberPatternSummaryResponse]
    patterns: list[PatternItemResponse]
    disclaimer: str