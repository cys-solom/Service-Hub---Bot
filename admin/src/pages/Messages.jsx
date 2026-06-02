import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Eye } from 'lucide-react';
import api from '../services/api';

export default function Messages() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [preview, setPreview] = useState(null);
  const [form, setForm] = useState({ key: '', type: 'text', content: '', parse_mode: 'HTML', is_active: true, group: 'general' });

  const load = () => api.getMessages().then(d => { setMessages(d.messages); setLoading(false); });
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    if (modal === 'edit') await api.updateMessage(form.id, form);
    else await api.createMessage(form);
    setModal(null); load();
  };

  const renderPreview = (content) => {
    return content
      .replace(/{user_name}/g, '<strong>John</strong>')
      .replace(/{product_name}/g, '<strong>Netflix Premium</strong>')
      .replace(/{price}/g, '<strong>$4.99</strong>')
      .replace(/{order_id}/g, '<strong>#ORD-001</strong>')
      .replace(/{qty}/g, '<strong>1</strong>')
      .replace(/{store_name}/g, '<strong>Service Hub</strong>')
      .replace(/{delivery_data}/g, '<code>account@email.com:password123</code>')
      .replace(/{wallet_address}/g, '<code>TXyz...abc</code>')
      .replace(/{payment_note}/g, '<code>PAY-12345</code>')
      .replace(/{timeout}/g, '30')
      .replace(/{stock_count}/g, '15');
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Messages Manager</h1>
      <p className="page-subtitle">Edit bot messages with live preview. Use placeholders like {'{user_name}'}, {'{product_name}'}, {'{price}'}</p>
      <div className="toolbar">
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{messages.length} templates</span>
        <button className="btn btn-primary" onClick={() => { setForm({ key: '', type: 'text', content: '', parse_mode: 'HTML', is_active: true, group: 'general' }); setModal('create'); }}>
          <Plus size={16} /> Add Message
        </button>
      </div>

      <div className="table-wrapper">
        <table>
          <thead><tr><th>Key</th><th>Type</th><th>Group</th><th>Active</th><th>Actions</th></tr></thead>
          <tbody>
            {messages.map(m => (
              <tr key={m.id}>
                <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>{m.key}</td>
                <td><span className="badge badge-neutral">{m.type}</span></td>
                <td style={{ color: 'var(--text-muted)' }}>{m.group}</td>
                <td><div className={`toggle ${m.is_active ? 'active' : ''}`} onClick={async () => { await api.updateMessage(m.id, { ...m, is_active: !m.is_active }); load(); }} /></td>
                <td>
                  <div className="flex gap-2">
                    <button className="btn btn-secondary btn-sm" onClick={() => setPreview(m)}><Eye size={13} /></button>
                    <button className="btn btn-secondary btn-sm" onClick={() => { setForm({ ...m }); setModal('edit'); }}><Edit2 size={13} /></button>
                    <button className="btn btn-danger btn-sm" onClick={async () => { if (confirm('Delete?')) { await api.deleteMessage(m.id); load(); } }}><Trash2 size={13} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {preview && (
        <div className="modal-overlay" onClick={() => setPreview(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">Preview — {preview.key}</h2>
            <div style={{ background: 'var(--bg-input)', padding: 16, borderRadius: 'var(--radius-md)', fontSize: 14, lineHeight: 1.6 }}
              dangerouslySetInnerHTML={{ __html: renderPreview(preview.content) }} />
            <div className="modal-actions"><button className="btn btn-secondary" onClick={() => setPreview(null)}>Close</button></div>
          </div>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ minWidth: 600 }}>
            <h2 className="modal-title">{modal === 'edit' ? 'Edit' : 'New'} Message</h2>
            <div className="grid-2">
              <div className="input-group"><label className="input-label">Key</label>
                <input className="input" value={form.key} onChange={e => setForm({ ...form, key: e.target.value })} placeholder="welcome" /></div>
              <div className="input-group"><label className="input-label">Type</label>
                <select className="select" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
                  <option value="text">Text</option><option value="photo">Photo</option><option value="video">Video</option><option value="document">Document</option>
                </select></div>
            </div>
            <div className="grid-2">
              <div>
                <div className="input-group"><label className="input-label">Content</label>
                  <textarea className="textarea" style={{ minHeight: 180 }} value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} /></div>
              </div>
              <div>
                <label className="input-label">Live Preview</label>
                <div style={{ background: 'var(--bg-input)', padding: 12, borderRadius: 'var(--radius-md)', fontSize: 13, lineHeight: 1.6, minHeight: 180 }}
                  dangerouslySetInnerHTML={{ __html: renderPreview(form.content) }} />
              </div>
            </div>
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
