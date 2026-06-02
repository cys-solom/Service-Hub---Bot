import { useState, useEffect } from 'react';
import { Plus, Database, Download, Trash2 } from 'lucide-react';
import api from '../services/api';

export default function Backups() {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = () => api.getBackups().then(d => { setBackups(d.backups); setLoading(false); });
  useEffect(() => { load(); }, []);

  const createBackup = async () => {
    await api.createBackup();
    showToast('✅ Backup queued!');
    load();
  };

  const handleDelete = async (id) => {
    if (deleteId !== id) { setDeleteId(id); return; }
    setDeleteId(null);
    try {
      await api.deleteBackup(id);
      showToast('🗑️ Backup deleted');
      load();
    } catch (e) {
      showToast(`❌ ${e.message}`, 'error');
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 9999,
          padding: '14px 24px', borderRadius: 12,
          background: toast.type === 'error' ? 'rgba(255,69,58,0.95)' : 'rgba(48,209,88,0.95)',
          color: '#fff', fontWeight: 600, fontSize: 14,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          animation: 'slideIn 0.3s ease',
        }}>
          {toast.msg}
        </div>
      )}

      <h1 className="page-title">Backups</h1>
      <p className="page-subtitle">Database backups and restore points</p>
      <div className="toolbar">
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{backups.length} backups</span>
        <button className="btn btn-primary" onClick={createBackup}><Plus size={16} /> Create Backup</button>
      </div>
      <div className="table-wrapper">
        <table>
          <thead><tr><th>Filename</th><th>Type</th><th>Size</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
          <tbody>
            {backups.map(b => (
              <tr key={b.id}>
                <td style={{ fontWeight: 500, fontFamily: 'monospace', fontSize: 12 }}><Database size={14} style={{ marginRight: 8, opacity: .5 }} />{b.filename}</td>
                <td><span className="badge badge-neutral">{b.type}</span></td>
                <td>{formatBytes(b.size_bytes)}</td>
                <td><span className={`badge ${b.status === 'completed' ? 'badge-success' : b.status === 'queued' ? 'badge-warning' : 'badge-danger'}`}>{b.status}</span></td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(b.created_at).toLocaleString()}</td>
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button className="btn btn-secondary btn-sm"><Download size={13} /></button>
                    {deleteId === b.id ? (
                      <>
                        <button className="btn btn-sm" onClick={() => handleDelete(b.id)}
                          style={{ background: '#ff453a', color: '#fff', border: 'none', fontSize: 11, padding: '4px 10px' }}>
                          Confirm
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => setDeleteId(null)}
                          style={{ fontSize: 11, padding: '4px 8px' }}>
                          ✕
                        </button>
                      </>
                    ) : (
                      <button className="btn btn-secondary btn-sm" onClick={() => handleDelete(b.id)}
                        style={{ color: '#ff453a' }}>
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {backups.length === 0 && <tr><td colSpan={6} className="empty-state">No backups yet</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
