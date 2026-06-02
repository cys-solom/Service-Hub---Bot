// src/app/api/admin/products/route.ts
// GET = list all products with category + provider
// POST = create a new product

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

/** Generate a URL-safe slug from a product name. */
function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

/**
 * GET /api/admin/products
 * Returns all products with their category and provider.
 */
export async function GET() {
  try {
    const db = getDb();
    const products = await db.product.findMany({
      include: {
        category: { select: { id: true, name: true, slug: true } },
        provider: { select: { id: true, name: true, code: true } },
        _count: { select: { stockItems: { where: { isSold: false } } } },
      },
      orderBy: [{ sortOrder: "asc" }, { createdAt: "desc" }],
    });

    return NextResponse.json({
      products: products.map((p) => ({
        ...serializeProduct(p),
        availableStock: p._count.stockItems,
      })),
    });
  } catch (error) {
    console.error("List products error:", error);
    return NextResponse.json(
      { error: "Failed to list products" },
      { status: 500 }
    );
  }
}

/**
 * POST /api/admin/products
 * Body: { name, price, description?, compareAtPrice?, categoryId?,
 *         deliveryMode?, providerId?, providerProductCode?,
 *         minQty?, maxQty?, isVisible?, meta? }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, price, description, compareAtPrice, categoryId,
      deliveryMode, providerId, providerProductCode,
      minQty, maxQty, isVisible, meta } = body;

    // ─── Validate required fields ────────────────────
    if (!name || typeof name !== "string" || name.trim().length === 0) {
      return NextResponse.json(
        { error: "Product name is required" },
        { status: 400 }
      );
    }

    if (price === undefined || price === null || price === "") {
      return NextResponse.json(
        { error: "Price is required" },
        { status: 400 }
      );
    }

    // ─── Validate price as Decimal ───────────────────
    let parsedPrice: Prisma.Decimal;
    try {
      parsedPrice = new Prisma.Decimal(String(price));
      if (parsedPrice.isNegative()) {
        return NextResponse.json(
          { error: "Price must be a positive number" },
          { status: 400 }
        );
      }
    } catch {
      return NextResponse.json(
        { error: "Price must be a valid decimal number (e.g. \"12.99\")" },
        { status: 400 }
      );
    }

    let parsedCompareAtPrice: Prisma.Decimal | null = null;
    if (compareAtPrice !== undefined && compareAtPrice !== null && compareAtPrice !== "") {
      try {
        parsedCompareAtPrice = new Prisma.Decimal(String(compareAtPrice));
      } catch {
        return NextResponse.json(
          { error: "Compare-at price must be a valid decimal number" },
          { status: 400 }
        );
      }
    }

    // ─── Validate delivery mode ──────────────────────
    const mode = deliveryMode || "api";
    if (mode !== "api" && mode !== "manual") {
      return NextResponse.json(
        { error: "deliveryMode must be \"api\" or \"manual\"" },
        { status: 400 }
      );
    }

    // ─── Resolve category ────────────────────────────
    const db = getDb();
    let resolvedCategoryId = categoryId;

    if (!resolvedCategoryId) {
      // Fall back to the seeded "General" category
      const defaultCategory = await db.category.findUnique({
        where: { slug: "general" },
      });
      if (!defaultCategory) {
        return NextResponse.json(
          { error: "No default category found. Please run the database seed first." },
          { status: 400 }
        );
      }
      resolvedCategoryId = defaultCategory.id;
    } else {
      // Verify the provided category exists
      const category = await db.category.findUnique({
        where: { id: resolvedCategoryId },
      });
      if (!category) {
        return NextResponse.json(
          { error: "Category not found" },
          { status: 400 }
        );
      }
    }

    // ─── Generate unique slug ────────────────────────
    let slug = slugify(name.trim());
    if (!slug) slug = "product";

    const existingSlug = await db.product.findUnique({ where: { slug } });
    if (existingSlug) {
      // Append a short random suffix
      const suffix = Math.random().toString(36).substring(2, 7);
      slug = `${slug}-${suffix}`;
    }

    // ─── Validate provider (optional) ────────────────
    if (providerId) {
      const provider = await db.provider.findUnique({
        where: { id: providerId },
      });
      if (!provider) {
        return NextResponse.json(
          { error: "Provider not found" },
          { status: 400 }
        );
      }
    }

    // ─── Create product ──────────────────────────────
    const product = await db.product.create({
      data: {
        name: name.trim(),
        slug,
        description: description?.trim() || null,
        price: parsedPrice,
        compareAtPrice: parsedCompareAtPrice,
        categoryId: resolvedCategoryId,
        deliveryMode: mode,
        providerId: providerId || null,
        providerProductCode: providerProductCode?.trim() || null,
        minQty: typeof minQty === "number" ? minQty : 1,
        maxQty: typeof maxQty === "number" ? maxQty : 10,
        isVisible: isVisible !== false,
        meta: meta || null,
      },
      include: {
        category: { select: { id: true, name: true, slug: true } },
        provider: { select: { id: true, name: true, code: true } },
      },
    });

    return NextResponse.json(
      { product: serializeProduct(product) },
      { status: 201 }
    );
  } catch (error) {
    console.error("Create product error:", error);

    // Handle unique constraint violations
    if (
      error instanceof Prisma.PrismaClientKnownRequestError &&
      error.code === "P2002"
    ) {
      return NextResponse.json(
        { error: "A product with this slug already exists" },
        { status: 409 }
      );
    }

    return NextResponse.json(
      { error: "Failed to create product" },
      { status: 500 }
    );
  }
}
