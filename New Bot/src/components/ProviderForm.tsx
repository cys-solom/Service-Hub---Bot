"use client";

// src/components/ProviderForm.tsx
// Create/edit provider modal. No secret fields (apiKey/apiSecret).

import { useState, useEffect, type FormEvent } from "react";

export interface ProviderFormData {
  id?: string;
  name: string;
  code: string;
  apiUrl: string;
  isEnabled: boolean;
  config: string; // JSON string for editing
}

const EMPTY_FORM: ProviderFormData = {
  name: "",
  code: "",
  apiUrl: "",
  isEnabled: true,
  config: "",
};

interface ProviderFormProps {
  provider?: ProviderFormData | null;
  onSave: (data: ProviderFormData) => Promise<{ error?: string }>;
  onClose: () => void;
}

export default function ProviderForm({
  provider,
  onSave,
  onClose,
}: ProviderFormProps) {
  const isEditing = !!provider?.id;
  const [form, setForm] = useState<ProviderFormData>(provider || EMPTY_FORM);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setForm(provider || EMPTY_FORM);
    setError("");
  }, [provider]);

  function updateField<K extends keyof ProviderFormData>(
    key: K,
    value: ProviderFormData[K]
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // Auto-generate code from name (only when creating)
  function handleNameChange(value: string) {
    updateField("name", value);
    if (!isEditing) {
      const autoCode = value
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_|_$/g, "");
      updateField("code", autoCode);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    // Validate config JSON if provided
    if (form.config.trim()) {
      try {
        JSON.parse(form.config);
      } catch {
        setError("Config must be valid JSON");
        return;
      }
    }

    setIsSaving(true);
    const result = await onSave(form);
    setIsSaving(false);

    if (result.error) {
      setError(result.error);
    }
  }

  // Derive expected env var names from code
  const envPrefix = form.code
    ? `PROVIDER_${form.code.toUpperCase()}`
    : "PROVIDER_<CODE>";

  const inputClass =
    "w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3.5 py-2 text-sm text-white " +
    "placeholder:text-neutral-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition-colors";

  const labelClass = "mb-1.5 block text-xs font-medium text-neutral-400";

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 backdrop-blur-sm p-4 pt-16">
      <div className="w-full max-w-lg rounded-xl border border-neutral-800 bg-neutral-900 shadow-2xl shadow-black/50">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">
            {isEditing ? "Edit Provider" : "New Provider"}
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Name */}
          <div>
            <label htmlFor="pvf-name" className={labelClass}>Provider Name *</label>
            <input
              id="pvf-name"
              type="text"
              value={form.name}
              onChange={(e) => handleNameChange(e.target.value)}
              required
              placeholder="VEX Reseller API"
              className={inputClass}
            />
          </div>

          {/* Code */}
          <div>
            <label htmlFor="pvf-code" className={labelClass}>
              Provider Code * {isEditing && <span className="text-neutral-600">(read-only)</span>}
            </label>
            <input
              id="pvf-code"
              type="text"
              value={form.code}
              onChange={(e) => updateField("code", e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
              required
              readOnly={isEditing}
              placeholder="vex_reseller"
              className={`${inputClass} font-mono ${isEditing ? "opacity-60 cursor-not-allowed" : ""}`}
            />
            <p className="mt-1 text-xs text-neutral-600">
              Lowercase, alphanumeric + underscores. Used for env var mapping.
            </p>
          </div>

          {/* API URL */}
          <div>
            <label htmlFor="pvf-url" className={labelClass}>API Base URL *</label>
            <input
              id="pvf-url"
              type="url"
              value={form.apiUrl}
              onChange={(e) => updateField("apiUrl", e.target.value)}
              required
              placeholder="https://api.example.com/v1"
              className={inputClass + " font-mono"}
            />
          </div>

          {/* Env var hint */}
          <div className="rounded-lg border border-neutral-800 bg-neutral-800/30 p-4">
            <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-2">
              Environment Variables (set in .env, NOT stored in DB)
            </p>
            <div className="space-y-1 font-mono text-xs">
              <p className="text-amber-400/80">
                {envPrefix}_API_KEY=<span className="text-neutral-600">"your-api-key"</span>
              </p>
              <p className="text-amber-400/80">
                {envPrefix}_API_SECRET=<span className="text-neutral-600">"your-api-secret"</span>
              </p>
              <p className="text-amber-400/80">
                {envPrefix}_API_BASE_URL=<span className="text-neutral-600">"base-url"</span>
              </p>
            </div>
            <p className="mt-2 text-xs text-neutral-600">
              These credentials must be configured in your deployment environment, not in the admin panel.
            </p>
          </div>

          {/* Config (non-secret JSON) */}
          <div>
            <label htmlFor="pvf-config" className={labelClass}>Config (non-secret JSON, optional)</label>
            <textarea
              id="pvf-config"
              value={form.config}
              onChange={(e) => updateField("config", e.target.value)}
              rows={3}
              placeholder='{"rate_limit": 60, "timeout_ms": 5000}'
              className={inputClass + " resize-none font-mono text-xs"}
            />
          </div>

          {/* Enabled toggle */}
          <label className="flex items-center gap-2 cursor-pointer pt-1">
            <input
              type="checkbox"
              checked={form.isEnabled}
              onChange={(e) => updateField("isEnabled", e.target.checked)}
              className="h-4 w-4 rounded border-neutral-600 bg-neutral-800 text-indigo-500 focus:ring-indigo-500/50"
            />
            <span className="text-sm text-neutral-300">Enabled</span>
          </label>

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-red-900/30 border border-red-800/50 px-3.5 py-2.5 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-neutral-400 hover:bg-neutral-800 hover:text-neutral-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white transition-all
                hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              {isSaving ? "Saving…" : isEditing ? "Update Provider" : "Create Provider"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
