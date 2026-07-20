from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FraudSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class FraudAnalysisRequest(BaseModel):
    """
    Options sent by the frontend when fraud analysis runs.
    """

    phone_number: str | None = Field(
        default=None,
        description=(
            "Optional target number. Leave empty to analyse "
            "all target numbers in the selected evidence."
        ),
    )

    include_call_rules: bool = True
    include_sms_rules: bool = True
    include_device_rules: bool = True
    include_roaming_rules: bool = True
    include_forwarding_rules: bool = True


class FraudAlertResponse(BaseModel):
    alert_id: str

    rule_code: str
    rule_name: str
    category: str
    severity: FraudSeverity
    risk_points: int

    case_id: int
    evidence_id: int
    phone_number: str

    window_start: datetime | None = None
    window_end: datetime | None = None

    observed_value: int | float | str
    threshold_value: int | float | str

    description: str
    explanation: str

    related_numbers: list[str] = Field(
        default_factory=list
    )

    imeis: list[str] = Field(
        default_factory=list
    )

    imsis: list[str] = Field(
        default_factory=list
    )

    cell_ids: list[str] = Field(
        default_factory=list
    )

    source_record_ids: list[int] = Field(
        default_factory=list
    )


class FraudNumberRiskResponse(BaseModel):
    phone_number: str

    total_risk_score: int
    risk_level: FraudSeverity

    total_alerts: int

    call_alerts: int
    sms_alerts: int
    device_alerts: int
    roaming_alerts: int
    forwarding_alerts: int


class FraudSummaryResponse(BaseModel):
    case_id: int
    evidence_id: int

    analysed_numbers: int
    total_alerts: int

    low_alerts: int
    medium_alerts: int
    high_alerts: int
    critical_alerts: int

    call_alerts: int
    sms_alerts: int
    device_alerts: int
    roaming_alerts: int
    forwarding_alerts: int

    highest_risk_score: int
    highest_risk_level: FraudSeverity

    number_risks: list[
        FraudNumberRiskResponse
    ]

    alerts: list[
        FraudAlertResponse
    ]

    disclaimer: str