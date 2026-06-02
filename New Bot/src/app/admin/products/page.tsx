"use client";

// src/app/admin/products/page.tsx
// Products management page — table + create/edit modal.

import { useState, useEffect, useCallback } from "react";
import ProductForm, { type ProductFormData } from "@/components/ProductForm";

interface Product {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price: string;
  compareAtPrice: string | null;
  categoryId: string;
  deliveryMode: string;
  isVisible: boolean;
  isOutOfStock: boolean;
  providerId: string | null;
  providerProductCode: string | null;
  minQty: number;
  maxQty: number;
  category: { id: string; name: string; slug: string } | null;
  provider: { id: string; name: string; code: string } | null;
  availableStock: number;
  createdAt: string;
}

interface Category {
  id: string;
  name: string;
}

interface ProviderOption {
  id: string;
  name: string;
  code: string;
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState<ProductFormData | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    try {
      const [prodRes, provRes] = await Promise.all([
        fetch("/api/admin/products"),
        fetch("/api/admin/providers"),
      ]);

      if (!prodRes.ok) throw new Error("Failed to load products");
      const prodData = await prodRes.json();
      setProducts(prodData.products || []);

      // Extract unique categories from products
      const catMap = new Map<string, Category>();
      for (const p of prodData.products || []) {
        if (p.category) catMap.set(p.category.id, p.category);
      }
      setCategories(Array.from(catMap.values()));

      // Load providers for the form dropdown
      if (provRes.ok) {
        const provData = await provRes.json();
        setProviders(
          (provData.providers || [])
            .filter((p: ProviderOption & { isEnabled: boolean }) => p.isEnabled)
            .map((p: ProviderOption) => ({ id: p.id, name: p.name, code: p.code }))
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load products");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  function handleCreate() {
    setEditingProduct(null);
    setShowForm(true);
  }

  function handleEdit(product: Product) {
    setEditingProduct({
      id: product.id,
      name: product.name,
      description: product.description || "",
      price: product.price,
      compareAtPrice: product.compareAtPrice || "",
      deliveryMode: product.deliveryMode,
      categoryId: product.categoryId,
      providerId: product.providerId || "",
      providerProductCode: product.providerProductCode || "",
      minQty: product.minQty,
      maxQty: product.maxQty,
      isVisible: product.isVisible,
      isOutOfStock: product.isOutOfStock,
    });
    setShowForm(true);
  }

  async function handleSave(formData: ProductFormData): Promise<{ error?: string }> {
    const isEditing = !!formData.id;
    const url = isEditing
      ? `/api/admin/products/${formData.id}`
      : "/api/admin/products";

    const res = await fetch(url, {
      method: isEditing ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: formData.name,
        description: formData.description || null,
        price: formData.price,
        compareAtPrice: formData.compareAtPrice || null,
        deliveryMode: formData.deliveryMode,
        categoryId: formData.categoryId || undefined,
        providerId: formData.providerId || null,
        providerProductCode: formData.providerProductCode || null,
        minQty: formData.minQty,
        maxQty: formData.maxQty,
        isVisible: formData.isVisible,
        isOutOfStock: formData.isOutOfStock,
      }),
    });

    const data = await res.json();
    if (!res.ok) return { error: data.error || "Save failed" };

    setShowForm(false);
    setEditingProduct(null);
    await fetchProducts();
    return {};
  }

