from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    """
    Request data for creating a forensic case.
    """

    case_number: str = Field(
        min_length=2,
        max_length=100,
    )

    title: str = Field(
        min_length=2,
        max_length=200,
    )

    description: str | None = None


class CaseResponse(BaseModel):
    """
    Case data returned by the API.
    """

    id: int
    case_number: str
    title: str
    description: str | None
    status: str
    created_by: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )