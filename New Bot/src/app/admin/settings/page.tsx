// src/app/admin/settings/page.tsx
// Settings management — placeholder for Phase 2B.

export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Settings</h1>
      <p className="mt-2 text-sm text-neutral-500">
        Store settings editor will be built in the next phase.
      </p>

      <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900 p-8">
        <div className="space-y-5">
          {["Store Name", "Default Currency", "Payment Timeout", "Support Contact"].map(
            (label) => (
              <div key={label} className="flex items-center justify-between">
                <span className="text-sm text-neutral-400">{label}</span>
                <div className="h-4 w-40 animate-pulse rounded bg-neutral-800" />
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
