// src/app/api/admin/products/[id]/route.ts
// GET = single product
// PUT = update product
// DELETE = soft-delete (set isVisible = false)

import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { Prisma } from "@prisma/client";

export const dynamic = "force-dynamic";

/** Serialize Decimal fields to strings for safe JSON transport. */
function serializeProduct(product: Record<string, unknown>) {
  return {
    ...product,
    price: String(product.price),
    compareAtPrice: product.compareAtPrice ? String(product.compareAtPrice) : null,
  };
}

type RouteContext = { params: Promise<{ id: string }> };

/**
 * GET /api/admin/products/[id]
 */
export async function GET(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const db = getDb();

    const product = await db.product.findUnique({
      where: { id },
      include: {
        category: { select: { id: true, name: true, slug: true } },
        provider: { select: { id: true, name: true, code: true } },
        _count: { select: { stockItems: { where: { isSold: false } } } },
      },
    });

    if (!product) {
      return NextResponse.json(
        { error: "Product not found" },
        { status: 404 }
      );
    }

    return NextResponse.json({
      product: {
        ...serializeProduct(product),
        availableStock: product._count.stockItems,
      },
    });
  } catch (error) {
    console.error("Get product error:", error);
    return NextResponse.json(
      { error: "Failed to get product" },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/admin/products/[id]
 * Accepts partial updates. Only provided fields are updated.
 */
export async function PUT(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const body = await request.json();
    const db = getDb();

    // Verify product exists
    const existing = await db.product.findUnique({ where: { id } });
    if (!existing) {
      return NextResponse.json(
        { error: "Product not found" },
        { status: 404 }
      );
    }

    // Build update data from provided fields only
    const updateData: Record<string, unknown> = {};

    // ─── Text fields ─────────────────────────────────
    if (body.name !== undefined) {
      if (typeof body.name !== "string" || body.name.trim().length === 0) {
        return NextResponse.json(
          { error: "Product name cannot be empty" },
          { status: 400 }
        );
      }
      updateData.name = body.name.trim();
    }

    if (body.description !== undefined) {
      updateData.description = body.description?.trim() || null;
    }

    // ─── Price fields (Decimal-safe) ─────────────────
    if (body.price !== undefined) {
      try {
        const parsed = new Prisma.Decimal(String(body.price));
        if (parsed.isNegative()) {
          return NextResponse.json(
            { error: "Price must be a positive number" },
            { status: 400 }
          );
        }
        updateData.price = parsed;
      } catch {
        return NextResponse.json(
          { error: "Price must be a valid decimal number" },
          { status: 400 }
        );
      }
    }

    if (body.compareAtPrice !== undefined) {
      if (body.compareAtPrice === null || body.compareAtPrice === "") {
        updateData.compareAtPrice = null;
      } else {
        try {
          updateData.compareAtPrice = new Prisma.Decimal(String(body.compareAtPrice));
        } catch {
          return NextResponse.json(
            { error: "Compare-at price must be a valid decimal number" },
            { status: 400 }
          );
        }
      }
    }

    // ─── Boolean toggles ─────────────────────────────
    if (body.isVisible !== undefined) {
      updateData.isVisible = Boolean(body.isVisible);
    }

    if (body.isOutOfStock !== undefined) {
      updateData.isOutOfStock = Boolean(body.isOutOfStock);
    }

    // ─── Delivery mode ───────────────────────────────
    if (body.deliveryMode !== undefined) {
      if (body.deliveryMode !== "api" && body.deliveryMode !== "manual") {
        return NextResponse.json(
          { error: "deliveryMode must be \"api\" or \"manual\"" },
          { status: 400 }
        );
      }
      updateData.deliveryMode = body.deliveryMode;
    }

    // ─── Quantity limits ─────────────────────────────
    if (body.minQty !== undefined) {
      updateData.minQty = Number(body.minQty);
    }
    if (body.maxQty !== undefined) {
      updateData.maxQty = Number(body.maxQty);
    }

    // ─── Category ────────────────────────────────────
    if (body.categoryId !== undefined) {
      const category = await db.category.findUnique({
        where: { id: body.categoryId },
      });
      if (!category) {
        return NextResponse.json(
          { error: "Category not found" },
          { status: 400 }
        );
      }
      updateData.categoryId = body.categoryId;
    }

    // ─── Provider (optional) ─────────────────────────
    if (body.providerId !== undefined) {
      if (body.providerId === null || body.providerId === "") {
        updateData.providerId = null;
        updateData.providerProductCode = null;
      } else {
        const provider = await db.provider.findUnique({
          where: { id: body.providerId },
        });
        if (!provider) {
          return NextResponse.json(
            { error: "Provider not found" },
            { status: 400 }
          );
        }
        updateData.providerId = body.providerId;
      }
    }

    if (body.providerProductCode !== undefined) {
      updateData.providerProductCode = body.providerProductCode?.trim() || null;
    }

    // ─── Sort order ──────────────────────────────────
    if (body.sortOrder !== undefined) {
      updateData.sortOrder = Number(body.sortOrder);
    }

    // ─── Meta (JSON) ─────────────────────────────────
    if (body.meta !== undefined) {
      updateData.meta = body.meta;
    }

    // ─── Perform update ──────────────────────────────
    const product = await db.product.update({
      where: { id },
      data: updateData,
      include: {
        category: { select: { id: true, name: true, slug: true } },
        provider: { select: { id: true, name: true, code: true } },
      },
    });

    return NextResponse.json({ product: serializeProduct(product) });
  } catch (error) {
    console.error("Update product error:", error);
    return NextResponse.json(
      { error: "Failed to update product" },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/admin/products/[id]
 * Soft-delete: sets isVisible = false.
 */
export async function DELETE(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const db = getDb();

    const existing = await db.product.findUnique({ where: { id } });
    if (!existing) {
      return NextResponse.json(
        { error: "Product not found" },
        { status: 404 }
      );
    }

    const product = await db.product.update({
      where: { id },
      data: { isVisible: false },
    });

    return NextResponse.json({
      product: serializeProduct(product),
      message: "Product hidden (soft-deleted)",
    });
  } catch (error) {
    console.error("Delete product error:", error);
    return NextResponse.json(
      { error: "Failed to delete product" },
      { status: 500 }
    );
  }
}
