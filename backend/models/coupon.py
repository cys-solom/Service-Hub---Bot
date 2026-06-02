"""Coupon model"""
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime
from models.base import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel
from datetime import datetime


class Coupon(BaseModel):
    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="percent", nullable=False)
    # percent, fixed
    value: Mapped[float] = mapped_column(Float, nullable=False)
    min_order: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_discount: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = unlimited
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Restrict to specific products/categories
    applies_to: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
