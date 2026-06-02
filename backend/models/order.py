"""Order models — full lifecycle tracking"""
import uuid
from sqlalchemy import String, Text, Float, Integer, BigInteger, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class Order(BaseModel):
    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    # pending, waiting_payment, paid, under_review, delivered, canceled, refunded
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    coupon_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", lazy="selectin")
    payment = relationship("Payment", back_populates="order", uselist=False, lazy="selectin")


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("products.id"), nullable=False
    )
    stock_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("stock_items.id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    delivered_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    order = relationship("Order", back_populates="items")
