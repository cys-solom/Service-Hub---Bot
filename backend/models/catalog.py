"""Catalog models — Categories, Products, Pricing"""
import uuid
from sqlalchemy import String, Text, Float, Integer, Boolean, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("categories.id"), nullable=True
    )
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Multilingual names stored as JSONB: {"en": "Games", "ar": "ألعاب"}
    names_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    descriptions_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    products = relationship("Product", back_populates="category", lazy="selectin")
    children = relationship("Category", back_populates="parent", lazy="selectin")
    parent = relationship("Category", remote_side="Category.id", back_populates="children")


class Product(BaseModel):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    stock_type: Mapped[str] = mapped_column(
        String(50), default="code", nullable=False
    )  # code, email_pass, email_pass_2fa, custom
    delivery_mode: Mapped[str] = mapped_column(
        String(50), default="auto", nullable=False
    )  # auto, manual, semi_auto
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    force_out_of_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_qty: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    bonus_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bonus_threshold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Provider-linked product (external API)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("external_providers.id"), nullable=True
    )
    provider_product_code: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Multilingual
    names_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    descriptions_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Reply message template for after-purchase delivery
    reply_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    category = relationship("Category", back_populates="products")
    prices = relationship("ProductPrice", back_populates="product", lazy="selectin")
    stock_items = relationship("StockItem", back_populates="product", lazy="selectin")


class ProductPrice(BaseModel):
    __tablename__ = "product_prices"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    old_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_qty: Mapped[int] = mapped_column(Integer, default=999, nullable=False)

    product = relationship("Product", back_populates="prices")
