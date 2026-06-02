"""Referral model — links, commission, earnings"""
import uuid
from sqlalchemy import String, Float, Integer, ForeignKey
from models.base import UUIDType
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel


class Referral(BaseModel):
    __tablename__ = "referrals"

    referrer_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=False, index=True
    )
    referred_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=False
    )
    commission_percent: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    total_earned: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
