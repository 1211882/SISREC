import datetime as dt

import jwt
import pytest

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


def test_token_roundtrip_preserves_identity():
    token = create_access_token(42, "app_abc123")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["dataset_user_id"] == "app_abc123"


def test_token_without_dataset_user():
    token = create_access_token(7, None)
    payload = decode_access_token(token)
    assert payload["sub"] == "7"
    assert payload["dataset_user_id"] is None


def test_tampered_token_is_rejected():
    token = create_access_token(1, "x")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "x")


def test_expired_token_is_rejected():
    expired = jwt.encode(
        {"sub": "1", "exp": dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


def test_token_signed_with_other_key_is_rejected():
    forged = jwt.encode({"sub": "1"}, "a-different-secret", algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(forged)
