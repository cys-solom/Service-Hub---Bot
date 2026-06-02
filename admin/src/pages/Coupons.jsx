import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Ticket as TicketIcon, Package, X } from 'lucide-react';
import api from '../services/api';

export default function Coupons() {
  const [coupons, setCoupons] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({
    code: '', type: 'percent', value: 10, min_order: 0, max_discount: null,
    max_uses: 0, is_active: true, description: '', product_ids: [],
  });

  const load = async () => {
    const [c, p] = await Promise.all([api.getCoupons(), api.getProducts()]);
    setCoupons(c.coupons);
    setProducts(p.products);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (modal === 'edit') await api.updateCoupon(form.id, form);
    else await api.createCoupon(form);
    setModal(null); load();
  };

  const [deleteId, setDeleteId] = useState(null);

  const handleDelete = async (id) => {
    try {
      await api.deleteCoupon(id);
      setDeleteId(null);
      load();
    } catch (e) {
      alert('Error: ' + e.message);
    }
  };

  const toggleProduct = (pid) => {
    setForm(f => ({
      ...f,
      product_ids: f.product_ids.includes(pid)
        ? f.product_ids.filter(id => id !== pid)
        : [...f.product_ids, pid],
    }));
  };

  const resetForm = () => ({
    code: '', type: 'percent', value: 10, min_order: 0, max_discount: null,
    max_uses: 0, is_active: true, description: '', product_ids: [],
  });

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Coupons</h1>
      <p className="page-subtitle">Create discount codes and assign them to products</p>
      <div className="toolbar">
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{coupons.length} coupons</span>
        <button className="btn btn-primary" onClick={() => { setForm(resetForm()); setModal('create'); }}>
          <Plus size={16} /> New Coupon
        </button>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Code</th><th>Type</th><th>Value</th><th>Min Order</th>
              <th>Applies To</th><th>Used / Max</th><th>Active</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {coupons.map(c => (
              <tr key={c.id}>
                <td style={{ fontWeight: 700, fontFamily: 'monospace', fontSize: 14, color: 'var(--primary)' }}>{c.code}</td>
                <td><span className="badge badge-neutral">{c.type}</span></td>
                <td style={{ fontWeight: 600 }}>{c.type === 'percent' ? `${c.value}%` : `$${c.value}`}</td>
                <td style={{ color: 'var(--text-muted)' }}>${c.min_order}</td>
                <td>
                  {c.applies_to_all ? (
                    <span style={{ color: '#30d158', fontSize: 12, fontWeight: 600 }}>🌐 All Products</span>
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                      {c.product_names.map((name, i) => (
                        <span key={i} style={{
                          padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                          background: 'rgba(99,102,241,0.15)', color: 'var(--primary)',
                        }}>📦 {name}</span>
                      ))}
                    </div>
                  )}
                </td>
                <td style={{ color: 'var(--text-muted)' }}>{c.used_count} / {c.max_uses || '∞'}</td>
                <td>
                  <div className={`toggle ${c.is_active ? 'active' : ''}`}
                    onClick={async () => { await api.updateCoupon(c.id, { ...c, is_active: !c.is_active }); load(); }} />
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setForm({ ...c }); setModal('edit'); }}>
                      <Edit2 size={13} />
                    </button>
                    {deleteId === c.id ? (
                      <>
                        <button className="btn btn-sm" onClick={() => handleDelete(c.id)}
                          style={{ background: '#ff453a', color: '#fff', border: 'none', fontSize: 11, padding: '4px 10px' }}>
                          Confirm
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => setDeleteId(null)}
                          style={{ fontSize: 11, padding: '4px 8px' }}>
                          ✕
                        </button>
                      </>
                    ) : (
                      <button className="btn btn-secondary btn-sm" onClick={() => setDeleteId(c.id)}
                        style={{ color: '#ff453a' }}>
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {coupons.length === 0 && (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                <TicketIcon size={40} style={{ opacity: 0.3, display: 'block', margin: '0 auto 8px' }} />
                No coupons yet
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 560 }}>
            <h2 className="modal-title">{modal === 'edit' ? '✏️ Edit' : '🆕 New'} Coupon</h2>

            <div className="grid-2">
              <div className="input-group">
                <label className="input-label">Code</label>
                <input className="input" value={form.code}
                  placeholder="DISCOUNT20"
                  onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} />
              </div>
              <div className="input-group">
                <label className="input-label">Type</label>
                <select className="select" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
                  <option value="percent">Percent (%)</option>
                  <option value="fixed">Fixed ($)</option>
                </select>
              </div>
            </div>

            <div className="grid-3">
              <div className="input-group">
                <label className="input-label">Value</label>
                <input className="input" type="number" value={form.value}
                  onChange={e => setForm({ ...form, value: parseFloat(e.target.value) || 0 })} />
              </div>
              <div className="input-group">
                <label className="input-label">Min Order ($)</label>
                <input className="input" type="number" value={form.min_order}
                  onChange={e => setForm({ ...form, min_order: parseFloat(e.target.value) || 0 })} />
              </div>
              <div className="input-group">
                <label className="input-label">Max Uses (0=∞)</label>
                <input className="input" type="number" value={form.max_uses}
                  onChange={e => setForm({ ...form, max_uses: parseInt(e.target.value) || 0 })} />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label">Description</label>
              <input className="input" value={form.description || ''}
                placeholder="Optional description..."
                onChange={e => setForm({ ...form, description: e.target.value })} />
            </div>

            {/* Product Assignment */}
            <div className="input-group" style={{ marginTop: 12 }}>
              <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <Package size={14} /> Applies to Products
              </label>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 8px' }}>
                Select products. Leave empty = applies to all.
              </p>
              <div style={{
                display: 'flex', flexWrap: 'wrap', gap: 6,
                maxHeight: 180, overflowY: 'auto', padding: 8,
                background: 'var(--bg-primary)', borderRadius: 8, border: '1px solid var(--border-color)',
              }}>
                {products.map(p => {
                  const isSelected = (form.product_ids || []).includes(p.id);
                  return (
                    <button key={p.id} onClick={() => toggleProduct(p.id)}
                      style={{
                        padding: '6px 12px', borderRadius: 6, border: '2px solid',
                        cursor: 'pointer', fontSize: 12, fontWeight: 600,
                        transition: 'all 0.2s',
                        background: isSelected ? 'rgba(99,102,241,0.15)' : 'transparent',
                        borderColor: isSelected ? 'var(--primary)' : 'var(--border-color)',
                        color: isSelected ? 'var(--primary)' : 'var(--text-muted)',
                      }}>
                      {isSelected ? '✅' : '📦'} {p.name}
                      {p.prices?.[0] && <span style={{ opacity: 0.7 }}> (${p.prices[0].price})</span>}
                    </button>
                  );
                })}
                {products.length === 0 && (
                  <span style={{ color: 'var(--text-muted)', fontSize: 12, padding: 8 }}>No products available</span>
                )}
              </div>
              {(form.product_ids || []).length > 0 && (
                <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 600 }}>
                    {form.product_ids.length} product(s) selected
                  </span>
                  <button onClick={() => setForm({ ...form, product_ids: [] })}
                    style={{
                      padding: '2px 8px', borderRadius: 4, border: 'none', cursor: 'pointer',
                      fontSize: 11, background: 'rgba(255,69,58,0.15)', color: '#ff453a',
                    }}>
                    <X size={10} /> Clear
                  </button>
                </div>
              )}
            </div>

            <div className="modal-actions" style={{ marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave}>
                {modal === 'edit' ? 'Update' : 'Create'} Coupon
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
