// src/app/api/admin/providers/route.ts
// GET = list all providers with linked product count
// POST = create a new provider

import { NextRequest, NextResponse } from "next/server";
import { getDb } from "@/lib/db";
import { Prisma } from "@prisma/client";

export const dynamic = "force-dynamic";

/**
 * GET /api/admin/providers
 * Returns all providers with their linked product count.
 */
export async function GET() {
  try {
    const db = getDb();
    const providers = await db.provider.findMany({
      include: {
        _count: { select: { products: true } },
      },
      orderBy: [{ isEnabled: "desc" }, { name: "asc" }],
    });

    return NextResponse.json({
      providers: providers.map((p) => ({
        ...p,
        productCount: p._count.products,
        _count: undefined,
      })),
    });
  } catch (error) {
    console.error("List providers error:", error);
    return NextResponse.json(
      { error: "Failed to list providers" },
      { status: 500 }
    );
  }
}

/**
 * POST /api/admin/providers
 * Body: { name, code, apiUrl, isEnabled?, config? }
 *
 * No apiKey or apiSecret fields — credentials come from env vars.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, code, apiUrl, isEnabled, config } = body;

    // ─── Validate required fields ────────────────────
    if (!name || typeof name !== "string" || name.trim().length === 0) {
      return NextResponse.json(
        { error: "Provider name is required" },
        { status: 400 }
      );
    }

    if (!code || typeof code !== "string" || code.trim().length === 0) {
      return NextResponse.json(
        { error: "Provider code is required" },
        { status: 400 }
      );
    }

    // Validate code format: lowercase, alphanumeric + underscores
    const cleanCode = code.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_");
    if (cleanCode !== code.trim()) {
      return NextResponse.json(
        { error: "Provider code must be lowercase alphanumeric with underscores only (e.g. \"vex_reseller\")" },
        { status: 400 }
      );
    }

    if (!apiUrl || typeof apiUrl !== "string" || apiUrl.trim().length === 0) {
      return NextResponse.json(
        { error: "API URL is required" },
        { status: 400 }
      );
    }

    // ─── Validate config (must be object or null) ────
    if (config !== undefined && config !== null && typeof config !== "object") {
      return NextResponse.json(
        { error: "Config must be a JSON object or null" },
        { status: 400 }
      );
    }

    // ─── Create provider ─────────────────────────────
    const db = getDb();

    const provider = await db.provider.create({
      data: {
        name: name.trim(),
        code: cleanCode,
        apiUrl: apiUrl.trim(),
        isEnabled: isEnabled !== false,
        config: config || null,
      },
      include: {
        _count: { select: { products: true } },
      },
    });

    return NextResponse.json(
      {
        provider: {
          ...provider,
          productCount: provider._count.products,
          _count: undefined,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("Create provider error:", error);

    if (
      error instanceof Prisma.PrismaClientKnownRequestError &&
      error.code === "P2002"
    ) {
      return NextResponse.json(
        { error: "A provider with this code already exists" },
        { status: 409 }
      );
    }

    return NextResponse.json(
      { error: "Failed to create provider" },
      { status: 500 }
    );
  }
}
