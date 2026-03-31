from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    useful: Mapped[int] = mapped_column(Integer, default=0)
    funny: Mapped[int] = mapped_column(Integer, default=0)
    cool: Mapped[int] = mapped_column(Integer, default=0)

    preferred_star_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_star_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    address: Mapped[str] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(10), nullable=True, index=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)

    categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    friends: Mapped[str | None] = mapped_column(Text, nullable=True)

    age: Mapped[int] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=True)