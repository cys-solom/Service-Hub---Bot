import { useState, useEffect } from 'react';
import { Plus, Edit2, Globe } from 'lucide-react';
import api from '../services/api';

export default function Providers() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({ name: '', code: '', api_url: '', api_key: '', is_enabled: true, description: '' });

  const load = () => api.getProviders().then(d => { setProviders(d.providers); setLoading(false); });
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (modal === 'edit') await api.updateProvider(form.id, form);
    else await api.createProvider(form);
    setModal(null); load();
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">External Providers</h1>
      <p className="page-subtitle">Connect to third-party APIs for automated stock fulfillment</p>
      <div className="toolbar">
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{providers.length} providers</span>
        <button className="btn btn-primary" onClick={() => { setForm({ name: '', code: '', api_url: '', api_key: '', is_enabled: true, description: '' }); setModal('create'); }}>
          <Plus size={16} /> Add Provider
        </button>
      </div>
      <div className="table-wrapper">
        <table>
          <thead><tr><th>Name</th><th>Code</th><th>API URL</th><th>Status</th><th>Last Sync</th><th>Actions</th></tr></thead>
          <tbody>
            {providers.map(p => (
              <tr key={p.id}>
                <td style={{ fontWeight: 600 }}><Globe size={14} style={{ marginRight: 8, opacity: .5 }} />{p.name}</td>
                <td><span className="badge badge-neutral">{p.code}</span></td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.api_url}</td>
                <td>{p.is_enabled ? <span className="badge badge-success">Active</span> : <span className="badge badge-danger">Disabled</span>}</td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{p.last_sync_at || 'Never'}</td>
                <td><button className="btn btn-secondary btn-sm" onClick={() => { setForm({ ...p }); setModal('edit'); }}><Edit2 size={13} /></button></td>
              </tr>
            ))}
            {providers.length === 0 && <tr><td colSpan={6} className="empty-state">No providers configured</td></tr>}
          </tbody>
        </table>
      </div>
      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">{modal === 'edit' ? 'Edit' : 'New'} Provider</h2>
            <div className="grid-2">
              <div className="input-group"><label className="input-label">Name</label>
                <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
              <div className="input-group"><label className="input-label">Code</label>
                <input className="input" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} placeholder="mmostore" /></div>
            </div>
            <div className="input-group"><label className="input-label">API URL</label>
              <input className="input" value={form.api_url} onChange={e => setForm({ ...form, api_url: e.target.value })} /></div>
            <div className="input-group"><label className="input-label">API Key</label>
              <input className="input" type="password" value={form.api_key || ''} onChange={e => setForm({ ...form, api_key: e.target.value })} /></div>
            <div className="input-group"><label className="input-label">Description</label>
              <textarea className="textarea" value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} /></div>
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
