"use client";

// src/app/admin/providers/page.tsx
// Providers management page — table + create/edit modal.

import { useState, useEffect, useCallback } from "react";
import ProviderForm, { type ProviderFormData } from "@/components/ProviderForm";

interface Provider {
  id: string;
  name: string;
  code: string;
  apiUrl: string;
  isEnabled: boolean;
  config: Record<string, unknown> | null;
  lastSyncAt: string | null;
  productCount: number;
  createdAt: string;
  updatedAt: string;
}

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderFormData | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const fetchProviders = useCallback(async () => {
    try {
      const res = await fetch("/api/admin/providers");
      if (!res.ok) throw new Error("Failed to load providers");
      const data = await res.json();
      setProviders(data.providers || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load providers");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  function handleCreate() {
    setEditingProvider(null);
    setShowForm(true);
  }

  function handleEdit(provider: Provider) {
    setEditingProvider({
      id: provider.id,
      name: provider.name,
      code: provider.code,
      apiUrl: provider.apiUrl,
      isEnabled: provider.isEnabled,
      config: provider.config ? JSON.stringify(provider.config, null, 2) : "",
    });
    setShowForm(true);
  }

  async function handleSave(formData: ProviderFormData): Promise<{ error?: string }> {
    const isEditing = !!formData.id;
    const url = isEditing
      ? `/api/admin/providers/${formData.id}`
      : "/api/admin/providers";

    let config: Record<string, unknown> | null = null;
    if (formData.config.trim()) {
      try {
        config = JSON.parse(formData.config);
      } catch {
        return { error: "Config must be valid JSON" };
      }
    }

    const res = await fetch(url, {
      method: isEditing ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: formData.name,
        code: formData.code,
        apiUrl: formData.apiUrl,
        isEnabled: formData.isEnabled,
        config,
      }),
    });

    const data = await res.json();
    if (!res.ok) return { error: data.error || "Save failed" };

    setShowForm(false);
    setEditingProvider(null);
    await fetchProviders();
    return {};
  }

  async function handleToggle(providerId: string, currentValue: boolean) {
    setTogglingId(providerId);
    try {
      const res = await fetch(`/api/admin/providers/${providerId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isEnabled: !currentValue }),
      });
      if (res.ok) {
        setProviders((prev) =>
          prev.map((p) =>
            p.id === providerId ? { ...p, isEnabled: !currentValue } : p
          )
        );
      }
    } finally {
      setTogglingId(null);
    }
  }

  async function handleSoftDelete(providerId: string) {
    if (!confirm("Disable this provider? It will be marked as inactive.")) return;

    const res = await fetch(`/api/admin/providers/${providerId}`, {
      method: "DELETE",
    });
    if (res.ok) {
      setProviders((prev) =>
        prev.map((p) =>
          p.id === providerId ? { ...p, isEnabled: false } : p
        )
      );
    }
  }

  function formatDate(dateStr: string | null) {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-semibold text-white">Providers</h1>
        <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900 p-8">
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="h-4 w-32 animate-pulse rounded bg-neutral-800" />
                <div className="h-4 w-56 animate-pulse rounded bg-neutral-800" />
                <div className="h-4 w-20 animate-pulse rounded bg-neutral-800" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Providers</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {providers.length} provider{providers.length !== 1 ? "s" : ""} configured
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white
            transition-all hover:bg-indigo-500 active:scale-[0.98]"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
          </svg>
          New Provider
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-lg bg-red-900/30 border border-red-800/50 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Providers table */}
      <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900 overflow-hidden">
        {providers.length === 0 ? (
          <div className="px-8 py-12 text-center">
            <p className="text-neutral-500">No providers configured yet.</p>
            <button
              onClick={handleCreate}
              className="mt-3 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Add your first provider →
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800 text-left">
                  <th className="px-4 py-3 font-medium text-neutral-400">Provider</th>
                  <th className="px-4 py-3 font-medium text-neutral-400">Code</th>
                  <th className="px-4 py-3 font-medium text-neutral-400">API URL</th>
                  <th className="px-4 py-3 font-medium text-neutral-400 text-center">Enabled</th>
                  <th className="px-4 py-3 font-medium text-neutral-400 text-center">Products</th>
                  <th className="px-4 py-3 font-medium text-neutral-400">Last Sync</th>
                  <th className="px-4 py-3 font-medium text-neutral-400 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/50">
                {providers.map((provider) => (
                  <tr
                    key={provider.id}
                    className="group hover:bg-neutral-800/30 transition-colors"
                  >
                    {/* Name */}
                    <td className="px-4 py-3">
                      <p className="font-medium text-neutral-200">{provider.name}</p>
                    </td>

                    {/* Code */}
                    <td className="px-4 py-3">
                      <span className="rounded bg-neutral-800 px-2 py-0.5 font-mono text-xs text-neutral-400">
                        {provider.code}
                      </span>
                    </td>

                    {/* API URL */}
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-neutral-500 max-w-[200px] truncate block">
                        {provider.apiUrl}
                      </span>
                    </td>

                    {/* Enabled toggle */}
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggle(provider.id, provider.isEnabled)}
                        disabled={togglingId === provider.id}
                        className="inline-flex items-center justify-center disabled:opacity-50"
                        title={provider.isEnabled ? "Click to disable" : "Click to enable"}
                      >
                        <span
                          className={`inline-block h-5 w-9 rounded-full transition-colors relative ${
                            provider.isEnabled ? "bg-emerald-600" : "bg-neutral-700"
                          }`}
                        >
                          <span
                            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                              provider.isEnabled ? "left-[18px]" : "left-0.5"
                            }`}
                          />
                        </span>
                      </button>
                    </td>

                    {/* Products count */}
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center rounded-full bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-400">
                        {provider.productCount}
                      </span>
                    </td>

                    {/* Last sync */}
                    <td className="px-4 py-3">
                      <span className="text-xs text-neutral-500">
                        {formatDate(provider.lastSyncAt)}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleEdit(provider)}
                          className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300 transition-colors"
                          title="Edit"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                            <path d="m5.433 13.917 1.262-3.155A4 4 0 0 1 7.58 9.42l6.92-6.918a2.121 2.121 0 0 1 3 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 0 1-.65-.65Z" />
                            <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0 0 10 3H4.75A2.75 2.75 0 0 0 2 5.75v9.5A2.75 2.75 0 0 0 4.75 18h9.5A2.75 2.75 0 0 0 17 15.25V10a.75.75 0 0 0-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5Z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleSoftDelete(provider.id)}
                          className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-800 hover:text-red-400 transition-colors"
                          title="Disable provider"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                            <path fillRule="evenodd" d="M5.965 4.904a9.461 9.461 0 0 1 4.5-2.87.75.75 0 0 0-.43-1.44 10.96 10.96 0 0 0-5.21 3.33.75.75 0 0 0 1.14.98ZM3.043 8.86a.75.75 0 0 0-1.454-.37 10.96 10.96 0 0 0 .706 6.161.75.75 0 1 0 1.37-.612 9.461 9.461 0 0 1-.622-5.18ZM5.96 15.096a.75.75 0 1 0-1.14.984 10.96 10.96 0 0 0 5.212 3.33.75.75 0 1 0 .428-1.438 9.462 9.462 0 0 1-4.5-2.876ZM13.535 4.904a.75.75 0 0 0 1.14-.98 10.96 10.96 0 0 0-5.212-3.33.75.75 0 1 0-.428 1.438 9.462 9.462 0 0 1 4.5 2.872ZM16.958 8.86a9.461 9.461 0 0 1 .621 5.179.75.75 0 1 0 1.37.612 10.96 10.96 0 0 0-.706-6.162.75.75 0 0 0-1.285.37ZM14.04 15.096a9.462 9.462 0 0 1-4.5 2.876.75.75 0 0 0 .428 1.438 10.96 10.96 0 0 0 5.212-3.33.75.75 0 1 0-1.14-.984ZM7.5 10a2.5 2.5 0 1 1 5 0 2.5 2.5 0 0 1-5 0Z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create/Edit modal */}
      {showForm && (
        <ProviderForm
          provider={editingProvider}
          onSave={handleSave}
          onClose={() => {
            setShowForm(false);
            setEditingProvider(null);
          }}
        />
      )}
    </div>
  );
}
