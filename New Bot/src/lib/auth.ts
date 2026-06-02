// src/lib/auth.ts
// Admin session management using iron-session.
// SESSION_SECRET comes from environment variables only.

import {
  getIronSession,
  type SessionOptions,
  type IronSession,
} from "iron-session";
import { cookies } from "next/headers";

/** Shape of data stored in the encrypted session cookie. */
export interface SessionData {
  adminId?: string;
  username?: string;
  isLoggedIn?: boolean;
}

/** Cookie name — shared between auth.ts and middleware.ts via getSessionConfig(). */
const COOKIE_NAME = "sh_admin_session";

/** Session TTL in seconds (24 hours). */
const SESSION_TTL = 60 * 60 * 24;

/**
 * Build iron-session options. Used by both auth.ts and middleware.ts
 * to ensure identical config (cookie name, password, options).
 *
 * Throws if SESSION_SECRET is missing or too short.
 */
export function getSessionConfig(): SessionOptions {
  const password = process.env.SESSION_SECRET;

  if (!password || password.length < 32) {
    throw new Error(
      "SESSION_SECRET must be set in environment variables and be at least 32 characters long."
    );
  }

  return {
    cookieName: COOKIE_NAME,
    password,
    ttl: SESSION_TTL,
    cookieOptions: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      path: "/",
    },
  };
}

/**
 * Get the current admin session from request cookies.
 * Use in Server Components and API Route handlers.
 */
export async function getSession(): Promise<IronSession<SessionData>> {
  const cookieStore = await cookies();
  return getIronSession<SessionData>(cookieStore, getSessionConfig());
}

/**
 * Check whether the current session has a logged-in admin.
 * Returns the session data if authenticated, null otherwise.
 */
export async function getAdmin(): Promise<SessionData | null> {
  try {
    const session = await getSession();
    if (session.isLoggedIn && session.adminId) {
      return {
        adminId: session.adminId,
        username: session.username,
        isLoggedIn: true,
      };
    }
  } catch {
    // If SESSION_SECRET is missing, treat as unauthenticated
  }
  return null;
}
