"""Reseller API Key model — API keys for external resellers with wallet"""
import uuid
import secrets
from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey, BigInteger
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel


class ResellerKey(BaseModel):
    __tablename__ = "reseller_keys"

    # Key info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # Permissions: ["products.read", "purchase", "balance.read", "orders.read"]
    permissions: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Wallet
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_deposited: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Rate limiting
    rate_limit: Mapped[int] = mapped_column(Integer, default=60, nullable=False)  # requests per minute
    ip_whitelist: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated IPs

    # Contact info
    contact: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @staticmethod
    def generate_key():
        return f"sk_live_{secrets.token_hex(24)}"


class ResellerTransaction(BaseModel):
    __tablename__ = "reseller_transactions"

    reseller_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("reseller_keys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # deposit, purchase, refund
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_before: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Purchase details
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType(), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # delivered items (for logs)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
