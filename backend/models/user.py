"""User model — Telegram users"""
from sqlalchemy import BigInteger, String, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referral_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    referred_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_orders: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    orders = relationship("Order", back_populates="user", lazy="selectin")
    wallet = relationship("Wallet", back_populates="user", uselist=False, lazy="selectin")
    support_tickets = relationship("SupportTicket", back_populates="user", lazy="selectin")
