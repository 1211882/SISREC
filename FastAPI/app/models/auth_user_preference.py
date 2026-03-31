from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AuthUserPreference(Base):
    __tablename__ = "auth_user_preferences"

    auth_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("auth_users.id"),
        primary_key=True,
    )
    preferred_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_categories: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    preferred_star_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_star_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    use_friends_boost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
