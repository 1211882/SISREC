import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.database.session import SessionLocal
from app.models.auth_user import AuthUser
from app.models.auth_user_dataset_link import AuthUserDatasetLink

bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUser:
    """Lightweight holder for the authenticated identity."""

    def __init__(self, auth_user_id: int, name: str, email: str, dataset_user_id: str | None):
        self.id = auth_user_id
        self.name = name
        self.email = email
        self.dataset_user_id = dataset_user_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Resolve the authenticated user from a Bearer JWT.

    Raises 401 when the token is missing, malformed, expired or the user no
    longer exists.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
        auth_user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise invalid

    session = SessionLocal()
    try:
        auth_user = session.query(AuthUser).filter(AuthUser.id == auth_user_id).first()
        if not auth_user:
            raise invalid

        link = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.auth_user_id == auth_user_id)
            .first()
        )
        dataset_user_id = link.dataset_user_id if link else None

        return CurrentUser(
            auth_user_id=auth_user.id,
            name=auth_user.name,
            email=auth_user.email,
            dataset_user_id=dataset_user_id,
        )
    finally:
        session.close()


def ensure_owns_auth_account(current_user: CurrentUser, auth_user_id: int) -> None:
    """Authorize: the caller may only act on their own account."""
    if current_user.id != auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nao tem permissao para aceder a este recurso.",
        )


def ensure_owns_dataset_user(current_user: CurrentUser, dataset_user_id: str) -> None:
    """Authorize: the caller may only act on their own dataset user."""
    if current_user.dataset_user_id != dataset_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nao tem permissao para aceder a este recurso.",
        )
