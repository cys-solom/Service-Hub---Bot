import { useState, useEffect } from 'react';
import { Key, Users2, DollarSign, ShoppingBag, Plus, Eye, EyeOff, Copy, RefreshCw, Trash2, ToggleLeft, ToggleRight, X, ChevronDown, ChevronUp, ArrowUpDown, Edit3 } from 'lucide-react';
import api from '../services/api';

export default function Resellers() {
  const [resellers, setResellers] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', contact: '', notes: '' });
  const [detailsModal, setDetailsModal] = useState(null);
  const [detailsTab, setDetailsTab] = useState('transactions');
  const [transactions, setTransactions] = useState([]);
  const [txLoading, setTxLoading] = useState(false);
  const [balanceModal, setBalanceModal] = useState(null);
  const [amount, setAmount] = useState(0);
  const [balanceNote, setBalanceNote] = useState('');
  const [wholesaleModal, setWholesaleModal] = useState(false);
  const [wholesalePrices, setWholesalePrices] = useState([]);
  const [visibleKeys, setVisibleKeys] = useState(new Set());
  const [editRow, setEditRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [r, s] = await Promise.all([api.getResellers(), api.getResellerStats()]);
      setResellers(r.resellers); setStats(s);
    } catch (e) { showToast('Failed to load', 'error'); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!createForm.name.trim()) return;
    try {
      const res = await api.createReseller(createForm);
      showToast(`Reseller created! Key: ${res.reseller.api_key.slice(0, 20)}...`);
      setShowCreate(false); setCreateForm({ name: '', contact: '', notes: '' });
      load();
    } catch (e) { showToast('Failed to create', 'error'); }
  };

  const handleToggle = async (r) => {
    await api.updateReseller(r.id, { is_active: !r.is_active });
    setResellers(rs => rs.map(x => x.id === r.id ? { ...x, is_active: !x.is_active } : x));
    showToast(r.is_active ? 'Deactivated' : 'Activated');
  };

  const handleDelete = async (r) => {
    if (!confirm(`Delete reseller "${r.name}"?`)) return;
    await api.deleteReseller(r.id);
    setResellers(rs => rs.filter(x => x.id !== r.id));
    showToast('Deleted');
  };

  const handleRegenerate = async (r) => {
    if (!confirm('Regenerate API key? The old key will stop working.')) return;
    const res = await api.regenerateKey(r.id);
    setResellers(rs => rs.map(x => x.id === r.id ? { ...x, api_key: res.api_key } : x));
    setVisibleKeys(prev => { const n = new Set(prev); n.add(r.id); return n; });
    showToast('New key generated');
  };

  const copyKey = (key) => {
    navigator.clipboard.writeText(key);
    showToast('API key copied!');
  };

  const openDetails = async (r) => {
    setDetailsModal(r); setDetailsTab('transactions'); setTxLoading(true);
    try {
      const res = await api.getResellerTransactions(r.id);
      setTransactions(res.transactions);
    } catch (e) { setTransactions([]); }
    setTxLoading(false);
  };

  const handleBalance = async (op) => {
    if (amount <= 0) return;
    try {
      if (op === 'add') await api.resellerDeposit(balanceModal.id, amount, balanceNote);
      else await api.resellerDeduct(balanceModal.id, amount, balanceNote);
      showToast(`Balance ${op === 'add' ? 'added' : 'deducted'}`);
      setBalanceModal(null); setAmount(0); setBalanceNote('');
      load();
    } catch (e) { showToast('Failed', 'error'); }
  };

  const openWholesale = async () => {
    setWholesaleModal(true);
    try {
      const res = await api.getWholesalePrices();
      setWholesalePrices(res.products);
    } catch (e) { showToast('Failed to load prices', 'error'); }
  };

  const saveWholesale = async (productId, price) => {
    try {
      await api.setWholesalePrice(productId, price === '' ? null : parseFloat(price));
      showToast('Wholesale price saved');
    } catch (e) { showToast('Failed', 'error'); }
  };

  const handleEditSave = async (r) => {
    await api.updateReseller(r.id, editForm);
    setEditRow(null);
    showToast('Updated');
    load();
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Reseller API</h1>
      <p className="page-subtitle">Manage reseller API keys, wallets, and wholesale pricing</p>

      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 9999, padding: '12px 20px', borderRadius: 10,
          background: toast.type === 'error' ? 'var(--danger)' : 'var(--success)',
          color: '#fff', fontWeight: 600, fontSize: 13, boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        }}>{toast.msg}</div>
      )}

      {/* Stats */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Resellers', value: stats.total_resellers || 0, icon: Users2, bg: 'var(--accent-bg)', color: 'var(--accent)' },
          { label: 'Active', value: stats.active_resellers || 0, icon: Key, bg: 'var(--success-bg)', color: 'var(--success)' },
          { label: 'Total Revenue', value: `$${stats.total_revenue || 0}`, icon: DollarSign, bg: 'var(--warning-bg)', color: 'var(--warning)' },
          { label: 'API Orders', value: stats.total_orders || 0, icon: ShoppingBag, bg: '#1e3a5f', color: '#60a5fa' },
        ].map((s, i) => (
          <div className="stat-card" key={i}>
            <div><div className="stat-label">{s.label}</div><div className="stat-value">{s.value}</div></div>
            <div className="stat-icon" style={{ background: s.bg, color: s.color }}><s.icon size={22} /></div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="toolbar" style={{ marginBottom: 16 }}>
        <div className="flex gap-2">
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New Reseller
          </button>
          <button className="btn btn-secondary" onClick={openWholesale}>
            <DollarSign size={16} /> Wholesale Prices
          </button>
        </div>
      </div>

      {/* Resellers Table */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Name</th><th>API Key</th><th>Balance</th><th>Spent</th><th>Orders</th>
              <th>Rate Limit</th><th>Status</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {resellers.map(r => (
              <tr key={r.id}>
                <td>
                  <div style={{ fontWeight: 600 }}>{r.name}</div>
                  {r.contact && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.contact}</div>}
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <code style={{ fontSize: 11, background: 'var(--bg)', padding: '2px 6px', borderRadius: 4, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {visibleKeys.has(r.id) ? r.api_key : '••••••••••••••••••••'}
                    </code>
                    <button className="btn btn-icon btn-sm" style={{ padding: 2 }} onClick={() => setVisibleKeys(prev => {
                      const n = new Set(prev); n.has(r.id) ? n.delete(r.id) : n.add(r.id); return n;
                    })}>
                      {visibleKeys.has(r.id) ? <EyeOff size={12} /> : <Eye size={12} />}
                    </button>
                    <button className="btn btn-icon btn-sm" style={{ padding: 2 }} onClick={() => copyKey(r.api_key)}>
                      <Copy size={12} />
                    </button>
                  </div>
                </td>
                <td style={{ fontWeight: 600, color: 'var(--success)' }}>${r.balance}</td>
                <td style={{ color: 'var(--text-muted)' }}>${r.total_spent}</td>
                <td>{r.total_orders}</td>
                <td style={{ fontSize: 12 }}>{r.rate_limit}/min</td>
                <td>
                  <span onClick={() => handleToggle(r)} style={{ cursor: 'pointer' }}
                    className={`badge ${r.is_active ? 'badge-success' : 'badge-danger'}`}>
                    {r.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <div className="flex gap-2">
                    <button className="btn btn-secondary btn-sm" title="Details" onClick={() => openDetails(r)}><Eye size={13} /></button>
                    <button className="btn btn-secondary btn-sm" title="Balance" onClick={() => { setBalanceModal(r); setAmount(0); setBalanceNote(''); }}><DollarSign size={13} /></button>
                    <button className="btn btn-secondary btn-sm" title="Edit" onClick={() => { setEditRow(r.id); setEditForm({ name: r.name, contact: r.contact || '', notes: r.notes || '', rate_limit: r.rate_limit }); }}><Edit3 size={13} /></button>
                    <button className="btn btn-secondary btn-sm" title="Regenerate Key" onClick={() => handleRegenerate(r)}><RefreshCw size={13} /></button>
                    <button className="btn btn-danger btn-sm" title="Delete" onClick={() => handleDelete(r)}><Trash2 size={13} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {resellers.length === 0 && <tr><td colSpan={8} className="empty-state">No resellers yet. Create one to get started.</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">New Reseller</h2>
            <div className="input-group"><label className="input-label">Name *</label>
              <input className="input" placeholder="e.g. Ahmed Bot" value={createForm.name} onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))} /></div>
            <div className="input-group"><label className="input-label">Contact</label>
              <input className="input" placeholder="@telegram or email" value={createForm.contact} onChange={e => setCreateForm(f => ({ ...f, contact: e.target.value }))} /></div>
            <div className="input-group"><label className="input-label">Notes</label>
              <textarea className="input" rows={3} value={createForm.notes} onChange={e => setCreateForm(f => ({ ...f, notes: e.target.value }))} /></div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleCreate}>Create & Generate Key</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editRow && (
        <div className="modal-overlay" onClick={() => setEditRow(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">Edit Reseller</h2>
            <div className="input-group"><label className="input-label">Name</label>
              <input className="input" value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} /></div>
            <div className="input-group"><label className="input-label">Contact</label>
              <input className="input" value={editForm.contact} onChange={e => setEditForm(f => ({ ...f, contact: e.target.value }))} /></div>
            <div className="input-group"><label className="input-label">Rate Limit (req/min)</label>
              <input className="input" type="number" value={editForm.rate_limit} onChange={e => setEditForm(f => ({ ...f, rate_limit: parseInt(e.target.value) || 60 }))} /></div>
            <div className="input-group"><label className="input-label">Notes</label>
              <textarea className="input" rows={3} value={editForm.notes} onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))} /></div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setEditRow(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => handleEditSave(resellers.find(r => r.id === editRow))}>Save</button>
            </div>
          </div>
        </div>
      )}

      {/* Balance Modal */}
      {balanceModal && (
        <div className="modal-overlay" onClick={() => setBalanceModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">Manage Balance — {balanceModal.name}</h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>Current: <strong style={{ color: 'var(--success)' }}>${balanceModal.balance}</strong></p>
            <div className="input-group"><label className="input-label">Amount</label>
              <input className="input" type="number" step="0.01" value={amount} onChange={e => setAmount(parseFloat(e.target.value) || 0)} /></div>
            <div className="input-group"><label className="input-label">Note (optional)</label>
              <input className="input" placeholder="e.g. Bank transfer #123" value={balanceNote} onChange={e => setBalanceNote(e.target.value)} /></div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setBalanceModal(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={() => handleBalance('deduct')}>Deduct</button>
              <button className="btn btn-success" onClick={() => handleBalance('add')}>Deposit</button>
            </div>
          </div>
        </div>
      )}

      {/* Details / Transactions Modal */}
      {detailsModal && (
        <div className="modal-overlay" onClick={() => setDetailsModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 700, maxHeight: '85vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h2 className="modal-title" style={{ margin: 0 }}>{detailsModal.name}</h2>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{detailsModal.contact || 'No contact'}</div>
              </div>
              <button onClick={() => setDetailsModal(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={20} /></button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
              {[
                { label: 'Balance', value: `$${detailsModal.balance}`, color: 'var(--success)' },
                { label: 'Deposited', value: `$${detailsModal.total_deposited}`, color: 'var(--accent)' },
                { label: 'Spent', value: `$${detailsModal.total_spent}`, color: 'var(--warning)' },
                { label: 'Orders', value: detailsModal.total_orders, color: '#60a5fa' },
              ].map((s, i) => (
                <div key={i} style={{ textAlign: 'center', padding: '10px 8px', borderRadius: 10, background: 'var(--bg)', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {detailsModal.notes && (
              <div style={{ padding: '8px 14px', borderRadius: 8, marginBottom: 12, background: 'var(--bg)', border: '1px solid var(--border)', fontSize: 13, color: 'var(--text-muted)' }}>
                📝 {detailsModal.notes}
              </div>
            )}

            <div style={{ flex: 1, overflow: 'auto', maxHeight: '40vh' }}>
              {txLoading ? <div style={{ textAlign: 'center', padding: 30 }}><div className="loading" /></div> : (
                <table style={{ width: '100%' }}>
                  <thead><tr><th>Type</th><th>Product</th><th>Qty</th><th>Amount</th><th>Balance</th><th>Note</th><th>Date</th></tr></thead>
                  <tbody>
                    {transactions.map(tx => (
                      <tr key={tx.id}>
                        <td><span className={`badge ${tx.type === 'deposit' ? 'badge-success' : tx.type === 'purchase' ? 'badge-warning' : 'badge-danger'}`}>{tx.type}</span></td>
                        <td style={{ fontSize: 12 }}>{tx.product_name || '—'}</td>
                        <td>{tx.quantity || '—'}</td>
                        <td style={{ fontWeight: 600, color: tx.amount >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                          {tx.amount >= 0 ? '+' : ''}{tx.amount}
                        </td>
                        <td>${tx.balance_after}</td>
                        <td style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis' }}>{tx.description || '—'}</td>
                        <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{new Date(tx.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                    {transactions.length === 0 && <tr><td colSpan={7} className="empty-state">No transactions yet</td></tr>}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Wholesale Prices Modal */}
      {wholesaleModal && (
        <div className="modal-overlay" onClick={() => setWholesaleModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 600, maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>Wholesale Prices</h2>
              <button onClick={() => setWholesaleModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={20} /></button>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16 }}>
              Set wholesale prices for resellers. Leave blank to use the retail price.
            </p>
            <div style={{ flex: 1, overflow: 'auto' }}>
              <table style={{ width: '100%' }}>
                <thead><tr><th>Product</th><th>Retail Price</th><th>Wholesale Price</th><th></th></tr></thead>
                <tbody>
                  {wholesalePrices.map(p => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 600 }}>{p.name}</td>
                      <td>${p.retail_price}</td>
                      <td>
                        <input type="number" step="0.01" min="0" placeholder="Same as retail"
                          defaultValue={p.wholesale_price ?? ''}
                          onChange={e => {
                            const val = e.target.value;
                            setWholesalePrices(ps => ps.map(x => x.id === p.id ? { ...x, _edited: val } : x));
                          }}
                          style={{ width: 100, padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontSize: 13 }}
                        />
                      </td>
                      <td>
                        <button className="btn btn-primary btn-sm" style={{ padding: '3px 10px', fontSize: 11 }}
                          onClick={() => {
                            const item = wholesalePrices.find(x => x.id === p.id);
                            const val = item._edited !== undefined ? item._edited : (item.wholesale_price ?? '');
                            saveWholesale(p.id, val);
                          }}>Save</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
