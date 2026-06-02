import { useState, useEffect, useCallback } from 'react';
import { Upload, Download, Trash2, RotateCcw, Package, Search, RefreshCw, X, ChevronLeft, ChevronRight, Plus, Edit2, AlertTriangle, Copy, Save, FileText } from 'lucide-react';
import api from '../services/api';

export default function Stock() {
  const [products, setProducts] = useState([]);
  const [stockSummary, setStockSummary] = useState({});
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stockLoading, setStockLoading] = useState(false);
  const [filter, setFilter] = useState('available');
  const [searchQuery, setSearchQuery] = useState('');
  const [toast, setToast] = useState(null);
  const [confirmDel, setConfirmDel] = useState(null);
  const [confirmDelSold, setConfirmDelSold] = useState(false);

  // Modal states
  const [modal, setModal] = useState(null); // 'add' | 'edit' | 'import'
  const [modalData, setModalData] = useState('');
  const [modalId, setModalId] = useState(null);
  const [modalSaving, setModalSaving] = useState(false);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [p, s] = await Promise.all([api.getProducts(), api.getStockSummary()]);
      setProducts(p.products || []);
      setStockSummary(s.summary || {});
    } catch (e) { showToast('Failed to load', 'error'); }
    setLoading(false);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const refreshSummary = async () => {
    const s = await api.getStockSummary();
    setStockSummary(s.summary || {});
  };

  const loadStock = useCallback(async (pid, p = 1) => {
    if (!pid) return;
    setStockLoading(true);
    try {
      const isSold = filter === 'sold' ? true : filter === 'available' ? false : undefined;
      let url = `/stock?product_id=${pid}&page=${p}&limit=50`;
      if (isSold !== undefined) url += `&is_sold=${isSold}`;
      const d = await api.get(url);
      setItems(d.items || []);
      setTotal(d.total || 0);
      setPage(d.page || p);
      setPages(d.pages || 1);
    } catch (e) { showToast('Failed to load stock', 'error'); }
    setStockLoading(false);
  }, [filter]);

  useEffect(() => {
    if (selectedProduct) loadStock(selectedProduct.id);
  }, [selectedProduct, filter, loadStock]);

  // ── Modal Handlers ──
  const openAdd = () => { setModal('add'); setModalData(''); setModalId(null); };
  const openEdit = (item) => { setModal('edit'); setModalData(item.data); setModalId(item.id); };
  const openImport = () => { setModal('import'); setModalData(''); };
  const closeModal = () => { setModal(null); setModalData(''); setModalId(null); setModalSaving(false); };

  const handleModalSave = async () => {
    if (!modalData.trim()) return;
    setModalSaving(true);
    try {
      if (modal === 'add') {
        // Use bulk endpoint even for single items to trigger broadcast notification
        const lines = modalData.split('\n').filter(l => l.trim());
        if (!lines.length) { setModalSaving(false); return; }
        const res = await api.addStockBulk({ product_id: selectedProduct.id, items: lines });
        showToast(`✅ Added ${res.added} item${res.added > 1 ? 's' : ''} — notification sent`);
      } else if (modal === 'edit') {
        await api.updateStockItem(modalId, { data: modalData.trim() });
        showToast('✅ Item updated successfully');
      } else if (modal === 'import') {
        const lines = modalData.split('\n').filter(l => l.trim());
        if (!lines.length) { setModalSaving(false); return; }
        const res = await api.addStockBulk({ product_id: selectedProduct.id, items: lines });
        showToast(`✅ Imported ${res.added} items — notification sent`);
      }
      closeModal();
      loadStock(selectedProduct.id, 1);
      refreshSummary();
    } catch (e) { showToast(e.message, 'error'); }
    setModalSaving(false);
  };

  const handleDelete = async (id) => {
    if (confirmDel !== id) { setConfirmDel(id); return; }
    try {
      await api.deleteStockItem(id);
      showToast('Item deleted');
      setConfirmDel(null);
      loadStock(selectedProduct.id, page); refreshSummary();
    } catch (e) { showToast(e.message, 'error'); }
  };

  const handleRestore = async (id) => {
    await api.restoreStock(id);
    loadStock(selectedProduct.id, page); refreshSummary();
    showToast('Item restored');
  };

  const handleDeleteSold = async () => {
    if (!selectedProduct) return;
    const summary = getProductStock(selectedProduct.id);
    if (!summary.sold) { showToast('No sold items', 'error'); return; }
    if (!confirmDelSold) { setConfirmDelSold(true); return; }
    await api.deleteSoldStock(selectedProduct.id);
    loadStock(selectedProduct.id, 1); refreshSummary();
    showToast(`Deleted ${summary.sold} sold items`);
    setConfirmDelSold(false);
  };

  const handleExport = async () => {
    if (!selectedProduct) return;
    const res = await api.exportStock(selectedProduct.id);
    const blob = new Blob([res.items.join('\n')], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${selectedProduct.name.replace(/\s+/g, '_')}_stock_${Date.now()}.txt`;
    a.click();
    showToast(`Exported ${res.count} items`);
  };

  const copyData = (data) => { navigator.clipboard.writeText(data); showToast('📋 Copied!'); };

  const getProductStock = (pid) => stockSummary[pid] || { total: 0, available: 0, sold: 0, reserved: 0 };
  const filteredProducts = products.filter(p => !searchQuery || p.name.toLowerCase().includes(searchQuery.toLowerCase()));

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  const importLineCount = modal === 'import' ? modalData.split('\n').filter(l => l.trim()).length : 0;

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

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="page-title" style={{ marginBottom: 4 }}>Stock Manager</h1>
          <p className="page-subtitle">Click a product to manage its inventory</p>
        </div>
        <button className="btn btn-secondary" onClick={loadAll}><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 16, maxWidth: 360 }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
        <input className="input" style={{ paddingLeft: 36 }} placeholder="Search products..."
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
      </div>

      {/* Product Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
        {filteredProducts.map(p => {
          const s = getProductStock(p.id);
          const isAPI = p.meta?.delivery_type === 'api';
          const isSelected = selectedProduct?.id === p.id;
          const isEmpty = !isAPI && s.available === 0;
          const isLow = !isAPI && s.available > 0 && s.available <= 5;
          return (
            <div key={p.id} onClick={() => { setSelectedProduct(isSelected ? null : p); setConfirmDel(null); }}
              style={{
                padding: '14px 16px', borderRadius: 12, cursor: 'pointer',
                border: `2px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                background: isSelected ? 'var(--accent-bg)' : 'var(--bg-card)',
                transition: 'all 0.2s ease', position: 'relative', overflow: 'hidden',
              }}>
              <div style={{
                position: 'absolute', top: 0, right: 0, width: 28, height: 28, borderRadius: '0 12px 0 8px',
                background: isAPI ? 'var(--info)' : isEmpty ? 'var(--danger)' : isLow ? 'var(--warning)' : 'var(--success)',
                opacity: 0.15,
              }} />
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>{p.meta?.emoji || '📦'}</span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
              </div>
              {isAPI ? (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className="badge badge-info" style={{ fontSize: 11 }}>🔌 API</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>No stock needed</span>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Available</div>
                    <div style={{ fontWeight: 700, fontSize: 18, color: isEmpty ? 'var(--danger)' : isLow ? 'var(--warning)' : 'var(--success)' }}>{s.available}</div>
                  </div>
                  <div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Sold</div>
                    <div style={{ fontWeight: 600, fontSize: 18, color: 'var(--text-muted)' }}>{s.sold}</div>
                  </div>
                </div>
              )}
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                ${p.prices?.[0]?.price || 0} · {p.stock_type || 'code'}
              </div>
            </div>
          );
        })}
        {filteredProducts.length === 0 && (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
            <Package size={48} strokeWidth={1} style={{ marginBottom: 12, opacity: 0.3 }} />
            <div>No products found</div>
          </div>
        )}
      </div>

      {/* ── Selected Product Detail ── */}
      {selectedProduct && (
        <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
          <div style={{
            padding: '16px 20px', background: 'var(--accent-bg)',
            borderBottom: '1px solid var(--border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 24 }}>{selectedProduct.meta?.emoji || '📦'}</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>{selectedProduct.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {(() => { const s = getProductStock(selectedProduct.id); return `${s.available} available · ${s.sold} sold · ${s.total} total`; })()}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
              <button className="btn btn-primary btn-sm" onClick={openAdd} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Plus size={13} /> Add Item
              </button>
              <button className="btn btn-primary btn-sm" onClick={openImport} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Upload size={13} /> Bulk Import
              </button>
              <button className="btn btn-secondary btn-sm" onClick={handleExport} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Download size={13} /> Export
              </button>
              {getProductStock(selectedProduct.id).sold > 0 && (
                <button className="btn btn-danger btn-sm" onClick={handleDeleteSold}
                  onMouseLeave={() => confirmDelSold && setTimeout(() => setConfirmDelSold(false), 2000)}
                  style={{ display: 'flex', alignItems: 'center', gap: 4, ...(confirmDelSold ? { background: '#dc2626' } : {}) }}>
                  {confirmDelSold ? <><AlertTriangle size={13} /> Confirm?</> : <><Trash2 size={13} /> Clear Sold ({getProductStock(selectedProduct.id).sold})</>}
                </button>
              )}
              <button onClick={() => setSelectedProduct(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}><X size={18} /></button>
            </div>
          </div>

          {/* Filter tabs */}
          <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 6 }}>
            {[
              { v: 'available', label: 'Available', count: getProductStock(selectedProduct.id).available },
              { v: 'sold', label: 'Sold', count: getProductStock(selectedProduct.id).sold },
              { v: 'all', label: 'All', count: getProductStock(selectedProduct.id).total },
            ].map(f => (
              <button key={f.v} className={`btn btn-sm ${filter === f.v ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => { setFilter(f.v); setPage(1); }}
                style={{ fontSize: 12, fontWeight: filter === f.v ? 700 : 500 }}>{f.label} ({f.count})</button>
            ))}
          </div>

          {/* Stock Table */}
          {stockLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><div className="loading" /></div>
          ) : (
            <>
              <div className="table-wrapper" style={{ margin: 0 }}>
                <table>
                  <thead><tr>
                    <th style={{ width: '40%' }}>Data</th>
                    <th>Status</th><th>Batch</th><th>Date</th>
                    <th style={{ width: '160px', textAlign: 'right' }}>Actions</th>
                  </tr></thead>
                  <tbody>
                    {items.map(item => (
                      <tr key={item.id}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'monospace', fontSize: 12, maxWidth: 400 }}>
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.data}</span>
                            <button onClick={() => copyData(item.data)} title="Copy"
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2, flexShrink: 0, opacity: 0.4 }}>
                              <Copy size={12} />
                            </button>
                          </div>
                        </td>
                        <td>
                          {item.is_sold ? <span className="badge badge-danger">Sold</span>
                            : item.is_reserved ? <span className="badge badge-warning">Reserved</span>
                            : <span className="badge badge-success">Available</span>}
                        </td>
                        <td style={{ color: 'var(--text-muted)', fontSize: 12, fontFamily: 'monospace' }}>{item.batch_id?.slice(0, 7) || '—'}</td>
                        <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{new Date(item.created_at).toLocaleDateString()}</td>
                        <td>
                          <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                            {!item.is_sold && (
                              <button className="btn btn-secondary btn-sm" onClick={() => openEdit(item)} title="Edit" style={{ padding: '4px 8px' }}>
                                <Edit2 size={12} />
                              </button>
                            )}
                            {item.is_sold && (
                              <button className="btn btn-secondary btn-sm" onClick={() => handleRestore(item.id)} style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11 }}>
                                <RotateCcw size={12} /> Restore
                              </button>
                            )}
                            <button className="btn btn-danger btn-sm" onClick={() => handleDelete(item.id)}
                              onMouseLeave={() => confirmDel === item.id && setTimeout(() => setConfirmDel(null), 2000)}
                              title={confirmDel === item.id ? 'Click to confirm' : 'Delete'}
                              style={{ padding: '4px 8px', display: 'flex', alignItems: 'center', gap: 3, fontSize: 11,
                                ...(confirmDel === item.id ? { background: '#dc2626' } : {}) }}>
                              {confirmDel === item.id ? <><AlertTriangle size={12} /> Sure?</> : <Trash2 size={12} />}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {items.length === 0 && (
                      <tr><td colSpan={5} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                        <Package size={32} strokeWidth={1} style={{ marginBottom: 8, opacity: 0.3 }} />
                        <div style={{ marginBottom: 12 }}>No {filter !== 'all' ? filter : ''} stock items</div>
                        <button className="btn btn-primary btn-sm" onClick={openAdd}><Plus size={13} /> Add First Item</button>
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {pages > 1 && (
                <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'center', gap: 4, alignItems: 'center' }}>
                  <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => loadStock(selectedProduct.id, page - 1)}><ChevronLeft size={14} /></button>
                  <span style={{ fontSize: 13, color: 'var(--text-muted)', padding: '0 12px' }}>Page {page} of {pages} · {total} items</span>
                  <button className="btn btn-secondary btn-sm" disabled={page >= pages} onClick={() => loadStock(selectedProduct.id, page + 1)}><ChevronRight size={14} /></button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ══════ Add / Edit Modal ══════ */}
      {(modal === 'add' || modal === 'edit') && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <div style={{
                width: 44, height: 44, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: modal === 'add' ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' : 'linear-gradient(135deg, #f59e0b, #ef4444)',
                color: '#fff', fontSize: 20,
              }}>
                {modal === 'add' ? <Plus size={22} /> : <Edit2 size={20} />}
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
                  {modal === 'add' ? 'Add Stock Item' : 'Edit Stock Item'}
                </h2>
                <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
                  {selectedProduct?.name}
                </p>
              </div>
            </div>

            <div className="input-group">
              <label className="input-label">Stock Data</label>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 8px' }}>
                {modal === 'add'
                  ? 'Enter items (one per line). A notification will be sent to all users.'
                  : 'Edit the item value — code, email:password, license key, etc.'}
              </p>
              <textarea className="textarea"
                style={{ minHeight: modal === 'add' ? 140 : 100, fontFamily: 'monospace', fontSize: 13, lineHeight: 1.6, resize: 'vertical' }}
                value={modalData} onChange={e => setModalData(e.target.value)}
                placeholder={modal === 'add' ? 'code123\nemail@example.com:password123\nanother_code_here' : ''}
                autoFocus
              />
              {modal === 'add' && modalData.trim() && (
                <div style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600, marginTop: 6 }}>
                  📦 {modalData.split('\n').filter(l => l.trim()).length} item(s) will be added + notified
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={closeModal}>Cancel</button>
              <button className="btn btn-primary" onClick={handleModalSave} disabled={modalSaving || !modalData.trim()}
                style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 100, justifyContent: 'center' }}>
                {modalSaving ? 'Saving...' : <><Save size={14} /> {modal === 'add' ? 'Add Item' : 'Save Changes'}</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════ Bulk Import Modal ══════ */}
      {modal === 'import' && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 600 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <div style={{
                width: 44, height: 44, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff',
              }}>
                <FileText size={22} />
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Bulk Import</h2>
                <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>{selectedProduct?.name}</p>
              </div>
            </div>

            <div className="input-group">
              <label className="input-label">Paste Items</label>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 8px' }}>
                One item per line — <code>code</code>, <code>email:password</code>, or <code>email:pass:2fa</code>
              </p>
              <textarea className="textarea"
                style={{ minHeight: 240, fontFamily: 'monospace', fontSize: 12, lineHeight: 1.5 }}
                value={modalData} onChange={e => setModalData(e.target.value)}
                placeholder={"item1\nitem2\nemail@gmail.com:password123\nemail@outlook.com:pass:2FA_CODE"}
                autoFocus />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderRadius: 8,
                background: importLineCount > 0 ? 'rgba(99,102,241,0.1)' : 'transparent',
                color: 'var(--accent)', fontWeight: 600, fontSize: 13,
              }}>
                <Package size={14} />
                {importLineCount} item{importLineCount !== 1 ? 's' : ''} to import
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-secondary" onClick={closeModal}>Cancel</button>
                <button className="btn btn-primary" onClick={handleModalSave} disabled={modalSaving || importLineCount === 0}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 100, justifyContent: 'center' }}>
                  {modalSaving ? 'Importing...' : <><Upload size={14} /> Import {importLineCount > 0 ? `(${importLineCount})` : ''}</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
