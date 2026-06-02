"""Categories CRUD API"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_admin
from models.catalog import Category, Product
from models.stock import StockItem

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryIn(BaseModel):
    name: str
    slug: str = ""
    description: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    is_visible: bool = True
    parent_id: Optional[str] = None
    names_i18n: Optional[dict] = None
    descriptions_i18n: Optional[dict] = None


@router.get("")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).where(Category.is_deleted == False).order_by(Category.sort_order, Category.name)
    )
    cats = result.scalars().all()
    items = []
    for c in cats:
        prod_count = (await db.execute(
            select(func.count(Product.id)).where(Product.category_id == c.id, Product.is_deleted == False)
        )).scalar() or 0
        stock_count = (await db.execute(
            select(func.count(StockItem.id))
            .join(Product, StockItem.product_id == Product.id)
            .where(Product.category_id == c.id, StockItem.is_sold == False, StockItem.is_deleted == False)
        )).scalar() or 0
        items.append({
            "id": str(c.id), "name": c.name, "slug": c.slug,
            "description": c.description, "image_url": c.image_url,
            "sort_order": c.sort_order, "is_visible": c.is_visible,
            "parent_id": str(c.parent_id) if c.parent_id else None,
            "names_i18n": c.names_i18n, "descriptions_i18n": c.descriptions_i18n,
            "products_count": prod_count, "stock_available": stock_count,
        })
    return {"categories": items}


@router.post("")
async def create_category(
    data: CategoryIn, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    slug = data.slug or data.name.lower().replace(" ", "-")
    cat = Category(
        name=data.name, slug=slug, description=data.description,
        image_url=data.image_url, sort_order=data.sort_order,
        is_visible=data.is_visible,
        parent_id=uuid.UUID(data.parent_id) if data.parent_id else None,
        names_i18n=data.names_i18n, descriptions_i18n=data.descriptions_i18n,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"success": True, "id": str(cat.id)}


@router.put("/{cat_id}")
async def update_category(
    cat_id: str, data: CategoryIn,
    db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    cat = (await db.execute(select(Category).where(Category.id == uuid.UUID(cat_id)))).scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Category not found")
    for field in ["name", "slug", "description", "image_url", "sort_order", "is_visible", "names_i18n", "descriptions_i18n"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(cat, field, val)
    if data.parent_id:
        cat.parent_id = uuid.UUID(data.parent_id)
    await db.commit()
    return {"success": True}


@router.delete("/{cat_id}")
async def delete_category(
    cat_id: str, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)
):
    cat = (await db.execute(select(Category).where(Category.id == uuid.UUID(cat_id)))).scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Category not found")
    cat.is_deleted = True
    await db.commit()
    return {"success": True}
