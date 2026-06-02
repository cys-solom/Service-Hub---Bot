"use client";

// src/components/ProductForm.tsx
// Create/edit product modal. Shows provider fields only when deliveryMode === "api".

import { useState, useEffect, type FormEvent } from "react";

export interface ProductFormData {
  id?: string;
  name: string;
  description: string;
  price: string;
  compareAtPrice: string;
  deliveryMode: string;
  categoryId: string;
  providerId: string;
  providerProductCode: string;
  minQty: number;
  maxQty: number;
  isVisible: boolean;
  isOutOfStock: boolean;
}

interface Category {
  id: string;
  name: string;
}

interface Provider {
  id: string;
  name: string;
  code: string;
}

const EMPTY_FORM: ProductFormData = {
  name: "",
  description: "",
  price: "",
  compareAtPrice: "",
  deliveryMode: "api",
  categoryId: "",
  providerId: "",
  providerProductCode: "",
  minQty: 1,
  maxQty: 10,
  isVisible: true,
  isOutOfStock: false,
};

interface ProductFormProps {
  product?: ProductFormData | null;
  categories: Category[];
  providers: Provider[];
  onSave: (data: ProductFormData) => Promise<{ error?: string }>;
  onClose: () => void;
}

export default function ProductForm({
  product,
  categories,
  providers,
  onSave,
  onClose,
}: ProductFormProps) {
  const isEditing = !!product?.id;
  const [form, setForm] = useState<ProductFormData>(product || EMPTY_FORM);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setForm(product || EMPTY_FORM);
    setError("");
  }, [product]);

  function updateField<K extends keyof ProductFormData>(
    key: K,
    value: ProductFormData[K]
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setIsSaving(true);

    const result = await onSave(form);
    setIsSaving(false);

    if (result.error) {
      setError(result.error);
    }
  }

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
            {isEditing ? "Edit Product" : "New Product"}
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
            <label htmlFor="pf-name" className={labelClass}>Product Name *</label>
            <input
              id="pf-name"
              type="text"
              value={form.name}
              onChange={(e) => updateField("name", e.target.value)}
              required
              placeholder="Adobe Creative Cloud"
              className={inputClass}
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="pf-desc" className={labelClass}>Description</label>
            <textarea
              id="pf-desc"
              value={form.description}
              onChange={(e) => updateField("description", e.target.value)}
              rows={2}
              placeholder="Brief product description"
              className={inputClass + " resize-none"}
            />
          </div>

          {/* Price row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="pf-price" className={labelClass}>Price (USD) *</label>
              <input
                id="pf-price"
                type="text"
                inputMode="decimal"
                value={form.price}
                onChange={(e) => updateField("price", e.target.value)}
                required
                placeholder="12.99"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="pf-compare" className={labelClass}>Compare-at Price</label>
              <input
                id="pf-compare"
                type="text"
                inputMode="decimal"
                value={form.compareAtPrice}
                onChange={(e) => updateField("compareAtPrice", e.target.value)}
                placeholder="29.99"
                className={inputClass}
              />
            </div>
          </div>

          {/* Category + Delivery Mode */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="pf-cat" className={labelClass}>Category</label>
              <select
                id="pf-cat"
                value={form.categoryId}
                onChange={(e) => updateField("categoryId", e.target.value)}
                className={inputClass}
              >
                <option value="">Default (General)</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="pf-mode" className={labelClass}>Delivery Mode</label>
              <select
                id="pf-mode"
                value={form.deliveryMode}
                onChange={(e) => updateField("deliveryMode", e.target.value)}
                className={inputClass}
              >
                <option value="api">API (External Provider)</option>
                <option value="manual">Manual (Stock Items)</option>
              </select>
            </div>
          </div>

          {/* Provider fields — only shown for API delivery mode */}
          {form.deliveryMode === "api" && (
            <div className="rounded-lg border border-neutral-800 bg-neutral-800/30 p-4 space-y-3">
              <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider">
                Provider Configuration
              </p>
              <div>
                <label htmlFor="pf-provider" className={labelClass}>Provider</label>
                <select
                  id="pf-provider"
                  value={form.providerId}
                  onChange={(e) => updateField("providerId", e.target.value)}
                  className={inputClass}
                >
                  <option value="">None</option>
                  {providers.map((prov) => (
                    <option key={prov.id} value={prov.id}>
                      {prov.name} ({prov.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="pf-provcode" className={labelClass}>Provider Product Code</label>
                <input
                  id="pf-provcode"
                  type="text"
                  value={form.providerProductCode}
                  onChange={(e) => updateField("providerProductCode", e.target.value)}
                  placeholder="External product ID or SKU from provider"
                  className={inputClass + " font-mono"}
                />
              </div>
            </div>
          )}

          {/* Quantity limits */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="pf-minq" className={labelClass}>Min Quantity</label>
              <input
                id="pf-minq"
                type="number"
                min={1}
                value={form.minQty}
                onChange={(e) => updateField("minQty", parseInt(e.target.value) || 1)}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="pf-maxq" className={labelClass}>Max Quantity</label>
              <input
                id="pf-maxq"
                type="number"
                min={1}
                value={form.maxQty}
                onChange={(e) => updateField("maxQty", parseInt(e.target.value) || 10)}
                className={inputClass}
              />
            </div>
          </div>

          {/* Toggles */}
          <div className="flex items-center gap-6 pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.isVisible}
                onChange={(e) => updateField("isVisible", e.target.checked)}
                className="h-4 w-4 rounded border-neutral-600 bg-neutral-800 text-indigo-500 focus:ring-indigo-500/50"
              />
              <span className="text-sm text-neutral-300">Visible</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.isOutOfStock}
                onChange={(e) => updateField("isOutOfStock", e.target.checked)}
                className="h-4 w-4 rounded border-neutral-600 bg-neutral-800 text-orange-500 focus:ring-orange-500/50"
              />
              <span className="text-sm text-neutral-300">Out of Stock</span>
            </label>
          </div>

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
              {isSaving ? "Saving…" : isEditing ? "Update Product" : "Create Product"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
