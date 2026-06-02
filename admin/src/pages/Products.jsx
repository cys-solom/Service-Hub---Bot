import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Eye, EyeOff, PauseCircle, PlayCircle, ChevronUp, ChevronDown, GripVertical, Save, AlertTriangle } from 'lucide-react';
import api from '../services/api';

export default function Products() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [reorderMode, setReorderMode] = useState(false);
  const [reorderList, setReorderList] = useState([]);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);
  const [form, setForm] = useState({
    name: '', slug: '', description: '', category_id: '', stock_type: 'code',
    delivery_mode: 'auto', is_visible: true, force_out_of_stock: false,
    min_qty: 1, max_qty: 100, reply_template: '',
    prices: [{ currency: 'USD', price: 0 }],
    meta: { delivery_type: 'stock', emoji: '📦', api_config: { url: '', method: 'POST', headers: {}, body: {}, success_key: 'status', success_value: 'success', result_key: '' }, input_label_en: '📧 Enter your email address for activation:', input_label_ar: '📧 أدخل بريدك الإلكتروني للتفعيل:' },
  });

  const apiCfg = (f) => (f.meta?.api_config || {});
  const setApiCfg = (key, val) => setForm(f => ({ ...f, meta: { ...f.meta, api_config: { ...apiCfg(f), [key]: val } } }));
  const setMeta  = (key, val) => setForm(f => ({ ...f, meta: { ...f.meta, [key]: val } }));
  const isApiProduct = (form.meta?.delivery_type || 'stock') === 'api';

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = async () => {
    try {
      const [p, c] = await Promise.all([api.getProducts(), api.getCategories()]);
      setProducts(p.products || []); setCategories(c.categories || []); setLoading(false);
    } catch(e) { showToast('Failed to load', 'error'); setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (modal === 'edit') await api.updateProduct(form.id, form);
      else await api.createProduct(form);
      setModal(null); load();
      showToast(modal === 'edit' ? 'Product updated!' : 'Product created!');
    } catch (e) { showToast(e.message, 'error'); }
    setSaving(false);
  };

  const [confirmDel, setConfirmDel] = useState(null);

  const handleDelete = async (id) => {
    if (confirmDel !== id) { setConfirmDel(id); return; }
    try {
      await api.deleteProduct(id); load();
      showToast('Product deleted');
    } catch (e) { showToast(e.message, 'error'); }
    setConfirmDel(null);
  };

  const toggleStock = async (p) => {
    try {
      await api.updateProduct(p.id, { ...p, force_out_of_stock: !p.force_out_of_stock });
      load();
      showToast(p.force_out_of_stock ? 'Sales resumed' : 'Sales paused');
    } catch (e) { showToast(e.message, 'error'); }
  };

  const toggleVisibility = async (p) => {
    try {
      await api.updateProduct(p.id, { ...p, is_visible: !p.is_visible });
      load();
      showToast(p.is_visible ? 'Product hidden from users' : 'Product visible to users');
    } catch (e) { showToast(e.message, 'error'); }
  };

  // Reorder
  const startReorder = () => {
    setReorderList([...products]);
    setReorderMode(true);
  };
  const moveProduct = (index, direction) => {
    const newList = [...reorderList];
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= newList.length) return;
    [newList[index], newList[newIndex]] = [newList[newIndex], newList[index]];
    setReorderList(newList);
  };
  const saveReorder = async () => {
    setSaving(true);
    try {
      const items = reorderList.map((p, i) => ({ id: p.id, sort_order: i }));
      await api.reorderProducts(items);
      setReorderMode(false);
      load();
      showToast('Order saved!');
    } catch(e) { showToast(e.message, 'error'); }
    setSaving(false);
  };

  const openCreate = () => {
    setForm({
      name: '', slug: '', description: '', category_id: categories[0]?.id || '',
      stock_type: 'code', delivery_mode: 'auto', is_visible: true, force_out_of_stock: false,
      min_qty: 1, max_qty: 100, reply_template: '', prices: [{ currency: 'USD', price: 0 }],
      meta: {
        delivery_type: 'stock', emoji: '📦',
        api_config: { api_provider: '', org_id: '', client_id: '', client_secret: '', url: '', method: 'POST', headers: {}, body: {}, success_key: 'status', success_value: 'success', result_key: '' },
        input_label_en: '📧 Enter your email address for activation:',
        input_label_ar: '📧 أدخل بريدك الإلكتروني للتفعيل:',
      },
    });
    setModal('create');
  };

  const openEdit = (p) => {
    const defaultMeta = {
      delivery_type: 'stock', emoji: '📦',
      api_config: { api_provider: '', org_id: '', client_id: '', client_secret: '', url: '', method: 'POST', headers: {}, body: {}, success_key: 'status', success_value: 'success', result_key: '' },
      input_label_en: '📧 Enter your email address for activation:',
      input_label_ar: '📧 أدخل بريدك الإلكتروني للتفعيل:',
    };
    const merged = { ...defaultMeta, ...(p.meta || {}), api_config: { ...defaultMeta.api_config, ...(p.meta?.api_config || {}) } };
    // Strip qty_presets from non-API products
    if (merged.delivery_type !== 'api') {
      delete merged.qty_presets;
      delete merged.qty_labels;
    }
    setForm({
      ...p,
      prices: p.prices?.length ? p.prices : [{ currency: 'USD', price: 0 }],
      meta: merged,
    });
    setModal('edit');
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  const displayList = reorderMode ? reorderList : products;

  return (
    <div>
      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 9999, padding: '12px 20px', borderRadius: 10,
          background: toast.type === 'error' ? 'var(--danger)' : 'var(--success)',
          color: '#fff', fontWeight: 600, fontSize: 13, boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          animation: 'fadeIn 0.2s ease',
        }}>{toast.msg}</div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: 4 }}>Products</h1>
          <p className="page-subtitle">{products.length} products · Manage your store catalog</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {reorderMode ? (
            <>
              <button className="btn btn-secondary" onClick={() => setReorderMode(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={saveReorder} disabled={saving}>
                <Save size={14} /> {saving ? 'Saving...' : 'Save Order'}
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-secondary" onClick={startReorder}>
                <GripVertical size={14} /> Reorder
              </button>
              <button className="btn btn-primary" onClick={openCreate}>
                <Plus size={16} /> Add Product
              </button>
            </>
          )}
        </div>
      </div>

      {reorderMode && (
        <div style={{
          padding: '10px 16px', background: 'var(--accent-bg)', border: '1px solid var(--accent)',
          borderRadius: 8, marginBottom: 16, fontSize: 13, color: 'var(--accent)',
        }}>
          ↕️ Use the arrows to reorder products. Click <b>Save Order</b> when done.
        </div>
      )}

      {/* Product Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {displayList.map((p, index) => {
          const isAPI = p.meta?.delivery_type === 'api';
          const stockBadge = p.force_out_of_stock ? { text: '⏸ Paused', cls: 'badge-danger' }
            : isAPI ? { text: '∞ API', cls: 'badge-info' }
            : p.stock_available > 5 ? { text: `${p.stock_available} in stock`, cls: 'badge-success' }
            : p.stock_available > 0 ? { text: `${p.stock_available} left`, cls: 'badge-warning' }
            : { text: 'Out of stock', cls: 'badge-danger' };

          return (
            <div key={p.id} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '14px 18px', borderRadius: 12,
              border: '1px solid var(--border)', background: 'var(--bg-card)',
              transition: 'all 0.15s ease',
            }}>
              {/* Reorder arrows */}
              {reorderMode && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <button onClick={() => moveProduct(index, -1)} disabled={index === 0}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: index === 0 ? 'var(--border)' : 'var(--text-muted)', padding: 2 }}>
                    <ChevronUp size={18} />
                  </button>
                  <button onClick={() => moveProduct(index, 1)} disabled={index === displayList.length - 1}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: index === displayList.length - 1 ? 'var(--border)' : 'var(--text-muted)', padding: 2 }}>
                    <ChevronDown size={18} />
                  </button>
                </div>
              )}

              {/* Order number */}
              <div style={{
                width: 32, height: 32, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--accent-bg)', color: 'var(--accent)', fontWeight: 700, fontSize: 13, flexShrink: 0,
              }}>{index + 1}</div>

              {/* Emoji */}
              <div style={{ fontSize: 24, flexShrink: 0 }}>{p.meta?.emoji || '📦'}</div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 700, fontSize: 15 }}>{p.name}</span>
                  {!p.is_visible && <span className="badge badge-neutral" style={{ fontSize: 10 }}>Hidden</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <span style={{ fontWeight: 700, color: 'var(--accent)' }}>${p.prices?.[0]?.price || 0}</span>
                  <span className={`badge ${stockBadge.cls}`} style={{ fontSize: 11 }}>{stockBadge.text}</span>
                  <span className={`badge ${isAPI ? 'badge-info' : 'badge-neutral'}`} style={{ fontSize: 11 }}>
                    {isAPI ? '🔌 API' : `📦 ${p.stock_type}`}
                  </span>
                </div>
              </div>

              {/* Actions */}
              {!reorderMode && (
                <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
                  <button
                    className={`btn btn-sm ${p.is_visible ? 'btn-secondary' : 'btn-warning'}`}
                    onClick={() => toggleVisibility(p)}
                    title={p.is_visible ? 'Hide from users' : 'Show to users'}
                    style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                  >
                    {p.is_visible ? <Eye size={13} /> : <><EyeOff size={13} /> Hidden</>}
                  </button>
                  <button
                    className={`btn btn-sm ${p.force_out_of_stock ? 'btn-danger' : 'btn-secondary'}`}
                    onClick={() => toggleStock(p)}
                    title={p.force_out_of_stock ? 'Resume Sales' : 'Pause Sales'}
                    style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}
                  >
                    {p.force_out_of_stock ? <><PlayCircle size={13} /> Resume</> : <><PauseCircle size={13} /> Pause</>}
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => openEdit(p)}>
                    <Edit2 size={13} />
                  </button>
                  <button
                    className={`btn btn-sm btn-danger`}
                    onClick={() => handleDelete(p.id)}
                    onMouseLeave={() => confirmDel === p.id && setTimeout(() => setConfirmDel(null), 2000)}
                    title={confirmDel === p.id ? 'Click again to confirm' : 'Delete'}
                    style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12,
                      ...(confirmDel === p.id ? { background: '#dc2626' } : {}) }}
                  >
                    {confirmDel === p.id ? <><AlertTriangle size={13} /> Sure?</> : <Trash2 size={13} />}
                  </button>
                </div>
              )}
            </div>
          );
        })}
        {products.length === 0 && (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📦</div>
            <h3>No products yet</h3>
            <p>Click "Add Product" to create your first product</p>
          </div>
        )}
      </div>

      {/* Product Modal */}
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 580 }}>
            <h2 className="modal-title">{modal === 'edit' ? '✏️ Edit Product' : '➕ New Product'}</h2>
            <div className="grid-2">
              <div className="input-group">
                <label className="input-label">Name</label>
                <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="input-group">
                <label className="input-label">Emoji</label>
                <input className="input" value={form.meta?.emoji || '📦'}
                  onChange={e => setMeta('emoji', e.target.value)}
                  placeholder="📦" style={{ width: 70, textAlign: 'center', fontSize: 20 }} />
              </div>
            </div>
            <div className="input-group">
              <label className="input-label">Description</label>
              <textarea className="textarea" value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="grid-3">
              <div className="input-group">
                <label className="input-label">Price (USD)</label>
                <input className="input" type="number" step="0.01" value={form.prices?.[0]?.price || 0}
                  onChange={e => setForm({ ...form, prices: [{ currency: 'USD', price: parseFloat(e.target.value) }] })} />
              </div>
              <div className="input-group">
                <label className="input-label">Stock Type</label>
                <select className="select" value={form.stock_type} onChange={e => setForm({ ...form, stock_type: e.target.value })}>
                  <option value="code">Code</option>
                  <option value="email_pass">Email:Password</option>
                  <option value="email_pass_2fa">Email:Pass:2FA</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div className="input-group">
                <label className="input-label">Delivery</label>
                <select className="select" value={form.delivery_mode} onChange={e => setForm({ ...form, delivery_mode: e.target.value })}>
                  <option value="auto">Auto</option>
                  <option value="manual">Manual</option>
                  <option value="semi_auto">Semi-Auto</option>
                </select>
              </div>
            </div>
            <div className="grid-2" style={{ marginTop: 8 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '8px 0' }}>
                <input type="checkbox" checked={form.force_out_of_stock || false}
                  onChange={e => setForm({ ...form, force_out_of_stock: e.target.checked })}
                  style={{ width: 18, height: 18, accentColor: 'var(--danger)' }} />
                <span style={{ fontWeight: 600, color: form.force_out_of_stock ? 'var(--danger)' : 'var(--text)' }}>
                  {form.force_out_of_stock ? '⏸ Force Out of Stock (Sales Paused)' : '▶ Sales Active'}
                </span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '8px 0' }}>
                <input type="checkbox" checked={form.is_visible !== false}
                  onChange={e => setForm({ ...form, is_visible: e.target.checked })}
                  style={{ width: 18, height: 18, accentColor: 'var(--primary)' }} />
                <span style={{ fontWeight: 600 }}>
                  {form.is_visible !== false ? '👁 Visible to Users' : '🚫 Hidden'}
                </span>
              </label>
              {/* Unlimited toggle — only for non-API products */}
              {!isApiProduct && (
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '8px 0' }}>
                  <input type="checkbox" checked={form.meta?.unlimited === true}
                    onChange={e => setMeta('unlimited', e.target.checked)}
                    style={{ width: 18, height: 18, accentColor: 'var(--success)' }} />
                  <span style={{ fontWeight: 600, color: form.meta?.unlimited ? 'var(--success)' : 'inherit' }}>
                    {form.meta?.unlimited ? '∞ Unlimited Stock (no inventory needed)' : '📦 Limited Stock (use inventory)'}
                  </span>
                </label>
              )}
            </div>
            <div className="input-group">
              <label className="input-label">Reply Template (after purchase)</label>
              <textarea className="textarea" value={form.reply_template || ''} onChange={e => setForm({ ...form, reply_template: e.target.value })}
                placeholder="Use {delivery_data} for stock content" />
            </div>

            {/* ── Delivery Type ── */}
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16, marginTop: 8 }}>
              <label className="input-label" style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12, display: 'block' }}>🚀 Delivery Type</label>
              <div className="grid-2">
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '10px 14px', border: `2px solid ${!isApiProduct ? 'var(--accent)' : 'var(--border)'}`, borderRadius: 8, background: !isApiProduct ? 'var(--accent-bg)' : 'transparent' }}>
                  <input type="radio" name="delivery_type" value="stock" checked={!isApiProduct}
                    onChange={() => setMeta('delivery_type', 'stock')} />
                  <div><div style={{ fontWeight: 600 }}>📦 Stock Delivery</div><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Deliver pre-loaded stock items</div></div>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', padding: '10px 14px', border: `2px solid ${isApiProduct ? 'var(--accent)' : 'var(--border)'}`, borderRadius: 8, background: isApiProduct ? 'var(--accent-bg)' : 'transparent' }}>
                  <input type="radio" name="delivery_type" value="api" checked={isApiProduct}
                    onChange={() => setMeta('delivery_type', 'api')} />
                  <div><div style={{ fontWeight: 600 }}>🔌 API Delivery</div><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Call external API (e.g. Adobe)</div></div>
                </label>
              </div>
            </div>

            {/* ── API Config (shown only for API products) ── */}
            {isApiProduct && (
              <div style={{ background: 'var(--bg-card-hover)', borderRadius: 10, padding: 16, border: '1px solid var(--border)', marginTop: 8 }}>
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12, color: 'var(--accent)' }}>🔌 API Configuration</div>

                {/* Provider selector */}
                <div className="input-group">
                  <label className="input-label">API Provider</label>
                  <select className="select" value={apiCfg(form).api_provider || ''} onChange={e => setApiCfg('api_provider', e.target.value)}>
                    <option value="">Generic HTTP API</option>
                    <option value="adobe">🎨 Adobe Creative Cloud</option>
                  </select>
                </div>

                {/* Adobe credentials */}
                {apiCfg(form).api_provider === 'adobe' && (
                  <div style={{ background: 'var(--bg-card)', borderRadius: 8, padding: 12, marginBottom: 12, border: '1px solid var(--accent)' }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', marginBottom: 10 }}>🎨 Adobe I/O Credentials</div>
                    <div className="grid-2">
                      <div className="input-group">
                        <label className="input-label">Organization ID</label>
                        <input className="input" value={apiCfg(form).org_id || ''}
                          onChange={e => setApiCfg('org_id', e.target.value)}
                          placeholder="XXXXXX@AdobeOrg" />
                      </div>
                      <div className="input-group">
                        <label className="input-label">Client ID / API Key</label>
                        <input className="input" value={apiCfg(form).client_id || ''}
                          onChange={e => setApiCfg('client_id', e.target.value)}
                          placeholder="de6266fdac3b..." />
                      </div>
                    </div>
                    <div className="input-group">
                      <label className="input-label">Client Secret</label>
                      <input className="input" type="password" value={apiCfg(form).client_secret || ''}
                        onChange={e => setApiCfg('client_secret', e.target.value)}
                        placeholder="p8e-87loOAY..." />
                    </div>
                  </div>
                )}

                {/* Generic HTTP (shown when not adobe) */}
                {!apiCfg(form).api_provider && (
                <div className="grid-2">
                  <div className="input-group">
                    <label className="input-label">API URL *</label>
                    <input className="input" value={apiCfg(form).url || ''}
                      onChange={e => setApiCfg('url', e.target.value)}
                      placeholder="https://api.example.com/activate" />
                  </div>
                  <div className="input-group">
                    <label className="input-label">Method</label>
                    <select className="select" value={apiCfg(form).method || 'POST'} onChange={e => setApiCfg('method', e.target.value)}>
                      <option value="POST">POST</option>
                      <option value="GET">GET</option>
                      <option value="PUT">PUT</option>
                    </select>
                  </div>
                </div>
                )}

                <div className="input-group">
                  <label className="input-label">Request Body (JSON) — use <code>{'{email}'}</code> and <code>{'{order_id}'}</code></label>
                  <textarea className="textarea" rows={3}
                    value={typeof apiCfg(form).body === 'object' ? JSON.stringify(apiCfg(form).body, null, 2) : (apiCfg(form).body || '')}
                    onChange={e => { try { setApiCfg('body', JSON.parse(e.target.value)); } catch { setApiCfg('body', e.target.value); } }}
                    placeholder={'{"email": "{email}", "product": "adobe_cc"}'} />
                </div>

                <div className="input-group">
                  <label className="input-label">Headers (JSON) — e.g. Authorization</label>
                  <textarea className="textarea" rows={2}
                    value={typeof apiCfg(form).headers === 'object' ? JSON.stringify(apiCfg(form).headers, null, 2) : (apiCfg(form).headers || '')}
                    onChange={e => { try { setApiCfg('headers', JSON.parse(e.target.value)); } catch { setApiCfg('headers', e.target.value); } }}
                    placeholder={'{"Authorization": "Bearer YOUR_API_KEY"}'} />
                </div>

                <div className="grid-3">
                  <div className="input-group">
                    <label className="input-label">Success Key</label>
                    <input className="input" value={apiCfg(form).success_key || 'status'}
                      onChange={e => setApiCfg('success_key', e.target.value)} placeholder="status" />
                    <small style={{ color: 'var(--text-muted)', fontSize: 11 }}>JSON key to check</small>
                  </div>
                  <div className="input-group">
                    <label className="input-label">Success Value</label>
                    <input className="input" value={apiCfg(form).success_value || 'success'}
                      onChange={e => setApiCfg('success_value', e.target.value)} placeholder="success" />
                    <small style={{ color: 'var(--text-muted)', fontSize: 11 }}>Expected value</small>
                  </div>
                  <div className="input-group">
                    <label className="input-label">Result Key (optional)</label>
                    <input className="input" value={apiCfg(form).result_key || ''}
                      onChange={e => setApiCfg('result_key', e.target.value)} placeholder="message" />
                    <small style={{ color: 'var(--text-muted)', fontSize: 11 }}>Key to show customer</small>
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, marginTop: 4 }}>
                  <label className="input-label" style={{ marginBottom: 8, display: 'block' }}>📧 Email prompt shown to customer</label>
                  <div className="grid-2">
                    <div className="input-group">
                      <label className="input-label">EN Label</label>
                      <input className="input" value={form.meta?.input_label_en || ''}
                        onChange={e => setMeta('input_label_en', e.target.value)}
                        placeholder="📧 Enter your Adobe email:" />
                    </div>
                    <div className="input-group">
                      <label className="input-label">AR Label</label>
                      <input className="input" value={form.meta?.input_label_ar || ''}
                        onChange={e => setMeta('input_label_ar', e.target.value)}
                        placeholder="📧 أدخل بريدك الإلكتروني:" />
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
