"""CMS models — Commands, Messages, Buttons (all DB-driven)"""
import uuid
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel


class CommandTemplate(BaseModel):
    __tablename__ = "command_templates"

    command: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # e.g. "start", "menu", "products", "wallet"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    # general, navigation, wallet, orders, admin, system
    requires_permission: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class MessageTemplate(BaseModel):
    __tablename__ = "message_templates"

    key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    # e.g. "welcome", "product_card", "payment_instructions"
    type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)
    # text, photo, video, document
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Supports placeholders: {user_name}, {product_name}, {price}, {order_id}, {qty}
    content_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_file_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parse_mode: Mapped[str] = mapped_column(String(20), default="HTML", nullable=False)
    buttons_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    group: Mapped[str] = mapped_column(String(100), default="general", nullable=False)


class ButtonTemplate(BaseModel):
    __tablename__ = "button_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    layout: Mapped[dict] = mapped_column(JSONB, nullable=False)
    layout_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    type: Mapped[str] = mapped_column(String(50), default="inline", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    group: Mapped[str] = mapped_column(String(100), default="general", nullable=False)


class ReplyButton(BaseModel):
    """Reply keyboard buttons — shown at bottom of Telegram chat"""
    __tablename__ = "reply_buttons"

    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Unique action key: shop, menu, wallet, topup, orders, referral, etc.
    text_en: Mapped[str] = mapped_column(String(100), nullable=False)
    text_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), default="📌", nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # Action types: shop, menu, wallet, topup, orders, referral, support, apikey, language
    row_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    col_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Which keyboard: "reply" for bottom keyboard, "inline" for inline menu
    keyboard_type: Mapped[str] = mapped_column(String(20), default="reply", nullable=False)

