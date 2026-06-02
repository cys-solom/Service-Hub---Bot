// src/app/admin/layout.tsx
// Admin panel layout — wraps all /admin/* pages with sidebar.
// Auth is enforced by middleware.ts, so we can safely read the session here.

import { getAdmin } from "@/lib/auth";
import AdminSidebar from "@/components/AdminSidebar";

export const metadata = {
  title: "Admin — Service Hub",
};

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const admin = await getAdmin();

  // If not logged in, render children only (login page handles its own layout)
  if (!admin) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-neutral-950">
      <AdminSidebar username={admin.username} />

      {/* Main content area — offset by sidebar width */}
      <main className="pl-60">
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex h-16 items-center border-b border-neutral-800 bg-neutral-950/80 px-8 backdrop-blur-sm">
          <div className="flex-1" />
          <div className="flex items-center gap-2 text-sm text-neutral-400">
            <div className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>{admin.username}</span>
          </div>
        </header>

        {/* Page content */}
        <div className="px-8 py-6">{children}</div>
      </main>
    </div>
  );
}
