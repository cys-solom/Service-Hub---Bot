"""Flows API — visual flow builder CRUD"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_admin
from models.flow import FlowNode, FlowEdge

router = APIRouter(prefix="/flows", tags=["flows"])

class FlowNodeIn(BaseModel):
    type: str
    label: str
    position_x: int = 0
    position_y: int = 0
    config: dict = {}

class FlowEdgeIn(BaseModel):
    source_node_id: str
    target_node_id: str
    condition: Optional[str] = None
    label: Optional[str] = None

class FlowSave(BaseModel):
    nodes: list[dict]
    edges: list[dict]

@router.get("")
async def list_flows(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(FlowNode.flow_id).distinct())
    flow_ids = [r[0] for r in result.all()]
    flows = []
    for fid in flow_ids:
        node_count = (await db.execute(
            select(FlowNode).where(FlowNode.flow_id == fid, FlowNode.is_deleted == False)
        )).scalars().all()
        flows.append({"flow_id": fid, "node_count": len(node_count)})
    return {"flows": flows}

@router.get("/{flow_id}")
async def get_flow(flow_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    nodes = (await db.execute(
        select(FlowNode).where(FlowNode.flow_id == flow_id, FlowNode.is_deleted == False)
    )).scalars().all()
    edges = (await db.execute(
        select(FlowEdge).where(FlowEdge.flow_id == flow_id, FlowEdge.is_deleted == False)
    )).scalars().all()
    return {
        "flow_id": flow_id,
        "nodes": [{
            "id": str(n.id), "type": n.type, "label": n.label,
            "position": {"x": n.position_x, "y": n.position_y},
            "config": n.config,
        } for n in nodes],
        "edges": [{
            "id": str(e.id), "source": str(e.source_node_id),
            "target": str(e.target_node_id),
            "condition": e.condition, "label": e.label,
        } for e in edges],
    }

@router.put("/{flow_id}")
async def save_flow(flow_id: str, data: FlowSave, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    # Delete existing
    await db.execute(delete(FlowEdge).where(FlowEdge.flow_id == flow_id))
    await db.execute(delete(FlowNode).where(FlowNode.flow_id == flow_id))
    await db.flush()

    node_id_map = {}
    for n in data.nodes:
        node = FlowNode(
            flow_id=flow_id, type=n["type"], label=n.get("label", ""),
            position_x=n.get("position", {}).get("x", 0),
            position_y=n.get("position", {}).get("y", 0),
            config=n.get("config", {}),
        )
        db.add(node)
        await db.flush()
        node_id_map[n.get("id", str(node.id))] = node.id

    for e in data.edges:
        src = node_id_map.get(e["source"])
        tgt = node_id_map.get(e["target"])
        if src and tgt:
            db.add(FlowEdge(
                flow_id=flow_id, source_node_id=src, target_node_id=tgt,
                condition=e.get("condition"), label=e.get("label"),
            ))

    await db.commit()
    return {"success": True}

@router.delete("/{flow_id}")
async def delete_flow(flow_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    await db.execute(delete(FlowEdge).where(FlowEdge.flow_id == flow_id))
    await db.execute(delete(FlowNode).where(FlowNode.flow_id == flow_id))
    await db.commit()
    return {"success": True}
