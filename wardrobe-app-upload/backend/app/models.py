from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    provider: Mapped[str | None] = mapped_column(String(24), nullable=True)
    provider_openid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    items: Mapped[list["ClothingItem"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("provider", "provider_openid", name="uq_provider_openid"),)


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(24), index=True)
    occasion: Mapped[str] = mapped_column(String(24), index=True)

    image_base64: Mapped[str] = mapped_column(Text)

    color_hex: Mapped[str] = mapped_column(String(8))
    hue: Mapped[float] = mapped_column(Float)
    saturation: Mapped[float] = mapped_column(Float)
    lightness: Mapped[float] = mapped_column(Float)

    fit: Mapped[str] = mapped_column(String(24), default="regular")
    warmth: Mapped[int] = mapped_column(Integer, default=2)
    style_tags: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    owner: Mapped[User] = relationship(back_populates="items")
