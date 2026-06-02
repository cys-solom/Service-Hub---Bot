"""Public Reseller API — External API for resellers to pull stock"""
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel as PydanticBase
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.reseller import ResellerKey, ResellerTransaction
from models.catalog import Product, ProductPrice, Category
from models.stock import StockItem

router = APIRouter(prefix="/public", tags=["public-api"])
logger = logging.getLogger(__name__)


# ─── API Key Auth ─────────────────────────────────────

async def get_reseller(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> ResellerKey:
    """Validate API key and return reseller"""
    reseller = (await db.execute(
        select(ResellerKey).where(
            ResellerKey.api_key == x_api_key,
            ResellerKey.is_active == True,
            ResellerKey.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not reseller:
        raise HTTPException(401, {"error": "invalid_api_key", "message": "Invalid or inactive API key"})

    return reseller


# ─── Products ─────────────────────────────────────────

@router.get("/products")
async def list_products(
    category: str = None,
    db: AsyncSession = Depends(get_db),
    reseller: ResellerKey = Depends(get_reseller),
):
    """List available products with wholesale prices and stock counts"""
    query = select(Product).where(
        Product.is_visible == True,
        Product.is_deleted == False,
        Product.force_out_of_stock == False,
    )
    if category:
        cat = (await db.execute(
            select(Category).where(Category.slug == category, Category.is_deleted == False)
        )).scalar_one_or_none()
        if cat:
            query = query.where(Product.category_id == cat.id)

    result = await db.execute(query.order_by(Product.sort_order))
    products = []

    for p in result.scalars().all():
        # Get wholesale price from meta, fallback to regular price
        meta = p.meta or {}
        wholesale_price = meta.get("wholesale_price")

        # Regular price
        price_obj = (await db.execute(
            select(ProductPrice).where(ProductPrice.product_id == p.id)
            .order_by(ProductPrice.min_qty)
        )).scalars().first()
        regular_price = price_obj.price if price_obj else 0

        if wholesale_price is None:
            wholesale_price = regular_price

        # Stock count
        stock_count = (await db.execute(
            select(func.count(StockItem.id)).where(
                StockItem.product_id == p.id,
                StockItem.is_sold == False,
                StockItem.is_reserved == False,
                StockItem.is_deleted == False,
            )
        )).scalar() or 0

        # Category name
        cat = (await db.execute(
            select(Category).where(Category.id == p.category_id)
        )).scalar_one_or_none()

        products.append({
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "category": cat.name if cat else None,
            "price": float(wholesale_price),
            "stock": stock_count,
            "min_qty": p.min_qty,
            "max_qty": p.max_qty,
        })

    return {"success": True, "products": products}


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    reseller: ResellerKey = Depends(get_reseller),
):
    """Get product details"""
    p = (await db.execute(
        select(Product).where(
            Product.id == uuid.UUID(product_id),
            Product.is_visible == True,
            Product.is_deleted == False,
        )
    )).scalar_one_or_none()

    if not p:
        raise HTTPException(404, {"error": "not_found", "message": "Product not found"})

    meta = p.meta or {}
    wholesale_price = meta.get("wholesale_price")

    price_obj = (await db.execute(
        select(ProductPrice).where(ProductPrice.product_id == p.id)
        .order_by(ProductPrice.min_qty)
    )).scalars().first()
    regular_price = price_obj.price if price_obj else 0

    if wholesale_price is None:
        wholesale_price = regular_price

    stock_count = (await db.execute(
        select(func.count(StockItem.id)).where(
            StockItem.product_id == p.id,
            StockItem.is_sold == False,
            StockItem.is_reserved == False,
            StockItem.is_deleted == False,
        )
    )).scalar() or 0

    cat = (await db.execute(
        select(Category).where(Category.id == p.category_id)
    )).scalar_one_or_none()

    return {
        "success": True,
        "product": {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "category": cat.name if cat else None,
            "price": float(wholesale_price),
            "stock": stock_count,
            "min_qty": p.min_qty,
            "max_qty": p.max_qty,
        }
    }


# ─── Purchase ─────────────────────────────────────────

class PurchaseRequest(PydanticBase):
    product_id: str
    quantity: int = 1

@router.post("/purchase")
async def purchase(
    data: PurchaseRequest,
    db: AsyncSession = Depends(get_db),
    reseller: ResellerKey = Depends(get_reseller),
):
    """Purchase stock items — deducts from reseller wallet and returns items"""

    # Validate product
    product = (await db.execute(
        select(Product).where(
            Product.id == uuid.UUID(data.product_id),
            Product.is_visible == True,
            Product.is_deleted == False,
            Product.force_out_of_stock == False,
        )
    )).scalar_one_or_none()

    if not product:
        raise HTTPException(404, {"error": "not_found", "message": "Product not found or out of stock"})

    # Validate quantity
    if data.quantity < product.min_qty:
        raise HTTPException(400, {"error": "min_qty", "message": f"Minimum quantity is {product.min_qty}"})
    if data.quantity > product.max_qty:
        raise HTTPException(400, {"error": "max_qty", "message": f"Maximum quantity is {product.max_qty}"})

    # Get wholesale price
    meta = product.meta or {}
    wholesale_price = meta.get("wholesale_price")
    if wholesale_price is None:
        price_obj = (await db.execute(
            select(ProductPrice).where(ProductPrice.product_id == product.id)
            .order_by(ProductPrice.min_qty)
        )).scalars().first()
        wholesale_price = price_obj.price if price_obj else 0

    wholesale_price = float(wholesale_price)
    total_cost = wholesale_price * data.quantity

    # Check balance
    if reseller.balance < total_cost:
        raise HTTPException(400, {
            "error": "insufficient_balance",
            "message": f"Insufficient balance. Need ${total_cost:.2f}, have ${reseller.balance:.2f}",
            "required": total_cost,
            "balance": reseller.balance,
        })

    # Check stock availability
    available = (await db.execute(
        select(StockItem).where(
            StockItem.product_id == product.id,
            StockItem.is_sold == False,
            StockItem.is_reserved == False,
            StockItem.is_deleted == False,
        ).order_by(StockItem.sort_order, StockItem.created_at)
        .limit(data.quantity)
    )).scalars().all()

    if len(available) < data.quantity:
        raise HTTPException(400, {
            "error": "insufficient_stock",
            "message": f"Only {len(available)} items in stock, requested {data.quantity}",
            "available": len(available),
        })

    # Deduct balance
    balance_before = reseller.balance
    reseller.balance -= total_cost
    reseller.total_spent += total_cost
    reseller.total_orders += 1

    # Mark items as sold and collect data
    items_data = []
    for item in available:
        item.is_sold = True
        items_data.append(item.data)

    # Log transaction
    tx = ResellerTransaction(
        reseller_id=reseller.id,
        type="purchase",
        amount=-total_cost,
        balance_before=balance_before,
        balance_after=reseller.balance,
        product_id=product.id,
        product_name=product.name,
        quantity=data.quantity,
        items_data="\n".join(items_data),
        description=f"Purchased {data.quantity}x {product.name}",
    )
    db.add(tx)

    await db.commit()

    logger.info(f"[Reseller] {reseller.name} purchased {data.quantity}x {product.name} for ${total_cost:.2f}")

    return {
        "success": True,
        "items": items_data,
        "quantity": data.quantity,
        "unit_price": wholesale_price,
        "total_cost": total_cost,
        "balance": round(reseller.balance, 2),
    }


# ─── Balance ──────────────────────────────────────────

@router.get("/balance")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    reseller: ResellerKey = Depends(get_reseller),
):
    """Check reseller balance"""
    return {
        "success": True,
        "balance": round(reseller.balance, 2),
        "total_deposited": round(reseller.total_deposited, 2),
        "total_spent": round(reseller.total_spent, 2),
        "total_orders": reseller.total_orders,
    }


# ─── Orders History ──────────────────────────────────

@router.get("/orders")
async def list_orders(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    reseller: ResellerKey = Depends(get_reseller),
):
    """List reseller's purchase history"""
    query = select(ResellerTransaction).where(
        ResellerTransaction.reseller_id == reseller.id,
        ResellerTransaction.is_deleted == False,
    ).order_by(ResellerTransaction.created_at.desc())

    total = (await db.execute(
        select(func.count(ResellerTransaction.id)).where(
            ResellerTransaction.reseller_id == reseller.id,
            ResellerTransaction.is_deleted == False,
        )
    )).scalar() or 0

    result = await db.execute(query.offset((page - 1) * limit).limit(limit))
    orders = []
    for tx in result.scalars().all():
        orders.append({
            "id": str(tx.id),
            "type": tx.type,
            "product_name": tx.product_name,
            "quantity": tx.quantity,
            "amount": round(tx.amount, 2),
            "balance_after": round(tx.balance_after, 2),
            "description": tx.description,
            "created_at": tx.created_at.isoformat(),
        })

    return {
        "success": True,
        "orders": orders,
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }
