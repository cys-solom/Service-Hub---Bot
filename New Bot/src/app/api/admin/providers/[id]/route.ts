// src/app/api/admin/providers/[id]/route.ts
// GET = single provider
// PUT = update provider
// DELETE = soft-disable (set isEnabled = false)

import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ id: string }> };

/**
 * GET /api/admin/providers/[id]
 */
export async function GET(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const db = getDb();

    const provider = await db.provider.findUnique({
      where: { id },
      include: {
        _count: { select: { products: true } },
        products: {
          select: { id: true, name: true, slug: true, isVisible: true },
          orderBy: { name: "asc" },
          take: 50,
        },
      },
    });

    if (!provider) {
      return NextResponse.json(
        { error: "Provider not found" },
        { status: 404 }
      );
    }

    return NextResponse.json({
      provider: {
        ...provider,
        productCount: provider._count.products,
        _count: undefined,
      },
    });
  } catch (error) {
    console.error("Get provider error:", error);
    return NextResponse.json(
      { error: "Failed to get provider" },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/admin/providers/[id]
 * Accepts partial updates. Only provided fields are updated.
 * Does NOT accept apiKey or apiSecret — those live in env vars only.
 */
export async function PUT(
  request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const body = await request.json();
    const db = getDb();

    const existing = await db.provider.findUnique({ where: { id } });
    if (!existing) {
      return NextResponse.json(
        { error: "Provider not found" },
        { status: 404 }
      );
    }

    const updateData: Record<string, unknown> = {};

    if (body.name !== undefined) {
      if (typeof body.name !== "string" || body.name.trim().length === 0) {
        return NextResponse.json(
          { error: "Provider name cannot be empty" },
          { status: 400 }
        );
      }
      updateData.name = body.name.trim();
    }

    if (body.apiUrl !== undefined) {
      if (typeof body.apiUrl !== "string" || body.apiUrl.trim().length === 0) {
        return NextResponse.json(
          { error: "API URL cannot be empty" },
          { status: 400 }
        );
      }
      updateData.apiUrl = body.apiUrl.trim();
    }

    if (body.isEnabled !== undefined) {
      updateData.isEnabled = Boolean(body.isEnabled);
    }

    if (body.config !== undefined) {
      if (body.config !== null && typeof body.config !== "object") {
        return NextResponse.json(
          { error: "Config must be a JSON object or null" },
          { status: 400 }
        );
      }
      updateData.config = body.config;
    }

    if (body.lastSyncAt !== undefined) {
      updateData.lastSyncAt = body.lastSyncAt ? new Date(body.lastSyncAt) : null;
    }

    // Code is immutable after creation — changing it would break env var mapping
    if (body.code !== undefined && body.code !== existing.code) {
      return NextResponse.json(
        { error: "Provider code cannot be changed after creation. It is used to map environment variables." },
        { status: 400 }
      );
    }

    const provider = await db.provider.update({
      where: { id },
      data: updateData,
      include: {
        _count: { select: { products: true } },
      },
    });

    return NextResponse.json({
      provider: {
        ...provider,
        productCount: provider._count.products,
        _count: undefined,
      },
    });
  } catch (error) {
    console.error("Update provider error:", error);
    return NextResponse.json(
      { error: "Failed to update provider" },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/admin/providers/[id]
 * Soft-disable: sets isEnabled = false.
 * Does NOT delete the record — linked products would break.
 */
export async function DELETE(
  _request: NextRequest,
  context: RouteContext
) {
  try {
    const { id } = await context.params;
    const db = getDb();

    const existing = await db.provider.findUnique({
      where: { id },
      include: { _count: { select: { products: true } } },
    });

    if (!existing) {
      return NextResponse.json(
        { error: "Provider not found" },
        { status: 404 }
      );
    }

    const provider = await db.provider.update({
      where: { id },
      data: { isEnabled: false },
      include: { _count: { select: { products: true } } },
    });

    return NextResponse.json({
      provider: {
        ...provider,
        productCount: provider._count.products,
        _count: undefined,
      },
      message: "Provider disabled (soft-deleted)",
    });
  } catch (error) {
    console.error("Delete provider error:", error);
    return NextResponse.json(
      { error: "Failed to delete provider" },
      { status: 500 }
    );
  }
}
