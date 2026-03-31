from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AuthUserDatasetLink(Base):
    __tablename__ = "auth_user_dataset_links"

    auth_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("auth_users.id"),
        primary_key=True,
    )
    dataset_user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.user_id"),
        nullable=False,
        unique=True,
        index=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
