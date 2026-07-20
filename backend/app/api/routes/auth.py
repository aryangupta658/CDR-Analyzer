from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import (
    CurrentUser,
    DatabaseSession,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse


router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    request: RegisterRequest,
    database: DatabaseSession,
):
    """
    Registers a new investigator account.
    """

    normalized_email = request.email.lower().strip()

    existing_user_query = select(User).where(
        User.email == normalized_email
    )

    existing_user = database.scalar(
        existing_user_query
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = User(
        full_name=request.full_name.strip(),
        email=normalized_email,
        password_hash=hash_password(
            request.password
        ),
        role="investigator",
    )

    database.add(new_user)
    database.commit()
    database.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(
    request: LoginRequest,
    database: DatabaseSession,
):
    """
    Checks email and password and returns a JWT token.
    """

    normalized_email = request.email.lower().strip()

    user_query = select(User).where(
        User.email == normalized_email
    )

    user = database.scalar(
        user_query
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    password_is_correct = verify_password(
        request.password,
        user.password_hash,
    )

    if not password_is_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        additional_data={
            "role": user.role
        },
    )

    return TokenResponse(
        access_token=access_token
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_my_profile(
    current_user: CurrentUser,
):
    """
    Returns the currently authenticated user.
    """

    return current_user