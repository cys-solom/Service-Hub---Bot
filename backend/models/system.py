"""System models — Audit, Settings, i18n, Notifications, Media, Rate Limits, Backups"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, Float, BigInteger, DateTime, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # admin, user, system
    actor_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)


class AppSetting(BaseModel):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    type: Mapped[str] = mapped_column(String(50), default="string", nullable=False)
    # string, number, boolean, json
    group: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Language(BaseModel):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    native_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_rtl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    flag_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)


class Translation(BaseModel):
    __tablename__ = "translations"

    language_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    group: Mapped[str] = mapped_column(String(100), default="bot", nullable=False)


class Notification(BaseModel):
    __tablename__ = "notifications"

    type: Mapped[str] = mapped_column(String(100), nullable=False)
    # new_order, payment_received, low_stock, delivery_completed
    target: Mapped[str] = mapped_column(String(50), nullable=False)
    # admin, user
    channel: Mapped[str] = mapped_column(String(50), default="telegram", nullable=False)
    # telegram, email, webhook
    template: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class NotificationLog(BaseModel):
    __tablename__ = "notification_logs"

    notification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("notifications.id"), nullable=True
    )
    recipient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="sent", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class MediaFile(BaseModel):
    __tablename__ = "media_files"

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group: Mapped[str] = mapped_column(String(100), default="general", nullable=False)


class RateLimit(BaseModel):
    __tablename__ = "rate_limits"

    key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    # e.g. "command:start", "payment:create", "api:products"
    max_requests: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    applies_to: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    # user, ip, global


class Backup(BaseModel):
    __tablename__ = "backups"

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="full", nullable=False)
    # full, incremental, data_only
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
