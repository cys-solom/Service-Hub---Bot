"""Payment models — crypto + extensible methods"""
import uuid
from sqlalchemy import String, Text, Float, Boolean, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class PaymentMethod(BaseModel):
    __tablename__ = "payment_methods"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # usdt_trc20, usdt_bep20, btc, eth, sol, binance_pay, wallet
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wallet_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    min_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_amount: Mapped[float] = mapped_column(Float, default=99999.0, nullable=False)
    fee_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fee_fixed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructions_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class Payment(BaseModel):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("orders.id"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=False
    )
    method_code: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    # pending, confirming, confirmed, failed, expired, refunded
    tx_hash: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tx_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_type: Mapped[str] = mapped_column(
        String(50), default="note", nullable=False
    )
    # note, api, manual
    expires_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    order = relationship("Order", back_populates="payment")
