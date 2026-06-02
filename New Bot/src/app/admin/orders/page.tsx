// src/app/admin/orders/page.tsx
// Orders management — placeholder for Phase 2B.

export default function OrdersPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Orders</h1>
      <p className="mt-2 text-sm text-neutral-500">
        Order management will be built in the next phase.
      </p>

      {/* Placeholder skeleton */}
      <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900 p-8">
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4">
              <div className="h-4 w-24 animate-pulse rounded bg-neutral-800" />
              <div className="h-4 w-40 animate-pulse rounded bg-neutral-800" />
              <div className="h-4 w-20 animate-pulse rounded bg-neutral-800" />
              <div className="h-4 w-16 animate-pulse rounded bg-neutral-800" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
