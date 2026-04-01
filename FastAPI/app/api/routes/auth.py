import hashlib
import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database.session import SessionLocal
from app.models.auth_user import AuthUser
from app.models.auth_user_dataset_link import AuthUserDatasetLink
from app.models.auth_user_preference import AuthUserPreference
from app.models.review import Review
from app.models.user import User


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LinkDatasetUserRequest(BaseModel):
    auth_user_id: int = Field(gt=0)
    dataset_user_id: str = Field(min_length=1, max_length=32)


class PreferencesRequest(BaseModel):
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_categories: str | None = Field(default=None, max_length=1000)
    preferred_star_min: float | None = Field(default=None, ge=0, le=5)
    preferred_star_max: float | None = Field(default=None, ge=0, le=5)
    use_friends_boost: bool = True


class UpdateNameRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class AddFriendRequest(BaseModel):
    friend_user_id: str = Field(min_length=1, max_length=32)


def parse_friends(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []

    return [friend_id.strip() for friend_id in raw_value.split(",") if friend_id.strip()]


def serialize_friends(friend_ids: list[str]) -> str:
    return ", ".join(friend_ids)


def normalize_category_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    normalized = [cat.strip() for cat in raw.split(",") if cat.strip()]
    unique: list[str] = []
    for cat in normalized:
        if cat not in unique:
            unique.append(cat)
        if len(unique) >= 20:
            break
    return unique


def serialize_categories(categories: list[str] | None) -> str | None:
    if not categories:
        return None

    return ", ".join(categories)


def get_auth_and_dataset_user(session, auth_user_id: int):
    auth_user = session.query(AuthUser).filter(AuthUser.id == auth_user_id).first()
    if not auth_user:
        raise HTTPException(status_code=404, detail="Utilizador autenticado nao encontrado.")

    link = (
        session.query(AuthUserDatasetLink)
        .filter(AuthUserDatasetLink.auth_user_id == auth_user_id)
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=400,
            detail="Utilizador sem dataset_user_id associado.",
        )

    dataset_user = session.query(User).filter(User.user_id == link.dataset_user_id).first()
    if not dataset_user:
        raise HTTPException(status_code=404, detail="user_id do dataset nao encontrado.")

    return auth_user, link, dataset_user


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return candidate == expected


@router.post("/register")
def register(payload: RegisterRequest):
    session = SessionLocal()
    try:
        normalized_email = payload.email.strip().lower()
        if "@" not in normalized_email or "." not in normalized_email:
            raise HTTPException(status_code=400, detail="Email invalido.")

        existing = (
            session.query(AuthUser)
            .filter(AuthUser.email == normalized_email)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Email ja registado.")

        new_user = AuthUser(
            name=payload.name.strip(),
            email=normalized_email,
            password_hash=hash_password(payload.password),
        )

        session.add(new_user)
        session.flush()

        # Create a dataset user for the new account and link it automatically.
        dataset_user_id = None
        for _ in range(5):
            candidate = f"app_{uuid4().hex[:20]}"
            exists = session.query(User).filter(User.user_id == candidate).first()
            if not exists:
                dataset_user_id = candidate
                break

        if not dataset_user_id:
            raise HTTPException(status_code=500, detail="Nao foi possivel gerar user_id do dataset.")

        dataset_user = User(
            user_id=dataset_user_id,
            name=payload.name.strip(),
            friends="",
        )
        session.add(dataset_user)
        session.flush()

        session.add(
            AuthUserDatasetLink(
                auth_user_id=new_user.id,
                dataset_user_id=dataset_user_id,
            )
        )

        session.commit()
        session.refresh(new_user)

        return {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "dataset_user_id": dataset_user_id,
            "message": "Conta criada com sucesso.",
        }
    finally:
        session.close()


@router.post("/login")
def login(payload: LoginRequest):
    session = SessionLocal()
    try:
        normalized_email = payload.email.strip().lower()
        auth_user = (
            session.query(AuthUser)
            .filter(AuthUser.email == normalized_email)
            .first()
        )

        if not auth_user or not verify_password(payload.password, auth_user.password_hash):
            raise HTTPException(status_code=401, detail="Credenciais invalidas.")

        dataset_link = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.auth_user_id == auth_user.id)
            .first()
        )

        return {
            "id": auth_user.id,
            "name": auth_user.name,
            "email": auth_user.email,
            "dataset_user_id": dataset_link.dataset_user_id if dataset_link else None,
            "message": "Login efetuado com sucesso.",
        }
    finally:
        session.close()


