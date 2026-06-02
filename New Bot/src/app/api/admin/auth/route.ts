// src/app/api/admin/auth/route.ts
// POST = login (verify credentials, set session)
// DELETE = logout (destroy session)

import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { getSession } from "@/lib/auth";
import { getDb } from "@/lib/db";

export const dynamic = "force-dynamic";

/**
 * POST /api/admin/auth
 * Body: { username: string, password: string }
 * Sets an encrypted session cookie on success.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return NextResponse.json(
        { error: "Username and password are required" },
        { status: 400 }
      );
    }

    const db = getDb();
    const admin = await db.admin.findUnique({
      where: { username },
    });

    if (!admin) {
      return NextResponse.json(
        { error: "Invalid credentials" },
        { status: 401 }
      );
    }

    const isValid = await bcrypt.compare(password, admin.passwordHash);

    if (!isValid) {
      return NextResponse.json(
        { error: "Invalid credentials" },
        { status: 401 }
      );
    }

    // Set session
    const session = await getSession();
    session.adminId = admin.id;
    session.username = admin.username;
    session.isLoggedIn = true;
    await session.save();

    return NextResponse.json({
      success: true,
      username: admin.username,
    });
  } catch (error) {
    console.error("Login error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/admin/auth
 * Destroys the session cookie (logout).
 */
export async function DELETE() {
  try {
    const session = await getSession();
    session.destroy();

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Logout error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
