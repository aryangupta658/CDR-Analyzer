from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Converts a plain password into a secure Argon2 hash.
    """

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    stored_password_hash: str,
) -> bool:
    """
    Checks whether a plain password matches the stored hash.
    """

    return password_hasher.verify(
        plain_password,
        stored_password_hash,
    )


def create_access_token(
    subject: str,
    additional_data: dict[str, Any] | None = None,
) -> str:
    """
    Creates a signed JWT access token.
    """

    current_time = datetime.now(timezone.utc)

    expiry_time = current_time + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    token_payload: dict[str, Any] = {
        "sub": subject,
        "iat": current_time,
        "exp": expiry_time,
    }

    if additional_data:
        token_payload.update(additional_data)

    token = jwt.encode(
        token_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Verifies and decodes a JWT token.
    """

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )