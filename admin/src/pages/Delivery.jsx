import { useState, useEffect } from 'react';
import { Plus, Truck as TruckIcon } from 'lucide-react';
import api from '../services/api';

export default function Delivery() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({ name: '', mode: 'auto', description: '', template: '', is_default: false });

  const load = () => api.getDeliveryRules().then(d => { setRules(d.rules); setLoading(false); });
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    await api.createDeliveryRule(form);
    setModal(null); load();
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Delivery Config</h1>
      <p className="page-subtitle">Configure how products are delivered to customers</p>
      <div className="toolbar">
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{rules.length} rules</span>
        <button className="btn btn-primary" onClick={() => { setForm({ name: '', mode: 'auto', description: '', template: '', is_default: false }); setModal('create'); }}>
          <Plus size={16} /> Add Rule
        </button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
        {rules.map(r => (
          <div key={r.id} className="card">
            <div className="flex items-center justify-between mb-4">
              <strong>{r.name}</strong>
              <span className={`badge ${r.mode === 'auto' ? 'badge-success' : r.mode === 'manual' ? 'badge-warning' : 'badge-info'}`}>{r.mode}</span>
            </div>
            {r.description && <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>{r.description}</p>}
            {r.is_default && <span className="badge badge-neutral">Default</span>}
            {r.template && <div style={{ marginTop: 8, padding: 8, background: 'var(--bg-input)', borderRadius: 6, fontSize: 12, fontFamily: 'monospace' }}>{r.template}</div>}
          </div>
        ))}
      </div>
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">New Delivery Rule</h2>
            <div className="grid-2">
              <div className="input-group"><label className="input-label">Name</label>
                <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
              <div className="input-group"><label className="input-label">Mode</label>
                <select className="select" value={form.mode} onChange={e => setForm({ ...form, mode: e.target.value })}>
                  <option value="auto">Auto</option><option value="manual">Manual</option><option value="semi_auto">Semi-Auto</option>
                </select></div>
            </div>
            <div className="input-group"><label className="input-label">Template</label>
              <textarea className="textarea" value={form.template} onChange={e => setForm({ ...form, template: e.target.value })}
                placeholder="Use {delivery_data} for the stock content" /></div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
