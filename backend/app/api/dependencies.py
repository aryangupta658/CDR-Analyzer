from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.dependencies import get_db
from app.models.user import User


bearer_security = HTTPBearer(
    auto_error=False
)


DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


def get_current_user(
    database: DatabaseSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_security),
    ],
) -> User:
    """
    Reads the Bearer token and returns the currently logged-in user.
    """

    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication token.",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    if credentials is None:
        raise authentication_error

    if credentials.scheme.lower() != "bearer":
        raise authentication_error

    try:
        token_data = decode_access_token(
            credentials.credentials
        )

        user_id = int(
            token_data.get("sub", "")
        )

    except (
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
    ):
        raise authentication_error

    user = database.get(
        User,
        user_id,
    )

    if user is None:
        raise authentication_error

    if not user.is_active:
        raise authentication_error

    return user


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]