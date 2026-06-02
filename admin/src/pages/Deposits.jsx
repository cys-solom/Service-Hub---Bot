import { useState, useEffect, useMemo } from 'react';
import { Check, X, Clock, DollarSign, RefreshCw, Trash2, ArrowUpDown, ArrowUp, ArrowDown, CheckSquare, Square, MinusSquare } from 'lucide-react';
import api from '../services/api';

const StatusBadge = ({ status }) => {
  const map = {
    pending: { bg: 'rgba(255,159,10,0.15)', color: '#ff9f0a', label: '⏳ Pending' },
    confirmed: { bg: 'rgba(48,209,88,0.15)', color: '#30d158', label: '✅ Approved' },
    failed: { bg: 'rgba(255,69,58,0.15)', color: '#ff453a', label: '❌ Rejected' },
  };
  const s = map[status] || { bg: 'rgba(99,99,102,0.15)', color: '#636366', label: status };
  return (
    <span style={{ padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600, background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
};

export default function Deposits() {
  const [deposits, setDeposits] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [toast, setToast] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const load = async (p = 1, s = filter) => {
    setLoading(true);
    setSelected(new Set());
    try {
      const d = await api.getPayments(p, 'deposit', s);
      setDeposits(d.payments); setTotal(d.total); setPage(p); setPages(d.pages);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  // Sort locally
  const sorted = useMemo(() => {
    const arr = [...deposits];
    arr.sort((a, b) => {
      let va = a[sortKey], vb = b[sortKey];
      if (sortKey === 'amount') { va = Number(va); vb = Number(vb); }
      if (sortKey === 'created_at') { va = new Date(va); vb = new Date(vb); }
      if (typeof va === 'string') { va = va.toLowerCase(); vb = (vb || '').toLowerCase(); }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return arr;
  }, [deposits, sortKey, sortDir]);

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
    else setSelected(new Set(sorted.map(d => d.id)));
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
      const res = await api.bulkDeletePayments([...selected]);
      showToast(`🗑️ Deleted ${res.deleted} record(s)`);
      load(page);
    } catch (e) {
      showToast(`❌ Error: ${e.message}`, 'error');
    }
    setBusy(null);
  };

  const handleApprove = async (id) => {
    setBusy(id);
    try {
      const res = await api.approveDeposit(id);
      showToast(`✅ ${res.message} — New balance: $${res.balance?.toFixed(2)}`);
      load(page);
    } catch (e) {
      showToast(`❌ Error: ${e.message}`, 'error');
    }
    setBusy(null);
  };

  const handleReject = async (id) => {
    setBusy(id);
    try {
      await api.rejectDeposit(id);
      showToast('❌ Deposit rejected');
      load(page);
    } catch (e) {
      showToast(`❌ Error: ${e.message}`, 'error');
    }
    setBusy(null);
  };

  const tabs = [
    { key: '', label: 'All' },
    { key: 'pending', label: '⏳ Pending' },
    { key: 'confirmed', label: '✅ Approved' },
    { key: 'failed', label: '❌ Rejected' },
  ];

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
          <h1 className="page-title">Deposit Requests</h1>
          <p className="page-subtitle" style={{ margin: 0 }}>Approve deposits to add balance • {total} requests</p>
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
          <button key={t.key} onClick={() => { setFilter(t.key); load(1, t.key); }}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: 600, transition: 'all 0.2s',
              background: filter === t.key ? 'var(--primary)' : 'var(--card-bg)',
              color: filter === t.key ? '#fff' : 'var(--text-muted)',
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
                <th><div style={thStyle} onClick={() => toggleSort('display_name')}>User <SortIcon col="display_name" /></div></th>
                <th><div style={thStyle} onClick={() => toggleSort('amount')}>Amount <SortIcon col="amount" /></div></th>
                <th><div style={thStyle} onClick={() => toggleSort('method_code')}>Method <SortIcon col="method_code" /></div></th>
                <th>Reference</th>
                <th><div style={thStyle} onClick={() => toggleSort('status')}>Status <SortIcon col="status" /></div></th>
                <th><div style={thStyle} onClick={() => toggleSort('created_at')}>Date <SortIcon col="created_at" /></div></th>
                <th style={{ minWidth: 180, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(d => (
                <tr key={d.id}
                  style={{
                    ...(d.status === 'pending' ? { background: 'rgba(255,159,10,0.05)', borderLeft: '3px solid #ff9f0a' } : {}),
                    ...(selected.has(d.id) ? { background: 'rgba(120,120,255,0.08)' } : {}),
                  }}>
                  <td>
                    <div onClick={() => toggleSelect(d.id)} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                      {selected.has(d.id) ?
                        <CheckSquare size={18} color="var(--primary)" /> :
                        <Square size={18} style={{ opacity: 0.3 }} />}
                    </div>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{d.display_name}</div>
                    {d.username && d.username !== d.display_name && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>@{d.username}</div>
                    )}
                  </td>
                  <td><strong style={{ color: 'var(--primary)', fontSize: 15 }}>${d.amount}</strong></td>
                  <td style={{ color: 'var(--text-muted)' }}>{d.method_code}</td>
                  <td>
                    <code style={{ fontSize: 11, background: 'rgba(0,0,0,0.2)', padding: '2px 6px', borderRadius: 4 }}>
                      {d.tx_note || '—'}
                    </code>
                  </td>
                  <td><StatusBadge status={d.status} /></td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{new Date(d.created_at).toLocaleString()}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      {d.status === 'pending' && (
                        <>
                          <button
                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleApprove(d.id); }}
                            disabled={busy === d.id}
                            style={{
                              padding: '6px 14px', borderRadius: 6, border: 'none', cursor: busy === d.id ? 'wait' : 'pointer',
                              background: '#30d158', color: '#fff', fontWeight: 600, fontSize: 12,
                              display: 'flex', alignItems: 'center', gap: 4,
                              opacity: busy === d.id ? 0.6 : 1, transition: 'all 0.2s',
                            }}>
                            {busy === d.id ? <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Check size={13} />}
                            {busy === d.id ? '...' : 'Approve'}
                          </button>
                          <button
                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleReject(d.id); }}
                            disabled={busy === d.id}
                            style={{
                              padding: '6px 14px', borderRadius: 6, border: 'none', cursor: busy === d.id ? 'wait' : 'pointer',
                              background: 'rgba(255,69,58,0.15)', color: '#ff453a', fontWeight: 600, fontSize: 12,
                              display: 'flex', alignItems: 'center', gap: 4,
                              opacity: busy === d.id ? 0.6 : 1, transition: 'all 0.2s',
                            }}>
                            <X size={13} /> Reject
                          </button>
                        </>
                      )}
                      {d.status === 'confirmed' && (
                        <span style={{ color: '#30d158', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Check size={14} /> Done
                        </span>
                      )}
                      {d.status === 'failed' && (
                        <span style={{ color: '#ff453a', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
                          <X size={14} /> Rejected
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {deposits.length === 0 && (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  <DollarSign size={40} style={{ opacity: 0.3, display: 'block', margin: '0 auto 8px' }} />
                  No deposit requests
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

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

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
