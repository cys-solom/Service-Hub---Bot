"""Flow Builder models — visual node-based automation"""
import uuid
from sqlalchemy import String, Text, Integer, ForeignKey
from models.base import UUIDType, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from models.base import BaseModel


class FlowNode(BaseModel):
    __tablename__ = "flow_nodes"

    flow_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    # Flow group identifier, e.g. "purchase_flow", "payment_flow"
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: start, message, condition, action, input, delay, end
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    # Visual position in the editor
    position_x: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position_y: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Node configuration (message content, action params, condition logic)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # e.g. for message node: {"message_template_id": "...", "buttons_template_id": "..."}
    # e.g. for action node: {"action": "create_order", "params": {...}}
    # e.g. for condition node: {"field": "wallet_balance", "operator": ">=", "value": 10}
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FlowEdge(BaseModel):
    __tablename__ = "flow_edges"

    flow_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False
    )
    # Condition for this edge (used with condition nodes)
    condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # e.g. "true", "false", "button_clicked:buy"
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FlowExecution(BaseModel):
    __tablename__ = "flow_executions"

    flow_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id"), nullable=False
    )
    current_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("flow_nodes.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    # running, paused, completed, failed
    context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Stores user inputs, selections, etc. during flow execution
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
