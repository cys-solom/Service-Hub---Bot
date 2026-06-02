import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Keyboard, Monitor, Eye, EyeOff, GripVertical } from 'lucide-react';
import api from '../services/api';

const ACTIONS = ['shop', 'menu', 'wallet', 'topup', 'orders', 'referral', 'apikey', 'language', 'support'];

export default function Buttons() {
  const [buttons, setButtons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [activeTab, setActiveTab] = useState('reply');
  const [form, setForm] = useState({
    key: '', text_en: '', text_ar: '', emoji: '📌', action: 'shop',
    row_order: 0, col_order: 0, is_enabled: true, keyboard_type: 'reply',
  });

  const load = async () => {
    const d = await api.getReplyButtons();
    setButtons(d.buttons);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const filtered = buttons.filter(b => b.keyboard_type === activeTab);

  const handleSave = async () => {
    try {
      if (modal === 'edit') await api.updateReplyButton(form.id, form);
      else await api.createReplyButton({ ...form, keyboard_type: activeTab });
      setModal(null); load();
    } catch (e) {
      alert(e.message || 'Error');
    }
  };

  const toggleEnabled = async (btn) => {
    await api.updateReplyButton(btn.id, { ...btn, is_enabled: !btn.is_enabled });
    load();
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this button?')) return;
    await api.deleteReplyButton(id);
    load();
  };

  const resetForm = () => ({
    key: '', text_en: '', text_ar: '', emoji: '📌', action: 'shop',
    row_order: 0, col_order: 0, is_enabled: true, keyboard_type: activeTab,
  });

  // Group buttons by row
  const groupByRow = (btns) => {
    const rows = {};
    btns.forEach(b => {
      if (!rows[b.row_order]) rows[b.row_order] = [];
      rows[b.row_order].push(b);
    });
    return Object.entries(rows).sort(([a], [b]) => a - b).map(([, v]) =>
      v.sort((a, b) => a.col_order - b.col_order)
    );
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  const rows = groupByRow(filtered);

  return (
    <div>
      <h1 className="page-title">Keyboard Buttons</h1>
      <p className="page-subtitle">Manage bot keyboard buttons — edit names, emojis, and enable/disable</p>

      {/* Tab Switcher */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button onClick={() => setActiveTab('reply')}
          style={{
            padding: '10px 20px', borderRadius: 8, border: '2px solid',
            cursor: 'pointer', fontWeight: 600, fontSize: 13, transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', gap: 6,
            background: activeTab === 'reply' ? 'rgba(99,102,241,0.15)' : 'transparent',
            borderColor: activeTab === 'reply' ? 'var(--primary)' : 'var(--border-color)',
            color: activeTab === 'reply' ? 'var(--primary)' : 'var(--text-muted)',
          }}>
          <Keyboard size={16} /> Reply Keyboard
          <span style={{
            background: 'var(--bg-secondary)', padding: '1px 6px', borderRadius: 4, fontSize: 11,
          }}>{buttons.filter(b => b.keyboard_type === 'reply').length}</span>
        </button>
        <button onClick={() => setActiveTab('inline')}
          style={{
            padding: '10px 20px', borderRadius: 8, border: '2px solid',
            cursor: 'pointer', fontWeight: 600, fontSize: 13, transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', gap: 6,
            background: activeTab === 'inline' ? 'rgba(16,185,129,0.15)' : 'transparent',
            borderColor: activeTab === 'inline' ? '#10b981' : 'var(--border-color)',
            color: activeTab === 'inline' ? '#10b981' : 'var(--text-muted)',
          }}>
          <Monitor size={16} /> Inline Menu
          <span style={{
            background: 'var(--bg-secondary)', padding: '1px 6px', borderRadius: 4, fontSize: 11,
          }}>{buttons.filter(b => b.keyboard_type === 'inline').length}</span>
        </button>
      </div>

      {/* Live Preview */}
      <div style={{
        background: 'var(--bg-secondary)', borderRadius: 12, padding: 20, marginBottom: 20,
        border: '1px solid var(--border-color)',
      }}>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10, fontWeight: 600 }}>
          {activeTab === 'reply' ? '⌨️ Reply Keyboard Preview' : '📱 Inline Menu Preview'}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxWidth: 400 }}>
          {rows.map((row, ri) => (
            <div key={ri} style={{ display: 'flex', gap: 4 }}>
              {row.map(btn => (
                <div key={btn.id} style={{
                  flex: 1, padding: '10px 8px', textAlign: 'center', fontSize: 13, fontWeight: 600,
                  borderRadius: 8, transition: 'all 0.2s',
                  background: btn.is_enabled
                    ? (activeTab === 'reply' ? 'rgba(99,102,241,0.12)' : 'rgba(16,185,129,0.12)')
                    : 'rgba(255,69,58,0.08)',
                  color: btn.is_enabled ? 'var(--text-primary)' : 'var(--text-muted)',
                  opacity: btn.is_enabled ? 1 : 0.5,
                  textDecoration: btn.is_enabled ? 'none' : 'line-through',
                  border: `1px solid ${btn.is_enabled ? 'var(--border-color)' : 'rgba(255,69,58,0.3)'}`,
                }}>
                  {btn.emoji} {btn.text_en}
                </div>
              ))}
            </div>
          ))}
          {rows.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20, fontSize: 13 }}>
              No buttons configured
            </div>
          )}
        </div>
      </div>

      {/* Toolbar */}
      <div className="toolbar">
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{filtered.length} buttons</span>
        <button className="btn btn-primary" onClick={() => { setForm(resetForm()); setModal('create'); }}>
          <Plus size={16} /> Add Button
        </button>
      </div>

      {/* Button Table */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Preview</th><th>Key</th><th>English</th><th>Arabic</th>
              <th>Action</th><th>Position</th><th>Visible</th><th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(b => (
              <tr key={b.id} style={{ opacity: b.is_enabled ? 1 : 0.6 }}>
                <td>
                  <span style={{
                    padding: '6px 14px', borderRadius: 6, fontWeight: 600, fontSize: 13,
                    background: b.is_enabled ? 'rgba(99,102,241,0.12)' : 'rgba(100,100,100,0.1)',
                    color: b.is_enabled ? 'var(--text-primary)' : 'var(--text-muted)',
                    display: 'inline-block',
                  }}>
                    {b.emoji} {b.text_en}
                  </span>
                </td>
                <td style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--primary)' }}>{b.key}</td>
                <td style={{ fontWeight: 500 }}>{b.text_en}</td>
                <td style={{ fontWeight: 500, direction: 'rtl' }}>{b.text_ar}</td>
                <td><span className="badge badge-neutral">{b.action}</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>Row {b.row_order}, Col {b.col_order}</td>
                <td>
                  <button onClick={() => toggleEnabled(b)}
                    style={{
                      padding: '4px 10px', borderRadius: 6, border: 'none', cursor: 'pointer',
                      fontSize: 11, fontWeight: 600, transition: 'all 0.2s',
                      background: b.is_enabled ? 'rgba(16,185,129,0.15)' : 'rgba(255,69,58,0.15)',
                      color: b.is_enabled ? '#10b981' : '#ff453a',
                    }}>
                    {b.is_enabled ? <><Eye size={12} /> Visible</> : <><EyeOff size={12} /> Hidden</>}
                  </button>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setForm({ ...b }); setModal('edit'); }}>
                      <Edit2 size={13} />
                    </button>
                    <button className="btn btn-secondary btn-sm" style={{ color: '#ff453a' }}
                      onClick={() => handleDelete(b.id)}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                <Keyboard size={40} style={{ opacity: 0.3, display: 'block', margin: '0 auto 8px' }} />
                No buttons in this keyboard
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal */}
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <h2 className="modal-title">{modal === 'edit' ? '✏️ Edit' : '🆕 New'} Button</h2>

            <div className="grid-2">
              <div className="input-group">
                <label className="input-label">Key (unique identifier)</label>
                <input className="input" value={form.key} placeholder="shop"
                  onChange={e => setForm({ ...form, key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })} />
              </div>
              <div className="input-group">
                <label className="input-label">Emoji</label>
                <input className="input" value={form.emoji} placeholder="🛍"
                  style={{ fontSize: 20, textAlign: 'center' }}
                  onChange={e => setForm({ ...form, emoji: e.target.value })} />
              </div>
            </div>

            <div className="grid-2">
              <div className="input-group">
                <label className="input-label">English Text</label>
                <input className="input" value={form.text_en} placeholder="Shop"
                  onChange={e => setForm({ ...form, text_en: e.target.value })} />
              </div>
              <div className="input-group">
                <label className="input-label">Arabic Text</label>
                <input className="input" value={form.text_ar} placeholder="المتجر" style={{ direction: 'rtl' }}
                  onChange={e => setForm({ ...form, text_ar: e.target.value })} />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label">Action</label>
              <select className="select" value={form.action} onChange={e => setForm({ ...form, action: e.target.value })}>
                {ACTIONS.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>

            <div className="grid-2">
              <div className="input-group">
                <label className="input-label">Row Order</label>
                <input className="input" type="number" value={form.row_order}
                  onChange={e => setForm({ ...form, row_order: parseInt(e.target.value) || 0 })} />
              </div>
              <div className="input-group">
                <label className="input-label">Column Order</label>
                <input className="input" type="number" value={form.col_order}
                  onChange={e => setForm({ ...form, col_order: parseInt(e.target.value) || 0 })} />
              </div>
            </div>

            {/* Preview */}
            <div style={{ marginTop: 8 }}>
              <label className="input-label">Preview</label>
              <div style={{
                padding: '12px 20px', borderRadius: 8, textAlign: 'center',
                background: 'rgba(99,102,241,0.12)', color: 'var(--text-primary)',
                fontWeight: 600, fontSize: 15,
              }}>
                {form.emoji} {form.text_en || 'Button Text'}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 12 }}>
              <label className="input-label" style={{ marginBottom: 0 }}>Visible</label>
              <div className={`toggle ${form.is_enabled ? 'active' : ''}`}
                onClick={() => setForm({ ...form, is_enabled: !form.is_enabled })} />
            </div>

            <div className="modal-actions" style={{ marginTop: 16 }}>
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave}>
                {modal === 'edit' ? 'Update' : 'Create'} Button
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
