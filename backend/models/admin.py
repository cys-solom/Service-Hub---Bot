"""Admin, Role, Permission models — RBAC system"""
import uuid
from sqlalchemy import String, Boolean, ForeignKey, Text
from models.base import UUIDType
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_super: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    permissions = relationship("RolePermission", back_populates="role", lazy="selectin")
    admins = relationship("Admin", back_populates="role", lazy="selectin")


class Permission(BaseModel):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    group: Mapped[str] = mapped_column(String(100), default="general", nullable=False)

    roles = relationship("RolePermission", back_populates="permission", lazy="selectin")


class RolePermission(BaseModel):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class Admin(BaseModel):
    __tablename__ = "admins"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("roles.id"), nullable=True
    )

    role = relationship("Role", back_populates="admins")
