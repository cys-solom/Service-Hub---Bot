"""Stock tasks — low stock alerts, auto-restock from providers"""
import logging
from sqlalchemy import select, func, create_engine
from sqlalchemy.orm import Session

from workers.celery_app import app
from core.config import settings

logger = logging.getLogger(__name__)

SYNC_DB_URL = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
engine = create_engine(SYNC_DB_URL, pool_size=3)


@app.task(name="workers.tasks.stock_tasks.check_low_stock_alerts")
def check_low_stock_alerts():
    """Check for products with low stock and create notifications"""
    from models.catalog import Product
    from models.stock import StockItem
    from models.system import Notification, NotificationLog

    LOW_STOCK_THRESHOLD = 5

    with Session(engine) as session:
        # Get products with stock count
        results = session.execute(
            select(
                Product.id, Product.name,
                func.count(StockItem.id).label("available")
            )
            .join(StockItem, StockItem.product_id == Product.id)
            .where(StockItem.is_sold == False, StockItem.is_deleted == False, Product.is_deleted == False)
            .group_by(Product.id, Product.name)
            .having(func.count(StockItem.id) < LOW_STOCK_THRESHOLD)
        ).all()

        low_stock_products = []
        for product_id, name, available in results:
            low_stock_products.append({
                "product_id": str(product_id),
                "name": name,
                "available": available,
            })

        if low_stock_products:
            logger.warning(f"Low stock alert: {len(low_stock_products)} products below threshold")

            # Create notification log
            for p in low_stock_products:
                session.add(NotificationLog(
                    notification_id=None,
                    channel="system",
                    recipient_id="admin",
                    content=f"Low stock: {p['name']} ({p['available']} left)",
                    status="sent",
                ))

            session.commit()

        return {"low_stock_count": len(low_stock_products), "products": low_stock_products}


@app.task(name="workers.tasks.stock_tasks.auto_restock")
def auto_restock(product_id: str, provider_id: str, quantity: int = 10):
    """Trigger auto-restock from external provider"""
    from workers.tasks.provider_tasks import fetch_from_provider
    result = fetch_from_provider.delay(provider_id, product_id, quantity)
    return {"task_id": str(result.id), "status": "queued"}
