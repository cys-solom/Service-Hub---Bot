import { useState, useEffect, useMemo } from 'react';
import { Users2, DollarSign, ToggleLeft, ToggleRight, Percent, ChevronUp, ChevronDown, Trash2, Trophy, ArrowUpDown, Shield, UserCheck } from 'lucide-react';
import api from '../services/api';

export default function Referrals() {
  const [referrals, setReferrals] = useState([]);
  const [stats, setStats] = useState({});
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [editCommission, setEditCommission] = useState(null);
  const [commissionVal, setCommissionVal] = useState('');
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [r, s, cfg] = await Promise.all([
        api.getReferrals(), api.getReferralStats(), api.getReferralSettings()
      ]);
      setReferrals(r.referrals);
      setStats(s);
      setSettings(cfg);
    } catch (e) {
      showToast('Failed to load data', 'error');
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  // Sorting
  const sorted = useMemo(() => {
    return [...referrals].sort((a, b) => {
      let va = a[sortKey], vb = b[sortKey];
      if (typeof va === 'string') va = va.toLowerCase();
      if (typeof vb === 'string') vb = vb.toLowerCase();
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [referrals, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <ArrowUpDown size={12} style={{ opacity: 0.3 }} />;
    return sortDir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  };

  // Selection
  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const toggleAll = () => {
    if (selected.size === sorted.length) setSelected(new Set());
    else setSelected(new Set(sorted.map(r => r.id)));
  };

  // Actions
  const handleToggleSystem = async () => {
    setSaving(true);
    await api.updateReferralSettings({ referral_enabled: !settings.referral_enabled });
    setSettings(s => ({ ...s, referral_enabled: !s.referral_enabled }));
    showToast(settings.referral_enabled ? 'Referral system disabled' : 'Referral system enabled');
    setSaving(false);
  };

  const handleAutoCredit = async () => {
    setSaving(true);
    await api.updateReferralSettings({ referral_auto_credit: !settings.referral_auto_credit });
    setSettings(s => ({ ...s, referral_auto_credit: !s.referral_auto_credit }));
    showToast('Auto-credit updated');
    setSaving(false);
  };

  const handleCommissionSave = async () => {
    const val = parseFloat(commissionVal);
    if (isNaN(val) || val < 0 || val > 100) return;
    setSaving(true);
    await api.updateReferralSettings({ referral_commission_percent: val });
    setSettings(s => ({ ...s, referral_commission_percent: val }));
    showToast(`Default commission set to ${val}%`);
    setSaving(false);
  };

  const handlePairCommission = async (id) => {
    const val = parseFloat(commissionVal);
    if (isNaN(val) || val < 0 || val > 100) return;
    await api.updateReferralCommission(id, val);
    setReferrals(refs => refs.map(r => r.id === id ? { ...r, commission_percent: val } : r));
    setEditCommission(null);
    showToast('Commission updated');
  };

  const handleToggleStatus = async (r) => {
    const newStatus = r.status === 'active' ? 'inactive' : 'active';
    await api.updateReferralStatus(r.id, newStatus);
    setReferrals(refs => refs.map(x => x.id === r.id ? { ...x, status: newStatus } : x));
    showToast(`Referral ${newStatus}`);
  };

  const handleBulkDelete = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} referral(s)?`)) return;
    await api.bulkDeleteReferrals([...selected]);
    setReferrals(refs => refs.filter(r => !selected.has(r.id)));
    setSelected(new Set());
    showToast('Deleted successfully');
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Referral System</h1>
      <p className="page-subtitle">Manage referral program, commissions, and performance tracking</p>

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

      {/* Settings Controls */}
      <div style={{
        background: 'var(--card-bg)', border: '1px solid var(--border)',
        borderRadius: 12, padding: '20px 24px', marginBottom: 24,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
          {/* Enable/Disable Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>System</span>
            <button
              onClick={handleToggleSystem} disabled={saving}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13,
                background: settings.referral_enabled ? 'var(--success-bg)' : 'var(--danger-bg)',
                color: settings.referral_enabled ? 'var(--success)' : 'var(--danger)',
              }}
            >
              {settings.referral_enabled ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
              {settings.referral_enabled ? 'Enabled' : 'Disabled'}
            </button>
          </div>

          {/* Auto Credit Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Auto Credit</span>
            <button
              onClick={handleAutoCredit} disabled={saving}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13,
                background: settings.referral_auto_credit ? 'var(--success-bg)' : 'var(--danger-bg)',
                color: settings.referral_auto_credit ? 'var(--success)' : 'var(--danger)',
              }}
            >
              {settings.referral_auto_credit ? <ToggleRight size={16} /> : <ToggleLeft size={16} />}
              {settings.referral_auto_credit ? 'On' : 'Off'}
            </button>
          </div>

          {/* Default Commission */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>Commission</span>
            <input
              type="number" step="0.5" min="0" max="100"
              defaultValue={settings.referral_commission_percent}
              onChange={e => setCommissionVal(e.target.value)}
              style={{
                width: 70, padding: '6px 10px', borderRadius: 8,
                border: '1px solid var(--border)', background: 'var(--bg)',
                color: 'var(--text)', fontSize: 13, textAlign: 'center',
              }}
            />
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>%</span>
            <button className="btn btn-primary btn-sm" onClick={handleCommissionSave} disabled={saving}
              style={{ padding: '5px 12px', fontSize: 12 }}>Save</button>
          </div>

          {/* Bulk Delete */}
          {selected.size > 0 && (
            <button className="btn btn-danger btn-sm" onClick={handleBulkDelete}
              style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Trash2 size={14} /> Delete ({selected.size})
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div><div className="stat-label">Total Referrals</div><div className="stat-value">{stats.total_referrals || 0}</div></div>
          <div className="stat-icon" style={{ background: 'var(--accent-bg)', color: 'var(--accent)' }}><Users2 size={22} /></div>
        </div>
        <div className="stat-card">
          <div><div className="stat-label">Active</div><div className="stat-value">{stats.active_referrals || 0}</div></div>
          <div className="stat-icon" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}><UserCheck size={22} /></div>
        </div>
        <div className="stat-card">
          <div><div className="stat-label">Total Earned</div><div className="stat-value">${stats.total_earned || 0}</div></div>
          <div className="stat-icon" style={{ background: 'var(--warning-bg)', color: 'var(--warning)' }}><DollarSign size={22} /></div>
        </div>
        <div className="stat-card">
          <div><div className="stat-label">Orders via Referral</div><div className="stat-value">{stats.total_orders || 0}</div></div>
          <div className="stat-icon" style={{ background: 'var(--info-bg, #1e3a5f)', color: 'var(--info, #60a5fa)' }}><Shield size={22} /></div>
        </div>
      </div>

      {/* Top Referrers */}
      {stats.top_referrers && stats.top_referrers.length > 0 && (
        <div style={{
          background: 'var(--card-bg)', border: '1px solid var(--border)',
          borderRadius: 12, padding: '16px 20px', marginBottom: 24,
        }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Trophy size={16} style={{ color: 'var(--warning)' }} /> Top Referrers
          </h3>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {stats.top_referrers.map((t, i) => (
              <div key={t.user_id} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '8px 16px',
                borderRadius: 10, background: 'var(--bg)',
                border: '1px solid var(--border)', minWidth: 180,
              }}>
                <span style={{
                  width: 26, height: 26, borderRadius: '50%',
                  background: i === 0 ? '#fbbf24' : i === 1 ? '#94a3b8' : i === 2 ? '#d97706' : 'var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 800, color: i < 3 ? '#000' : 'var(--text-muted)',
                }}>
                  {i + 1}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{t.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {t.referral_count} invites · ${t.total_earned}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Referrals Table */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th style={{ width: 40 }}>
                <input type="checkbox" checked={selected.size === sorted.length && sorted.length > 0}
                  onChange={toggleAll} />
              </th>
              <th onClick={() => toggleSort('referrer_name')} style={{ cursor: 'pointer' }}>
                Referrer <SortIcon col="referrer_name" />
              </th>
              <th onClick={() => toggleSort('referred_name')} style={{ cursor: 'pointer' }}>
                Referred <SortIcon col="referred_name" />
              </th>
              <th onClick={() => toggleSort('commission_percent')} style={{ cursor: 'pointer' }}>
                Commission <SortIcon col="commission_percent" />
              </th>
              <th onClick={() => toggleSort('total_earned')} style={{ cursor: 'pointer' }}>
                Earned <SortIcon col="total_earned" />
              </th>
              <th onClick={() => toggleSort('referred_orders')} style={{ cursor: 'pointer' }}>
                Ref. Orders <SortIcon col="referred_orders" />
              </th>
              <th onClick={() => toggleSort('referred_spent')} style={{ cursor: 'pointer' }}>
                Ref. Spent <SortIcon col="referred_spent" />
              </th>
              <th onClick={() => toggleSort('status')} style={{ cursor: 'pointer' }}>
                Status <SortIcon col="status" />
              </th>
              <th onClick={() => toggleSort('created_at')} style={{ cursor: 'pointer' }}>
                Date <SortIcon col="created_at" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(r => (
              <tr key={r.id}>
                <td><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelect(r.id)} /></td>
                <td>
                  <div style={{ fontWeight: 600 }}>{r.referrer_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>@{r.referrer_username}</div>
                </td>
                <td>
                  <div>{r.referred_name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>@{r.referred_username}</div>
                </td>
                <td>
                  {editCommission === r.id ? (
                    <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                      <input type="number" step="0.5" min="0" max="100"
                        value={commissionVal} onChange={e => setCommissionVal(e.target.value)}
                        style={{ width: 55, padding: '3px 6px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontSize: 12 }}
                        onKeyDown={e => e.key === 'Enter' && handlePairCommission(r.id)}
                        autoFocus
                      />
                      <button className="btn btn-primary btn-sm" style={{ padding: '2px 8px', fontSize: 11 }}
                        onClick={() => handlePairCommission(r.id)}>✓</button>
                      <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: 11 }}
                        onClick={() => setEditCommission(null)}>✕</button>
                    </div>
                  ) : (
                    <span style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                      onClick={() => { setEditCommission(r.id); setCommissionVal(r.commission_percent.toString()); }}>
                      <Percent size={12} style={{ color: 'var(--accent)' }} /> {r.commission_percent}%
                    </span>
                  )}
                </td>
                <td style={{ fontWeight: 600, color: 'var(--success)' }}>${r.total_earned}</td>
                <td>{r.referred_orders}</td>
                <td>${r.referred_spent}</td>
                <td>
                  <span
                    onClick={() => handleToggleStatus(r)}
                    className={`badge ${r.status === 'active' ? 'badge-success' : 'badge-danger'}`}
                    style={{ cursor: 'pointer' }}
                  >
                    {r.status}
                  </span>
                </td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr><td colSpan={9} className="empty-state">No referrals yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
