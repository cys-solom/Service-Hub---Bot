"""Wallet models — balance, deposit, transactions"""
import uuid
from sqlalchemy import String, Text, Float, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class Wallet(BaseModel):
    __tablename__ = "wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id"), unique=True, nullable=False
    )
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_deposited: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)

    user = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", lazy="selectin")


class WalletTransaction(BaseModel):
    __tablename__ = "wallet_transactions"

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # deposit, purchase, refund, bonus, admin_add, admin_deduct
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_before: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    wallet = relationship("Wallet", back_populates="transactions")
