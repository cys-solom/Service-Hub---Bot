import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Terminal, Shield, Users, Filter } from 'lucide-react';
import api from '../services/api';

const CATEGORIES = [
  { value: 'all', label: '📋 All', color: '#8b5cf6' },
  { value: 'navigation', label: '🧭 Navigation', color: '#3b82f6' },
  { value: 'wallet', label: '💰 Wallet', color: '#10b981' },
  { value: 'orders', label: '📦 Orders', color: '#f59e0b' },
  { value: 'admin', label: '🔐 Admin', color: '#ef4444' },
  { value: 'system', label: '⚙️ System', color: '#6b7280' },
  { value: 'general', label: '📝 General', color: '#8b5cf6' },
];

export default function Commands() {
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [activeTab, setActiveTab] = useState('all');
  const [form, setForm] = useState({
    command: '', description: '', is_enabled: true, is_admin: false,
    category: 'general', cooldown_seconds: 0, sort_order: 0,
  });

  const load = () => api.getCommands().then(d => { setCommands(d.commands); setLoading(false); });
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    try {
      if (modal === 'edit') await api.updateCommand(form.id, form);
      else await api.createCommand(form);
      setModal(null); load();
    } catch (e) {
      alert(e.message || 'Error saving command');
    }
  };

  const filtered = activeTab === 'all'
    ? commands
    : commands.filter(c => c.category === activeTab);

  const adminCmds = commands.filter(c => c.is_admin);
  const userCmds = commands.filter(c => !c.is_admin);

  const resetForm = () => ({
    command: '', description: '', is_enabled: true, is_admin: false,
    category: 'general', cooldown_seconds: 0, sort_order: 0,
  });

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Commands Manager</h1>
      <p className="page-subtitle">Manage bot commands, categorize them, and control admin access</p>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{
          padding: '10px 16px', borderRadius: 8, background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Terminal size={16} style={{ color: 'var(--primary)' }} />
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Total: <b style={{ color: 'var(--text-primary)' }}>{commands.length}</b></span>
        </div>
        <div style={{
          padding: '10px 16px', borderRadius: 8, background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Users size={16} style={{ color: '#10b981' }} />
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>User: <b style={{ color: '#10b981' }}>{userCmds.length}</b></span>
        </div>
        <div style={{
          padding: '10px 16px', borderRadius: 8, background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Shield size={16} style={{ color: '#ef4444' }} />
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Admin: <b style={{ color: '#ef4444' }}>{adminCmds.length}</b></span>
        </div>
      </div>

      {/* Category Tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
        {CATEGORIES.map(cat => (
          <button key={cat.value} onClick={() => setActiveTab(cat.value)}
            style={{
              padding: '6px 14px', borderRadius: 6, border: '2px solid',
              cursor: 'pointer', fontSize: 12, fontWeight: 600, transition: 'all 0.2s',
              background: activeTab === cat.value ? `${cat.color}20` : 'transparent',
              borderColor: activeTab === cat.value ? cat.color : 'var(--border-color)',
              color: activeTab === cat.value ? cat.color : 'var(--text-muted)',
            }}>
            {cat.label}
            {activeTab !== 'all' ? '' : (() => {
              const count = cat.value === 'all' ? commands.length : commands.filter(c => c.category === cat.value).length;
              return count > 0 ? ` (${count})` : '';
            })()}
          </button>
        ))}
      </div>

      <div className="toolbar">
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          {filtered.length} commands {activeTab !== 'all' ? `in ${activeTab}` : ''}
        </span>
        <button className="btn btn-primary" onClick={() => { setForm(resetForm()); setModal('create'); }}>
          <Plus size={16} /> Add Command
        </button>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Command</th><th>Description</th><th>Category</th>
              <th>Access</th><th>Cooldown</th><th>Status</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(c => {
              const cat = CATEGORIES.find(ct => ct.value === c.category) || CATEGORIES[6];
              return (
                <tr key={c.id}>
                  <td style={{ fontWeight: 700, fontFamily: 'monospace', fontSize: 14, color: 'var(--primary)' }}>
                    /{c.command}
                  </td>
                  <td style={{ color: 'var(--text-muted)', maxWidth: 200 }}>{c.description || '—'}</td>
                  <td>
                    <span style={{
                      padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                      background: `${cat.color}15`, color: cat.color,
                    }}>
                      {cat.label}
                    </span>
                  </td>
                  <td>
                    {c.is_admin ? (
                      <span style={{
                        padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                        background: 'rgba(239,68,68,0.15)', color: '#ef4444',
                      }}>🔐 Admin Only</span>
                    ) : (
                      <span style={{
                        padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        background: 'rgba(16,185,129,0.15)', color: '#10b981',
                      }}>👥 Everyone</span>
                    )}
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{c.cooldown_seconds > 0 ? `${c.cooldown_seconds}s` : '—'}</td>
                  <td>
                    <div className={`toggle ${c.is_enabled ? 'active' : ''}`}
                      onClick={async () => { await api.updateCommand(c.id, { ...c, is_enabled: !c.is_enabled }); load(); }} />
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => { setForm({ ...c }); setModal('edit'); }}>
                        <Edit2 size={13} />
                      </button>
                      <button className="btn btn-secondary btn-sm" style={{ color: '#ff453a' }}
                        onClick={async () => { if (confirm('Delete this command?')) { await api.deleteCommand(c.id); load(); } }}>
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                <Terminal size={40} style={{ opacity: 0.3, display: 'block', margin: '0 auto 8px' }} />
                No commands in this category
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <h2 className="modal-title">{modal === 'edit' ? '✏️ Edit' : '🆕 New'} Command</h2>

            <div className="grid-2">
              <div className="input-group">
                <label className="input-label">Command (without /)</label>
                <input className="input" value={form.command} placeholder="start"
                  onChange={e => setForm({ ...form, command: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })} />
              </div>
              <div className="input-group">
                <label className="input-label">Category</label>
                <select className="select" value={form.category}
                  onChange={e => setForm({ ...form, category: e.target.value })}>
                  {CATEGORIES.filter(c => c.value !== 'all').map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="input-group">
              <label className="input-label">Description</label>
              <input className="input" value={form.description || ''} placeholder="What does this command do?"
                onChange={e => setForm({ ...form, description: e.target.value })} />
            </div>

            <div className="grid-2">
              <div className="input-group">
                <label className="input-label">Cooldown (seconds)</label>
                <input className="input" type="number" value={form.cooldown_seconds}
                  onChange={e => setForm({ ...form, cooldown_seconds: parseInt(e.target.value) || 0 })} />
              </div>
              <div className="input-group">
                <label className="input-label">Sort Order</label>
                <input className="input" type="number" value={form.sort_order}
                  onChange={e => setForm({ ...form, sort_order: parseInt(e.target.value) || 0 })} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 20, marginTop: 8 }}>
              <div className="input-group" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <label className="input-label" style={{ marginBottom: 0 }}>Enabled</label>
                <div className={`toggle ${form.is_enabled ? 'active' : ''}`}
                  onClick={() => setForm({ ...form, is_enabled: !form.is_enabled })} />
              </div>
              <div className="input-group" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <label className="input-label" style={{ marginBottom: 0, color: '#ef4444' }}>🔐 Admin Only</label>
                <div className={`toggle ${form.is_admin ? 'active' : ''}`}
                  onClick={() => setForm({ ...form, is_admin: !form.is_admin })} />
              </div>
            </div>

            <div className="modal-actions" style={{ marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave}>
                {modal === 'edit' ? 'Update' : 'Create'} Command
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
