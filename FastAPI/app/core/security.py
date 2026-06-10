from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def create_access_token(auth_user_id: int, dataset_user_id: str | None) -> str:
    """Create a signed JWT for an authenticated user."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(auth_user_id),
        "dataset_user_id": dataset_user_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