@router.post("/link-dataset-user")
def link_dataset_user(payload: LinkDatasetUserRequest):
    session = SessionLocal()
    try:
        auth_user = session.query(AuthUser).filter(AuthUser.id == payload.auth_user_id).first()
        if not auth_user:
            raise HTTPException(status_code=404, detail="Utilizador autenticado nao encontrado.")

        dataset_user = (
            session.query(User)
            .filter(User.user_id == payload.dataset_user_id)
            .first()
        )
        if not dataset_user:
            raise HTTPException(status_code=404, detail="user_id do dataset nao encontrado.")

        existing_for_dataset = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.dataset_user_id == payload.dataset_user_id)
            .first()
        )
        if existing_for_dataset and existing_for_dataset.auth_user_id != payload.auth_user_id:
            raise HTTPException(
                status_code=409,
                detail="Esse user_id do dataset ja esta associado a outra conta.",
            )

        existing_for_auth = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.auth_user_id == payload.auth_user_id)
            .first()
        )
        if existing_for_auth:
            existing_for_auth.dataset_user_id = payload.dataset_user_id
        else:
            session.add(
                AuthUserDatasetLink(
                    auth_user_id=payload.auth_user_id,
                    dataset_user_id=payload.dataset_user_id,
                )
            )

        session.commit()

        return {
            "auth_user_id": payload.auth_user_id,
            "dataset_user_id": payload.dataset_user_id,
            "message": "Associacao criada com sucesso.",
        }
    finally:
        session.close()


@router.get("/{auth_user_id}/dataset-link")
def get_dataset_link(auth_user_id: int):
    session = SessionLocal()
    try:
        link = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.auth_user_id == auth_user_id)
            .first()
        )
        if not link:
            return {
                "auth_user_id": auth_user_id,
                "dataset_user_id": None,
                "linked": False,
            }

        return {
            "auth_user_id": auth_user_id,
            "dataset_user_id": link.dataset_user_id,
            "linked": True,
        }
    finally:
        session.close()


@router.get("/{auth_user_id}/preferences")
def get_preferences(auth_user_id: int):
    session = SessionLocal()
    try:
        auth_user = session.query(AuthUser).filter(AuthUser.id == auth_user_id).first()
        if not auth_user:
            raise HTTPException(status_code=404, detail="Utilizador autenticado nao encontrado.")

        prefs = (
            session.query(AuthUserPreference)
            .filter(AuthUserPreference.auth_user_id == auth_user_id)
            .first()
        )

        if not prefs:
            return {
                "auth_user_id": auth_user_id,
                "preferred_city": None,
                "preferred_categories": None,
                "preferred_star_min": None,
                "preferred_star_max": None,
                "use_friends_boost": True,
            }

        return {
            "auth_user_id": auth_user_id,
            "preferred_city": prefs.preferred_city,
            "preferred_categories": prefs.preferred_categories,
            "preferred_star_min": prefs.preferred_star_min,
            "preferred_star_max": prefs.preferred_star_max,
            "use_friends_boost": prefs.use_friends_boost,
        }
    finally:
        session.close()


@router.put("/{auth_user_id}/preferences")
def update_preferences(auth_user_id: int, payload: PreferencesRequest):
    session = SessionLocal()
    try:
        auth_user = session.query(AuthUser).filter(AuthUser.id == auth_user_id).first()
        if not auth_user:
            raise HTTPException(status_code=404, detail="Utilizador autenticado nao encontrado.")

        if (
            payload.preferred_star_min is not None
            and payload.preferred_star_max is not None
            and payload.preferred_star_min > payload.preferred_star_max
        ):
            raise HTTPException(
                status_code=400,
                detail="preferred_star_min nao pode ser maior que preferred_star_max.",
            )

        prefs = (
            session.query(AuthUserPreference)
            .filter(AuthUserPreference.auth_user_id == auth_user_id)
            .first()
        )

        normalized_city = payload.preferred_city.strip() if payload.preferred_city else None
        normalized_categories = serialize_categories(
            normalize_category_list(payload.preferred_categories)
        )

        if not prefs:
            prefs = AuthUserPreference(
                auth_user_id=auth_user_id,
                preferred_city=normalized_city,
                preferred_categories=normalized_categories,
                preferred_star_min=payload.preferred_star_min,
                preferred_star_max=payload.preferred_star_max,
                use_friends_boost=payload.use_friends_boost,
            )
            session.add(prefs)
        else:
            prefs.preferred_city = normalized_city
            prefs.preferred_categories = normalized_categories
            prefs.preferred_star_min = payload.preferred_star_min
            prefs.preferred_star_max = payload.preferred_star_max
            prefs.use_friends_boost = payload.use_friends_boost

        session.commit()

        return {
            "auth_user_id": auth_user_id,
            "preferred_city": prefs.preferred_city,
            "preferred_categories": prefs.preferred_categories,
            "preferred_star_min": prefs.preferred_star_min,
            "preferred_star_max": prefs.preferred_star_max,
            "use_friends_boost": prefs.use_friends_boost,
            "message": "Preferencias atualizadas com sucesso.",
        }
    finally:
        session.close()


