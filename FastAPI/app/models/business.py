from sqlalchemy import String, Integer, Float, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class Business(Base):
    __tablename__ = "businesses"

    business_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    address: Mapped[str] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(10), nullable=True, index=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)

    stars: Mapped[float] = mapped_column(Float, nullable=True, index=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)

    is_open: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)

    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)