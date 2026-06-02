"""Base model with UUID PK, timestamps, soft delete — works with both PostgreSQL and SQLite"""
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Boolean, String, Text, TypeDecorator, JSON
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UUIDType(TypeDecorator):
    """Platform-agnostic UUID type: CHAR(36) storage, works on both PostgreSQL and SQLite"""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(uuid.UUID(value))
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
        return value


# Cross-platform JSONB — uses JSON on all backends (works on SQLite & PostgreSQL)
JSONB = JSON


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Abstract base with UUID PK, timestamps, soft delete"""
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        primary_key=True,
        default=uuid.uuid4,
    )
