// src/middleware.ts
// Next.js middleware — protects /admin/* routes.
// Unauthenticated requests are redirected to /admin/login.
// Does NOT protect /admin/login or /api/admin/auth (the login endpoint).
//
// Security: Uses getIronSession() which DECRYPTS + VERIFIES the sealed cookie
// using SESSION_SECRET. It does NOT just check cookie existence.
// A forged or tampered cookie will result in an empty session object.

import { NextRequest, NextResponse } from "next/server";
import { getIronSession } from "iron-session";
import { getSessionConfig, type SessionData } from "@/lib/auth";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip protection for login page and auth API
  if (
    pathname === "/admin/login" ||
    pathname.startsWith("/api/admin/auth")
  ) {
    return NextResponse.next();
  }

  // Decrypt and verify the session cookie
  let isAuthenticated = false;

  try {
    const response = NextResponse.next();
    const session = await getIronSession<SessionData>(
      request,
      response,
      getSessionConfig()
    );

    if (session.isLoggedIn && session.adminId) {
      isAuthenticated = true;
      return response;
    }
  } catch {
    // SESSION_SECRET missing or invalid — treat as unauthenticated
  }

  if (!isAuthenticated) {
    // For API routes, return 401 instead of redirect
    if (pathname.startsWith("/api/admin")) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const loginUrl = new URL("/admin/login", request.url);
    return NextResponse.redirect(loginUrl);
  }
}

// Only run middleware on /admin/* and /api/admin/* routes
export const config = {
  matcher: ["/admin/:path*", "/api/admin/:path*"],
};
