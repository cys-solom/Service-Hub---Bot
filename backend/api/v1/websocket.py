"""WebSocket endpoint for real-time dashboard updates"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.order import Order
from models.user import User
from models.stock import StockItem
from models.support import SupportTicket

router = APIRouter(tags=["websocket"])

# Connected clients store
active_connections: list[WebSocket] = []


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.append(ws)

    try:
        while True:
            # Send stats every 5 seconds
            try:
                async with get_db() as session:
                    stats = await get_live_stats(session)
                    await ws.send_json({"type": "stats", "data": stats})
            except Exception:
                pass

            # Wait for 5 seconds or incoming message
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        active_connections.remove(ws)
    except Exception:
        if ws in active_connections:
            active_connections.remove(ws)


async def get_live_stats(session: AsyncSession):
    """Get real-time stats for WebSocket broadcast"""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    pending_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.status.in_(["pending", "waiting_payment", "under_review"]))
    )).scalar() or 0

    today_orders = (await session.execute(
        select(func.count(Order.id)).where(Order.created_at >= today)
    )).scalar() or 0

    today_revenue = float((await session.execute(
        select(func.coalesce(func.sum(Order.final_amount), 0))
        .where(Order.status == "delivered", Order.created_at >= today)
    )).scalar() or 0)

    stock_available = (await session.execute(
        select(func.count(StockItem.id)).where(StockItem.is_sold == False, StockItem.is_deleted == False)
    )).scalar() or 0

    open_tickets = (await session.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(["open", "in_progress"]))
    )).scalar() or 0

    return {
        "pending_orders": pending_orders,
        "today_orders": today_orders,
        "today_revenue": round(today_revenue, 2),
        "stock_available": stock_available,
        "open_tickets": open_tickets,
        "timestamp": now.isoformat(),
    }


async def broadcast(event_type: str, data: dict):
    """Broadcast event to all connected WebSocket clients"""
    message = json.dumps({"type": event_type, "data": data})
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        active_connections.remove(ws)
