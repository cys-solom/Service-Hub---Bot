"use client";

// src/app/admin/login/page.tsx
// Admin login page — standalone layout (no sidebar).

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/admin/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Login failed");
        setIsLoading(false);
        return;
      }

      // Redirect to admin orders page
      router.push("/admin/orders");
    } catch {
      setError("Network error. Please try again.");
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-950 p-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-lg font-bold text-white">
            SH
          </div>
          <h1 className="text-xl font-semibold text-white">Service Hub</h1>
          <p className="mt-1 text-sm text-neutral-500">Admin Panel</p>
        </div>

        {/* Login Form */}
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-neutral-800 bg-neutral-900 p-6 shadow-2xl shadow-black/40"
        >
          <div className="space-y-4">
            <div>
              <label
                htmlFor="login-username"
                className="mb-1.5 block text-xs font-medium text-neutral-400"
              >
                Username
              </label>
              <input
                id="login-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                placeholder="admin"
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3.5 py-2.5 text-sm text-white
                  placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50
                  transition-colors"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="mb-1.5 block text-xs font-medium text-neutral-400"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3.5 py-2.5 text-sm text-white
                  placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50
                  transition-colors"
              />
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mt-4 rounded-lg bg-red-900/30 border border-red-800/50 px-3.5 py-2.5 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="mt-5 w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white
              transition-all hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50
              disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Signing in…
              </span>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-neutral-600">
          Protected admin area
        </p>
      </div>
    </div>
  );
}
