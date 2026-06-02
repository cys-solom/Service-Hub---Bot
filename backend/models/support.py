"""Support ticket model"""
import uuid
from sqlalchemy import String, Text, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import BaseModel


class SupportTicket(BaseModel):
    __tablename__ = "support_tickets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    # open, in_progress, resolved, closed
    priority: Mapped[str] = mapped_column(String(50), default="normal", nullable=False)
    # low, normal, high, urgent
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("admins.id"), nullable=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("orders.id"), nullable=True
    )
    replies: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Array of {sender, message, timestamp}

    user = relationship("User", back_populates="support_tickets")

