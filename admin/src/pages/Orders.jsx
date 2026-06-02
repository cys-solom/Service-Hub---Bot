import { useState, useEffect, useMemo } from 'react';
import { Eye, Check, X, Truck, Trash2, Package, RefreshCw, ArrowUpDown, ArrowUp, ArrowDown, CheckSquare, Square, MinusSquare } from 'lucide-react';
import api from '../services/api';

const STATUS_COLORS = {
  pending: { bg: 'rgba(255,159,10,0.15)', color: '#ff9f0a', label: 'Pending' },
  waiting_payment: { bg: 'rgba(255,159,10,0.15)', color: '#ff9f0a', label: 'Waiting' },
  paid: { bg: 'rgba(48,209,88,0.15)', color: '#30d158', label: 'Paid' },
  under_review: { bg: 'rgba(94,92,230,0.15)', color: '#5e5ce6', label: 'Review' },
  delivered: { bg: 'rgba(52,199,89,0.15)', color: '#34c759', label: 'Delivered' },
  canceled: { bg: 'rgba(255,69,58,0.15)', color: '#ff453a', label: 'Canceled' },
  refunded: { bg: 'rgba(255,69,58,0.15)', color: '#ff453a', label: 'Refunded' },
};

const StatusBadge = ({ status }) => {
  const s = STATUS_COLORS[status] || { bg: 'rgba(99,99,102,0.15)', color: '#636366', label: status };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600,
      background: s.bg, color: s.color, textTransform: 'capitalize',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.color }} />
      {s.label}
    </span>
  );
};

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(null);
  const [toast, setToast] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const load = async (p = 1, s = status) => {
    setLoading(true);
    setSelected(new Set());
    try {
      const d = await api.getOrders(p, s);
      setOrders(d.orders); setTotal(d.total); setPage(p); setPages(d.pages);
    } catch (e) { console.error(e); }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  // Sort locally
  const sorted = useMemo(() => {
    const arr = [...orders];
    arr.sort((a, b) => {
      let va = a[sortKey], vb = b[sortKey];
      if (['final_amount', 'total_amount'].includes(sortKey)) { va = Number(va); vb = Number(vb); }
      if (sortKey === 'created_at') { va = new Date(va); vb = new Date(vb); }
      if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return arr;
  }, [orders, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <ArrowUpDown size={12} style={{ opacity: 0.3 }} />;
    return sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />;
  };

  // Selection
  const toggleSelect = (id) => {
    setSelected(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === sorted.length) setSelected(new Set());
    else setSelected(new Set(sorted.map(o => o.id)));
  };

  const allSelected = sorted.length > 0 && selected.size === sorted.length;
  const someSelected = selected.size > 0 && selected.size < sorted.length;

  // Bulk delete
  const [confirmBulk, setConfirmBulk] = useState(false);
  const handleBulkDelete = async () => {
    if (selected.size === 0) return;
    if (!confirmBulk) { setConfirmBulk(true); return; }
    setConfirmBulk(false);
    setBusy('bulk');
    try {
      const res = await api.bulkDeleteOrders([...selected]);
      showToast(`🗑️ Deleted ${res.deleted} order(s)`);
      load(page);
    } catch (e) {
      showToast(`❌ Error: ${e.message}`, 'error');
    }
    setBusy(null);
  };

  const viewOrder = async (id) => {
    try {
      const d = await api.getOrder(id);
      setDetail(d);
    } catch (e) { showToast(`❌ ${e.message}`, 'error'); }
  };

  const handleApprove = async (id) => {
    setBusy(id);
    try {
      const res = await api.approveOrder(id);
      showToast(`✅ ${res.message}`);
      load(page);
      if (detail?.id === id) viewOrder(id);
    } catch (e) { showToast(`❌ ${e.message}`, 'error'); }
    setBusy(null);
  };

  const handleReject = async (id) => {
    const reason = 'Order rejected by admin';
    setBusy(id);
    try {
      await api.rejectOrder(id, reason);
      showToast('❌ Order rejected');
      load(page);
      if (detail?.id === id) setDetail({ ...detail, status: 'canceled' });
    } catch (e) { showToast(`❌ ${e.message}`, 'error'); }
    setBusy(null);
  };

  const [deleteId, setDeleteId] = useState(null);
  const handleDelete = async (id) => {
    if (deleteId !== id) { setDeleteId(id); return; }
    setDeleteId(null);
    setBusy(id);
    try {
      await api.deleteOrder(id);
      showToast('🗑️ Order deleted');
      load(page);
      if (detail?.id === id) setDetail(null);
    } catch (e) { showToast(`❌ ${e.message}`, 'error'); }
    setBusy(null);
  };

  const changeStatus = async (id, newStatus) => {
    setBusy(id);
    try {
      await api.updateOrderStatus(id, newStatus);
      load(page);
      if (detail?.id === id) setDetail({ ...detail, status: newStatus });
    } catch (e) { showToast(`❌ ${e.message}`, 'error'); }
    setBusy(null);
  };

  const tabs = [
    { key: '', label: 'All' },
    { key: 'pending', label: '⏳ Pending' },
    { key: 'paid', label: '💰 Paid' },
    { key: 'delivered', label: '✅ Delivered' },
    { key: 'canceled', label: '❌ Canceled' },
  ];

  const canApprove = (s) => ['pending', 'paid', 'waiting_payment', 'under_review'].includes(s);
  const thStyle = { cursor: 'pointer', userSelect: 'none', display: 'flex', alignItems: 'center', gap: 4 };

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 9999,
          padding: '14px 24px', borderRadius: 12,
          background: toast.type === 'error' ? 'rgba(255,69,58,0.95)' : 'rgba(48,209,88,0.95)',
          color: '#fff', fontWeight: 600, fontSize: 14,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          backdropFilter: 'blur(12px)',
          animation: 'slideIn 0.3s ease', maxWidth: 400,
        }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <h1 className="page-title">Orders</h1>
          <p className="page-subtitle" style={{ margin: 0 }}>Approve to auto-deliver • Reject to cancel • {total} total</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {selected.size > 0 && (
            <button onClick={handleBulkDelete} disabled={busy === 'bulk'}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
                background: confirmBulk ? '#ff453a' : 'rgba(255,69,58,0.15)',
                color: confirmBulk ? '#fff' : '#ff453a', fontWeight: 600, fontSize: 13,
                transition: 'all 0.2s',
              }}>
              <Trash2 size={14} /> {confirmBulk ? `⚠ Confirm Delete (${selected.size})` : `Delete (${selected.size})`}
            </button>
          )}
          {confirmBulk && (
            <button onClick={() => setConfirmBulk(false)}
              style={{ padding: '8px 12px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--bg-card-hover)', color: 'var(--text-muted)', fontSize: 12 }}>
              ✕
            </button>
          )}
          <button className="btn btn-secondary" onClick={() => load(page)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => { setStatus(t.key); load(1, t.key); }}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: 600, transition: 'all 0.2s',
              background: status === t.key ? 'var(--primary)' : 'var(--card-bg)',
              color: status === t.key ? '#fff' : 'var(--text-muted)',
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th style={{ width: 40 }}>
                  <div onClick={toggleSelectAll} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                    {allSelected ? <CheckSquare size={18} color="var(--primary)" /> :
                     someSelected ? <MinusSquare size={18} color="var(--primary)" /> :
                     <Square size={18} style={{ opacity: 0.4 }} />}
                  </div>
                </th>
                <th><div style={thStyle} onClick={() => toggleSort('order_number')}>Order <SortIcon col="order_number" /></div></th>
                <th><div style={thStyle} onClick={() => toggleSort('display_name')}>Customer <SortIcon col="display_name" /></div></th>
                <th><div style={thStyle} onClick={() => toggleSort('final_amount')}>Amount <SortIcon col="final_amount" /></div></th>
                <th><div style={thStyle} onClick={() => toggleSort('status')}>Status <SortIcon col="status" /></div></th>
                <th><div style={thStyle} onClick={() => toggleSort('created_at')}>Date <SortIcon col="created_at" /></div></th>
                <th style={{ minWidth: 220, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(o => (
                <tr key={o.id}
                  style={{
                    ...(o.status === 'paid' ? { background: 'rgba(48,209,88,0.05)', borderLeft: '3px solid #30d158' } : {}),
                    ...(selected.has(o.id) ? { background: 'rgba(120,120,255,0.08)' } : {}),
                  }}>
                  <td>
                    <div onClick={() => toggleSelect(o.id)} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                      {selected.has(o.id) ?
                        <CheckSquare size={18} color="var(--primary)" /> :
                        <Square size={18} style={{ opacity: 0.3 }} />}
                    </div>
                  </td>
                  <td>
                    <span style={{ fontWeight: 700, fontSize: 13 }}>{o.order_number}</span>
                    {o.payment_method && <span style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)' }}>{o.payment_method}</span>}
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{o.display_name}</div>
                    {o.username && o.username !== o.display_name && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>@{o.username}</div>
                    )}
                  </td>
                  <td><strong style={{ color: 'var(--primary)' }}>${o.final_amount}</strong></td>
                  <td><StatusBadge status={o.status} /></td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{new Date(o.created_at).toLocaleString()}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => viewOrder(o.id)} title="View">
                        <Eye size={13} />
                      </button>

                      {canApprove(o.status) && (
                        <button className="btn btn-sm" onClick={() => handleApprove(o.id)}
                          disabled={busy === o.id} title="Approve & Deliver"
                          style={{ background: '#30d158', color: '#fff', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Check size={13} /> Deliver
                        </button>
                      )}

                      {canApprove(o.status) && (
                        <button className="btn btn-danger btn-sm" onClick={() => handleReject(o.id)}
                          disabled={busy === o.id} title="Reject">
                          <X size={13} />
                        </button>
                      )}

                      {deleteId === o.id ? (
                        <>
                          <button className="btn btn-sm" onClick={() => handleDelete(o.id)}
                            style={{ background: '#ff453a', color: '#fff', border: 'none', fontSize: 11, padding: '4px 10px' }}>
                            Confirm
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={() => setDeleteId(null)}
                            style={{ fontSize: 11, padding: '4px 8px' }}>
                            ✕
                          </button>
                        </>
                      ) : (
                        <button className="btn btn-sm" onClick={() => handleDelete(o.id)} disabled={busy === o.id} title="Delete"
                          style={{ background: 'rgba(255,69,58,0.1)', color: '#ff453a' }}>
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {orders.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  <Package size={40} style={{ opacity: 0.3, marginBottom: 8, display: 'block', margin: '0 auto 8px' }} />
                  No orders found
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div style={{ display: 'flex', gap: 4, justifyContent: 'center', marginTop: 16 }}>
          {Array.from({ length: pages }, (_, i) => (
            <button key={i} onClick={() => load(i + 1)}
              style={{
                padding: '6px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: page === i + 1 ? 'var(--primary)' : 'var(--card-bg)',
                color: page === i + 1 ? '#fff' : 'var(--text-muted)', fontWeight: 600, fontSize: 13,
              }}>{i + 1}</button>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ minWidth: 580, maxWidth: 700, maxHeight: '85vh', overflow: 'auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>
                <Package size={20} style={{ marginRight: 8 }} />
                {detail.order_number}
              </h2>
              <StatusBadge status={detail.status} />
            </div>

            {/* Info Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
              {[
                { label: 'Amount', value: `$${detail.final_amount}`, color: 'var(--primary)' },
                { label: 'Customer', value: detail.username || `TG:${detail.telegram_id}` },
                { label: 'Payment', value: detail.payment_method || '—' },
              ].map((c, i) => (
                <div key={i} style={{ background: 'var(--bg)', borderRadius: 8, padding: '12px 14px' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{c.label}</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: c.color || 'var(--text)' }}>{c.value}</div>
                </div>
              ))}
            </div>

            {/* Items Table */}
            {detail.items?.length > 0 && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--text-muted)' }}>ORDER ITEMS</div>
                <div className="table-wrapper" style={{ marginBottom: 16 }}>
                  <table>
                    <thead><tr><th>Product</th><th>Qty</th><th>Price</th><th>Status</th></tr></thead>
                    <tbody>
                      {detail.items.map(i => (
                        <tr key={i.id}>
                          <td style={{ fontWeight: 600 }}>{i.product_name || i.product_id}</td>
                          <td>{i.quantity}</td>
                          <td>${i.total_price}</td>
                          <td><StatusBadge status={i.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Delivered Data */}
                {detail.items.some(i => i.delivered_data) && (
                  <>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--text-muted)' }}>DELIVERY DATA</div>
                    <div style={{
                      background: 'rgba(48,209,88,0.08)', border: '1px solid rgba(48,209,88,0.2)',
                      borderRadius: 8, padding: 14, marginBottom: 16, fontFamily: 'monospace', fontSize: 12,
                    }}>
                      {detail.items.filter(i => i.delivered_data).map((i, idx) => (
                        <div key={idx}>
                          <div style={{ color: '#30d158', fontWeight: 600, marginBottom: 4 }}>{i.product_name}:</div>
                          <pre style={{ margin: '0 0 8px', whiteSpace: 'pre-wrap', color: 'var(--text)' }}>{i.delivered_data}</pre>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              {canApprove(detail.status) && (
                <button onClick={() => handleApprove(detail.id)} disabled={busy === detail.id}
                  style={{
                    flex: 1, padding: '12px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: 'linear-gradient(135deg, #30d158, #34c759)', color: '#fff',
                    fontWeight: 700, fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  }}>
                  <Truck size={18} /> Approve & Auto-Deliver
                </button>
              )}
              {canApprove(detail.status) && (
                <button onClick={() => handleReject(detail.id)} disabled={busy === detail.id}
                  style={{
                    padding: '12px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: 'rgba(255,69,58,0.15)', color: '#ff453a', fontWeight: 700, fontSize: 14,
                  }}>
                  <X size={16} /> Reject
                </button>
              )}
              {detail.status === 'delivered' && (
                <div style={{
                  flex: 1, padding: '12px 16px', borderRadius: 8,
                  background: 'rgba(48,209,88,0.1)', color: '#30d158',
                  fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}>
                  <Check size={18} /> Already Delivered
                </div>
              )}
            </div>

            {/* Manual Status + Delete */}
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="input-group" style={{ flex: 1, marginBottom: 0 }}>
                <label className="input-label">Manual Status</label>
                <select className="select" value={detail.status}
                  onChange={e => changeStatus(detail.id, e.target.value)}>
                  {['pending', 'paid', 'delivered', 'canceled', 'refunded'].map(s =>
                    <option key={s} value={s}>{s}</option>
                  )}
                </select>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button onClick={() => handleDelete(detail.id)}
                  style={{
                    padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
                    background: 'rgba(255,69,58,0.1)', color: '#ff453a', fontWeight: 600, fontSize: 13,
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={() => setDetail(null)}>Close</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