  async function handleToggle(
    productId: string,
    field: "isVisible" | "isOutOfStock",
    currentValue: boolean
  ) {
    setTogglingId(productId);
    try {
      const res = await fetch(`/api/admin/products/${productId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: !currentValue }),
      });
      if (res.ok) {
        setProducts((prev) =>
          prev.map((p) =>
            p.id === productId ? { ...p, [field]: !currentValue } : p
          )
        );
      }
    } finally {
      setTogglingId(null);
    }
  }

  async function handleSoftDelete(productId: string) {
    if (!confirm("Hide this product? It will be set to invisible.")) return;

    const res = await fetch(`/api/admin/products/${productId}`, {
      method: "DELETE",
    });
    if (res.ok) {
      setProducts((prev) =>
        prev.map((p) =>
          p.id === productId ? { ...p, isVisible: false } : p
        )
      );
    }
  }

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-semibold text-white">Products</h1>
        <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900 p-8">
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="h-4 w-48 animate-pulse rounded bg-neutral-800" />
                <div className="h-4 w-16 animate-pulse rounded bg-neutral-800" />
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
          <h1 className="text-2xl font-semibold text-white">Products</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {products.length} product{products.length !== 1 ? "s" : ""}
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
          New Product
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-lg bg-red-900/30 border border-red-800/50 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Products table */}
      <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900 overflow-hidden">
        {products.length === 0 ? (
          <div className="px-8 py-12 text-center">
            <p className="text-neutral-500">No products yet.</p>
            <button
              onClick={handleCreate}
              className="mt-3 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              Create your first product →
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800 text-left">
                  <th className="px-4 py-3 font-medium text-neutral-400">Product</th>
                  <th className="px-4 py-3 font-medium text-neutral-400">Price</th>
                  <th className="px-4 py-3 font-medium text-neutral-400">Mode</th>
                  <th className="px-4 py-3 font-medium text-neutral-400">Category</th>
                  <th className="px-4 py-3 font-medium text-neutral-400 text-center">Visible</th>
                  <th className="px-4 py-3 font-medium text-neutral-400 text-center">Stock</th>
                  <th className="px-4 py-3 font-medium text-neutral-400 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800/50">
                {products.map((product) => (
                  <tr
                    key={product.id}
                    className="group hover:bg-neutral-800/30 transition-colors"
                  >
                    {/* Name + slug */}
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-neutral-200">{product.name}</p>
                        <p className="text-xs text-neutral-600 mt-0.5">/{product.slug}</p>
                      </div>
                    </td>

                    {/* Price */}
                    <td className="px-4 py-3">
                      <div>
                        <span className="text-neutral-200 font-mono">
                          ${product.price}
                        </span>
                        {product.compareAtPrice && (
                          <span className="ml-2 text-xs text-neutral-600 line-through font-mono">
                            ${product.compareAtPrice}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Delivery mode */}
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          product.deliveryMode === "api"
                            ? "bg-blue-900/30 text-blue-400"
                            : "bg-amber-900/30 text-amber-400"
                        }`}
                      >
                        {product.deliveryMode}
                      </span>
                    </td>

                    {/* Category */}
                    <td className="px-4 py-3 text-neutral-400">
                      {product.category?.name || "—"}
                    </td>

                    {/* Visible toggle */}
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggle(product.id, "isVisible", product.isVisible)}
                        disabled={togglingId === product.id}
                        className="inline-flex items-center justify-center disabled:opacity-50"
                        title={product.isVisible ? "Click to hide" : "Click to show"}
                      >
                        <span
                          className={`inline-block h-5 w-9 rounded-full transition-colors relative ${
                            product.isVisible ? "bg-emerald-600" : "bg-neutral-700"
                          }`}
                        >
                          <span
                            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                              product.isVisible ? "left-[18px]" : "left-0.5"
                            }`}
                          />
                        </span>
                      </button>
                    </td>

                    {/* Stock status */}
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggle(product.id, "isOutOfStock", product.isOutOfStock)}
                        disabled={togglingId === product.id}
                        className="disabled:opacity-50"
                        title={product.isOutOfStock ? "Mark as in stock" : "Mark as out of stock"}
                      >
                        {product.isOutOfStock ? (
                          <span className="inline-flex items-center rounded-full bg-red-900/30 px-2 py-0.5 text-xs font-medium text-red-400">
                            Out
                          </span>
                        ) : product.deliveryMode === "manual" ? (
                          <span className="inline-flex items-center rounded-full bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-400">
                            {product.availableStock}
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-emerald-900/30 px-2 py-0.5 text-xs font-medium text-emerald-400">
                            API
                          </span>
                        )}
                      </button>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleEdit(product)}
                          className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-800 hover:text-neutral-300 transition-colors"
                          title="Edit"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                            <path d="m5.433 13.917 1.262-3.155A4 4 0 0 1 7.58 9.42l6.92-6.918a2.121 2.121 0 0 1 3 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 0 1-.65-.65Z" />
                            <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0 0 10 3H4.75A2.75 2.75 0 0 0 2 5.75v9.5A2.75 2.75 0 0 0 4.75 18h9.5A2.75 2.75 0 0 0 17 15.25V10a.75.75 0 0 0-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5Z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleSoftDelete(product.id)}
                          className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-800 hover:text-red-400 transition-colors"
                          title="Hide (soft-delete)"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                            <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022.841 10.518A2.75 2.75 0 0 0 7.596 19h4.807a2.75 2.75 0 0 0 2.742-2.53l.841-10.52.149.023a.75.75 0 0 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z" clipRule="evenodd" />
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
        <ProductForm
          product={editingProduct}
          categories={categories}
          providers={providers}
          onSave={handleSave}
          onClose={() => {
            setShowForm(false);
            setEditingProduct(null);
          }}
        />
      )}
    </div>
  );
}
