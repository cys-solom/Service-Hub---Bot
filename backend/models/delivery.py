"""Delivery rules model"""
from sqlalchemy import String, Text, Boolean, Integer
from models.base import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel


class DeliveryRule(BaseModel):
    __tablename__ = "delivery_rules"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="auto", nullable=False)
    # auto, manual, semi_auto
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Template for delivery message
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
