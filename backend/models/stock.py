"""Stock models — inventory management"""
import uuid
from sqlalchemy import String, Text, Boolean, ForeignKey, Integer
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class StockType(BaseModel):
    __tablename__ = "stock_types"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Structure definition: ["email", "password", "2fa_code"]
    fields: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    separator: Mapped[str] = mapped_column(String(10), default=":", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StockItem(BaseModel):
    __tablename__ = "stock_items"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # The actual stock data (email:pass, code, etc.)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured data as JSON for complex stock types
    data_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_sold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_reserved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reserved_until: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reserved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=True
    )
    sold_to: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("orders.id"), nullable=True
    )
    batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="stock_items")
