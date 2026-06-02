// src/app/api/health/route.ts
// Smoke-test endpoint. Verifies the app is running and can reach the database.

import { NextResponse } from "next/server";
import { getDb } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const db = getDb();

    // Quick DB connectivity check — count admins (lightweight query)
    const adminCount = await db.admin.count();

    return NextResponse.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      database: "connected",
      admins: adminCount,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown database error";
    return NextResponse.json(
      {
        status: "error",
        timestamp: new Date().toISOString(),
        database: "disconnected",
        error: message,
      },
      { status: 503 }
    );
  }
}
