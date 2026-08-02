"""Password hashing and signed session-token helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings, get_settings

ACCESS_TOKEN_COOKIE = "access_token"
_PASSWORD_HASHER = PasswordHasher()
# A real Argon2 hash keeps the unknown-user login path comparable to a bad password.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$jt9233aEgd6uBauKwyhqNQ$"
    "yX6cM78yLr9bwJcW6Nh6hQ8DpYGq16LxIckqZnMY86M"
)


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verify a password while doing Argon2 work even when the account is absent."""
    candidate_hash = password_hash or _DUMMY_PASSWORD_HASH
    try:
        return _PASSWORD_HASHER.verify(candidate_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # A malformed legacy hash is treated exactly like a wrong password.
        return False


def create_access_token(subject: UUID, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> UUID:
    settings = settings or get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
    try:
        return UUID(str(payload["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("invalid subject") from exc
