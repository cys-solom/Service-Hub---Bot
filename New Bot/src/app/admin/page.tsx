// src/app/admin/page.tsx
// Redirect /admin → /admin/orders

import { redirect } from "next/navigation";

export default function AdminPage() {
  redirect("/admin/orders");
}
