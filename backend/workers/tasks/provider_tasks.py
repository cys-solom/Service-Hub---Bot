"""Provider tasks — sync stock from external supplier APIs"""
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from workers.celery_app import app
from core.config import settings

logger = logging.getLogger(__name__)

SYNC_DB_URL = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
engine = create_engine(SYNC_DB_URL, pool_size=3)


@app.task(name="workers.tasks.provider_tasks.sync_all_providers")
def sync_all_providers():
    """Sync stock from all enabled providers"""
    from models.provider import ExternalProvider

    with Session(engine) as session:
        providers = session.execute(
            select(ExternalProvider).where(
                ExternalProvider.is_enabled == True,
                ExternalProvider.is_deleted == False,
            )
        ).scalars().all()

        results = []
        for provider in providers:
            try:
                result = sync_provider(str(provider.id))
                results.append({"provider": provider.name, "result": result})
            except Exception as e:
                logger.error(f"Provider sync error [{provider.name}]: {e}")
                results.append({"provider": provider.name, "error": str(e)})

        return {"synced": len(results), "results": results}


@app.task(name="workers.tasks.provider_tasks.sync_provider")
def sync_provider(provider_id: str):
    """Sync stock from a single provider"""
    import requests
    from models.provider import ExternalProvider, ProviderProduct, ProviderLog

    with Session(engine) as session:
        provider = session.execute(
            select(ExternalProvider).where(ExternalProvider.id == uuid.UUID(provider_id))
        ).scalar_one_or_none()

        if not provider:
            return {"error": "Provider not found"}

        api_url = provider.api_url
        headers = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
            headers["X-Api-Key"] = provider.api_key

        try:
            # Fetch product list from provider
            resp = requests.get(f"{api_url}/products", headers=headers, timeout=15)
            resp.raise_for_status()
            products_data = resp.json()

            synced = 0
            for item in (products_data if isinstance(products_data, list) else products_data.get("products", products_data.get("data", []))):
                ext_code = str(item.get("id", item.get("code", item.get("external_id", ""))))
                name = item.get("name", item.get("title", "Unknown"))
                cost = float(item.get("price", item.get("cost", item.get("cost_price", 0))))
                available = item.get("available", item.get("in_stock", item.get("stock", True)))

                # Upsert provider product
                existing = session.execute(
                    select(ProviderProduct).where(
                        ProviderProduct.provider_id == provider.id,
                        ProviderProduct.external_code == ext_code,
                    )
                ).scalar_one_or_none()

                if existing:
                    existing.name = name
                    existing.cost_price = cost
                    existing.is_available = bool(available)
                    existing.last_synced_at = datetime.now(timezone.utc)
                else:
                    session.add(ProviderProduct(
                        provider_id=provider.id,
                        external_code=ext_code,
                        name=name,
                        cost_price=cost,
                        is_available=bool(available),
                        last_synced_at=datetime.now(timezone.utc),
                    ))

                synced += 1

            # Update provider last sync
            provider.last_sync_at = datetime.now(timezone.utc)

            # Log
            session.add(ProviderLog(
                provider_id=provider.id,
                action="sync_products",
                status="success",
                details={"synced": synced},
            ))

            session.commit()
            logger.info(f"Provider [{provider.name}] synced {synced} products")
            return {"synced": synced}

        except Exception as e:
            session.add(ProviderLog(
                provider_id=provider.id,
                action="sync_products",
                status="error",
                details={"error": str(e)},
            ))
            session.commit()
            logger.error(f"Provider sync failed [{provider.name}]: {e}")
            return {"error": str(e)}


@app.task(name="workers.tasks.provider_tasks.fetch_from_provider")
def fetch_from_provider(provider_id: str, product_id: str, quantity: int = 1):
    """Purchase stock from a provider and add to inventory"""
    import requests
    from models.provider import ExternalProvider, ProviderProduct, ProviderLog
    from models.stock import StockItem
    from models.catalog import Product

    with Session(engine) as session:
        provider = session.execute(
            select(ExternalProvider).where(ExternalProvider.id == uuid.UUID(provider_id))
        ).scalar_one_or_none()

        if not provider:
            return {"error": "Provider not found"}

        # Find the provider product linked to our product
        pp = session.execute(
            select(ProviderProduct).where(
                ProviderProduct.provider_id == provider.id,
                ProviderProduct.product_id == uuid.UUID(product_id),
                ProviderProduct.is_deleted == False,
            )
        ).scalar_one_or_none()

        if not pp:
            return {"error": "No provider product mapping found"}

        api_url = provider.api_url
        headers = {}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
            headers["X-Api-Key"] = provider.api_key
            headers["Content-Type"] = "application/json"

        try:
            # Place order with provider
            resp = requests.post(
                f"{api_url}/orders",
                json={
                    "product_id": pp.external_code,
                    "quantity": quantity,
                },
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            order_data = resp.json()

            # Extract delivered items
            items = order_data.get("items", order_data.get("data", order_data.get("codes", [])))
            if isinstance(items, str):
                items = items.strip().split("\n")

            batch_id = f"prov_{uuid.uuid4().hex[:8]}"
            added = 0
            for item_data in items:
                if isinstance(item_data, dict):
                    data_str = item_data.get("code", item_data.get("data", str(item_data)))
                else:
                    data_str = str(item_data).strip()

                if data_str:
                    session.add(StockItem(
                        product_id=uuid.UUID(product_id),
                        data=data_str,
                        is_sold=False,
                        batch_id=batch_id,
                    ))
                    added += 1

            # Log
            session.add(ProviderLog(
                provider_id=provider.id,
                action="purchase",
                status="success",
                details={"product": pp.external_code, "quantity": quantity, "received": added, "batch_id": batch_id},
            ))

            session.commit()
            logger.info(f"Fetched {added} items from provider [{provider.name}]")
            return {"added": added, "batch_id": batch_id}

        except Exception as e:
            session.add(ProviderLog(
                provider_id=provider.id,
                action="purchase",
                status="error",
                details={"error": str(e)},
            ))
            session.commit()
            logger.error(f"Provider fetch error [{provider.name}]: {e}")
            return {"error": str(e)}
