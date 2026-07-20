from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """
    Data required to register an investigator.
    """

    full_name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    """
    Data required for login.
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    Response returned after successful login.
    """

    access_token: str
    token_type: str = "bearer"