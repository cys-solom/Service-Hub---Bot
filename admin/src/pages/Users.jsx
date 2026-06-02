import { useState, useEffect } from 'react';
import { Search, Ban, DollarSign, Shield, Eye, Users2, ShoppingBag, Wallet, X, ChevronRight } from 'lucide-react';
import api from '../services/api';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [balanceModal, setBalanceModal] = useState(null);
  const [amount, setAmount] = useState(0);
  const [detailsModal, setDetailsModal] = useState(null);
  const [detailsTab, setDetailsTab] = useState('orders');
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = async (p = 1, s = search) => {
    setLoading(true);
    const d = await api.getUsers(p, s);
    setUsers(d.users); setTotal(d.total); setPage(p); setPages(d.pages); setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const toggleBan = async (user) => {
    await api.toggleBan(user.id, !user.is_banned);
    showToast(user.is_banned ? 'User unbanned' : 'User banned');
    load(page);
  };

  const handleBalance = async (op) => {
    await api.updateBalance(balanceModal.id, amount, op);
    setBalanceModal(null); setAmount(0);
    showToast(`Balance ${op === 'add' ? 'added' : 'deducted'} successfully`);
    load(page);
  };

  const openDetails = async (user) => {
    setDetailsLoading(true);
    setDetailsTab('orders');
    setDetailsModal(null);
    try {
      const d = await api.getUserDetails(user.id);
      setDetailsModal(d);
    } catch (e) {
      showToast('Failed to load user details', 'error');
    }
    setDetailsLoading(false);
  };

  const statusBadge = (status) => {
    const colors = {
      delivered: 'badge-success', paid: 'badge-warning', waiting_payment: 'badge-neutral',
      canceled: 'badge-danger', under_review: 'badge-warning',
    };
    return <span className={`badge ${colors[status] || 'badge-neutral'}`}>{status}</span>;
  };

  return (
    <div>
      <h1 className="page-title">Users</h1>
      <p className="page-subtitle">Manage Telegram bot users</p>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 9999,
          padding: '12px 20px', borderRadius: 10,
          background: toast.type === 'error' ? 'var(--danger)' : 'var(--success)',
          color: '#fff', fontWeight: 600, fontSize: 13,
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)', animation: 'fadeIn 0.3s ease',
        }}>{toast.msg}</div>
      )}

      <div className="toolbar">
        <div className="search-box" style={{ width: 300 }}>
          <Search size={16} />
          <input placeholder="Search by username or ID..." value={search}
            onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === 'Enter' && load(1)} />
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{total} users</span>
      </div>

      {loading ? <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div> : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>User</th><th>Telegram ID</th><th>Balance</th><th>Spent</th>
                <th>Orders</th><th>Referrals</th><th>Ref. Earned</th>
                <th>Referred By</th><th>Joined</th><th>Status</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{u.display_name || u.username}</div>
                    {u.username !== 'N/A' && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>@{u.username}</div>}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{u.telegram_id}</td>
                  <td>${u.balance}</td>
                  <td style={{ color: 'var(--text-muted)' }}>${u.total_spent}</td>
                  <td>{u.total_orders}</td>
                  <td>
                    {u.referral_count > 0 ? (
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Users2 size={13} style={{ color: 'var(--accent)' }} /> {u.referral_count}
                      </span>
                    ) : '0'}
                  </td>
                  <td style={{ color: u.referral_earnings > 0 ? 'var(--success)' : 'var(--text-muted)' }}>
                    ${u.referral_earnings}
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {u.referred_by ? `@${u.referred_by}` : '—'}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{new Date(u.joined).toLocaleDateString()}</td>
                  <td>{u.is_banned ? <span className="badge badge-danger">Banned</span> : <span className="badge badge-success">Active</span>}</td>
                  <td>
                    <div className="flex gap-2">
                      <button className="btn btn-secondary btn-sm" title="View Details" onClick={() => openDetails(u)}>
                        <Eye size={13} />
                      </button>
                      <button className="btn btn-secondary btn-sm" title="Manage Balance" onClick={() => { setBalanceModal(u); setAmount(0); }}>
                        <DollarSign size={13} />
                      </button>
                      <button className={`btn ${u.is_banned ? 'btn-success' : 'btn-danger'} btn-sm`} title={u.is_banned ? 'Unban' : 'Ban'} onClick={() => toggleBan(u)}>
                        <Ban size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="pagination">
        {Array.from({ length: pages }, (_, i) => (
          <button key={i} className={`page-btn ${page === i+1 ? 'active' : ''}`} onClick={() => load(i+1)}>{i+1}</button>
        ))}
      </div>

      {/* Balance Modal */}
      {balanceModal && (
        <div className="modal-overlay" onClick={() => setBalanceModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">Manage Balance — {balanceModal.display_name || `@${balanceModal.username}`}</h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>Current: <strong>${balanceModal.balance}</strong></p>
            <div className="input-group">
              <label className="input-label">Amount</label>
              <input className="input" type="number" step="0.01" value={amount} onChange={e => setAmount(parseFloat(e.target.value) || 0)} />
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setBalanceModal(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={() => handleBalance('deduct')}>Deduct</button>
              <button className="btn btn-success" onClick={() => handleBalance('add')}>Add</button>
            </div>
          </div>
        </div>
      )}

      {/* Details Loading Overlay */}
      {detailsLoading && (
        <div className="modal-overlay">
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>
        </div>
      )}

      {/* User Details Modal */}
      {detailsModal && (
        <div className="modal-overlay" onClick={() => setDetailsModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 700, maxHeight: '85vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h2 className="modal-title" style={{ margin: 0 }}>{detailsModal.user.display_name}</h2>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  @{detailsModal.user.username} · ID: {detailsModal.user.telegram_id}
                  {detailsModal.user.is_premium && <span className="badge badge-warning" style={{ marginLeft: 8 }}>Premium</span>}
                </div>
              </div>
              <button onClick={() => setDetailsModal(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>

            {/* Stats Row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 16 }}>
              {[
                { label: 'Total Spent', value: `$${detailsModal.stats.total_spent}`, color: 'var(--accent)' },
                { label: 'Orders', value: `${detailsModal.stats.delivered_orders}/${detailsModal.stats.total_orders}`, color: 'var(--success)' },
                { label: 'Referrals', value: detailsModal.stats.referral_count, color: 'var(--warning)' },
                { label: 'Ref. Earned', value: `$${detailsModal.stats.referral_earnings}`, color: 'var(--info, #60a5fa)' },
              ].map((s, i) => (
                <div key={i} style={{
                  textAlign: 'center', padding: '10px 8px', borderRadius: 10,
                  background: 'var(--bg)', border: '1px solid var(--border)',
                }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Referred By */}
            {detailsModal.referred_by && (
              <div style={{
                padding: '8px 14px', borderRadius: 8, marginBottom: 12,
                background: 'var(--accent-bg)', border: '1px solid var(--accent)',
                fontSize: 13, display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <Users2 size={14} /> Referred by: <strong>@{detailsModal.referred_by.username || detailsModal.referred_by.name}</strong>
              </div>
            )}

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 0, borderBottom: '2px solid var(--border)', marginBottom: 12 }}>
              {[
                { key: 'orders', label: 'Orders', icon: ShoppingBag, count: detailsModal.orders.length },
                { key: 'referrals', label: 'Referrals', icon: Users2, count: detailsModal.referrals.length },
                { key: 'wallet', label: 'Wallet', icon: Wallet, count: detailsModal.transactions.length },
              ].map(tab => (
                <button key={tab.key} onClick={() => setDetailsTab(tab.key)}
                  style={{
                    padding: '8px 18px', border: 'none', cursor: 'pointer',
                    background: 'none', fontSize: 13, fontWeight: 600,
                    color: detailsTab === tab.key ? 'var(--accent)' : 'var(--text-muted)',
                    borderBottom: detailsTab === tab.key ? '2px solid var(--accent)' : '2px solid transparent',
                    marginBottom: -2, display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                  <tab.icon size={14} /> {tab.label}
                  <span style={{
                    fontSize: 11, padding: '1px 6px', borderRadius: 8,
                    background: 'var(--border)', color: 'var(--text-muted)',
                  }}>{tab.count}</span>
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div style={{ flex: 1, overflow: 'auto', maxHeight: '40vh' }}>
              {/* Orders Tab */}
              {detailsTab === 'orders' && (
                <table style={{ width: '100%' }}>
                  <thead><tr><th>Order #</th><th>Product</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead>
                  <tbody>
                    {detailsModal.orders.map(o => (
                      <tr key={o.id}>
                        <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{o.order_number}</td>
                        <td style={{ fontWeight: 600 }}>{o.product_name}</td>
                        <td>${o.amount}</td>
                        <td>{statusBadge(o.status)}</td>
                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(o.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                    {detailsModal.orders.length === 0 && <tr><td colSpan={5} className="empty-state">No orders yet</td></tr>}
                  </tbody>
                </table>
              )}

              {/* Referrals Tab */}
              {detailsTab === 'referrals' && (
                <table style={{ width: '100%' }}>
                  <thead><tr><th>Invited User</th><th>Commission</th><th>Earned</th><th>Orders</th><th>Status</th><th>Date</th></tr></thead>
                  <tbody>
                    {detailsModal.referrals.map(r => (
                      <tr key={r.id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{r.referred_name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>@{r.referred_username}</div>
                        </td>
                        <td>{r.commission_percent}%</td>
                        <td style={{ color: 'var(--success)', fontWeight: 600 }}>${r.total_earned}</td>
                        <td>{r.total_orders}</td>
                        <td><span className={`badge ${r.status === 'active' ? 'badge-success' : 'badge-danger'}`}>{r.status}</span></td>
                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(r.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                    {detailsModal.referrals.length === 0 && <tr><td colSpan={6} className="empty-state">No referrals yet</td></tr>}
                  </tbody>
                </table>
              )}

              {/* Wallet Tab */}
              {detailsTab === 'wallet' && (
                <table style={{ width: '100%' }}>
                  <thead><tr><th>Type</th><th>Amount</th><th>Balance After</th><th>Description</th><th>Date</th></tr></thead>
                  <tbody>
                    {detailsModal.transactions.map(tx => (
                      <tr key={tx.id}>
                        <td>
                          <span className={`badge ${tx.amount >= 0 ? 'badge-success' : 'badge-danger'}`}>
                            {tx.type.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td style={{ fontWeight: 600, color: tx.amount >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                          {tx.amount >= 0 ? '+' : ''}{tx.amount}
                        </td>
                        <td>${tx.balance_after}</td>
                        <td style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {tx.description}
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(tx.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                    {detailsModal.transactions.length === 0 && <tr><td colSpan={5} className="empty-state">No transactions yet</td></tr>}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