@router.get("/{auth_user_id}/social-profile")
def get_social_profile(auth_user_id: int):
    session = SessionLocal()
    try:
        auth_user = session.query(AuthUser).filter(AuthUser.id == auth_user_id).first()
        if not auth_user:
            raise HTTPException(status_code=404, detail="Utilizador autenticado nao encontrado.")

        link = (
            session.query(AuthUserDatasetLink)
            .filter(AuthUserDatasetLink.auth_user_id == auth_user_id)
            .first()
        )

        if not link:
            return {
                "auth_user_id": auth_user_id,
                "auth_name": auth_user.name,
                "dataset_user_id": None,
                "dataset_name": None,
                "reviews_count": 0,
                "friends": [],
                "message": "Sem user_id do dataset associado.",
            }

        dataset_user = session.query(User).filter(User.user_id == link.dataset_user_id).first()
        if not dataset_user:
            raise HTTPException(status_code=404, detail="user_id do dataset nao encontrado.")

        reviews_count = session.query(Review).filter(Review.user_id == dataset_user.user_id).count()
        friend_ids = parse_friends(dataset_user.friends)

        friends = []
        if friend_ids:
            friend_rows = session.query(User).filter(User.user_id.in_(friend_ids)).all()
            friend_name_map = {row.user_id: row.name for row in friend_rows}

            for friend_id in friend_ids:
                friends.append(
                    {
                        "user_id": friend_id,
                        "name": friend_name_map.get(friend_id),
                    }
                )

        return {
            "auth_user_id": auth_user_id,
            "auth_name": auth_user.name,
            "dataset_user_id": dataset_user.user_id,
            "dataset_name": dataset_user.name,
            "reviews_count": reviews_count,
            "friends": friends,
        }
    finally:
        session.close()


@router.put("/{auth_user_id}/name")
def update_auth_name(auth_user_id: int, payload: UpdateNameRequest):
    session = SessionLocal()
    try:
        auth_user = session.query(AuthUser).filter(AuthUser.id == auth_user_id).first()
        if not auth_user:
            raise HTTPException(status_code=404, detail="Utilizador autenticado nao encontrado.")

        auth_user.name = payload.name.strip()
        session.commit()

        return {
            "auth_user_id": auth_user_id,
            "name": auth_user.name,
            "message": "Nome atualizado com sucesso.",
        }
    finally:
        session.close()


@router.post("/{auth_user_id}/friends")
def add_friend(auth_user_id: int, payload: AddFriendRequest):
    session = SessionLocal()
    try:
        _, _, dataset_user = get_auth_and_dataset_user(session, auth_user_id)

        friend = session.query(User).filter(User.user_id == payload.friend_user_id).first()
        if not friend:
            raise HTTPException(status_code=404, detail="Amigo nao encontrado no dataset.")

        friend_ids = parse_friends(dataset_user.friends)
        if payload.friend_user_id in friend_ids:
            raise HTTPException(status_code=409, detail="Esse amigo ja esta na lista.")

        friend_ids.append(payload.friend_user_id)
        dataset_user.friends = serialize_friends(friend_ids)
        session.commit()

        return {
            "auth_user_id": auth_user_id,
            "dataset_user_id": dataset_user.user_id,
            "friends_count": len(friend_ids),
            "message": "Amigo adicionado com sucesso.",
        }
    finally:
        session.close()


@router.delete("/{auth_user_id}/friends/{friend_user_id}")
def remove_friend(auth_user_id: int, friend_user_id: str):
    session = SessionLocal()
    try:
        _, _, dataset_user = get_auth_and_dataset_user(session, auth_user_id)

        friend_ids = parse_friends(dataset_user.friends)
        if friend_user_id not in friend_ids:
            raise HTTPException(status_code=404, detail="Amigo nao existe na lista.")

        friend_ids = [item for item in friend_ids if item != friend_user_id]
        dataset_user.friends = serialize_friends(friend_ids)
        session.commit()

        return {
            "auth_user_id": auth_user_id,
            "dataset_user_id": dataset_user.user_id,
            "friends_count": len(friend_ids),
            "message": "Amigo removido com sucesso.",
        }
    finally:
        session.close()
