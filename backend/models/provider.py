"""External provider models — API integrations"""
import uuid
from sqlalchemy import String, Text, Boolean, Float, Integer, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel


class ExternalProvider(BaseModel):
    __tablename__ = "external_providers"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    api_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_secret: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Rate limiting, headers, auth method, etc.
    last_sync_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProviderProduct(BaseModel):
    __tablename__ = "provider_products"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("external_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_code: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    cost_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("products.id"), nullable=True
    )
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ProviderOrder(BaseModel):
    __tablename__ = "provider_orders"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("external_providers.id"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("orders.id"), nullable=False
    )
    external_order_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    response_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
