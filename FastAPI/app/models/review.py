from sqlalchemy import String, Integer, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.user_id"), nullable=False, index=True
    )
    business_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("businesses.business_id"), nullable=False, index=True
    )

    stars: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommend: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    useful: Mapped[int] = mapped_column(Integer, default=0)
    funny: Mapped[int] = mapped_column(Integer, default=0)
    cool: Mapped[int] = mapped_column(Integer, default=0)

    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)
