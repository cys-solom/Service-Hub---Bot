import { useState, useEffect } from 'react';
import { FileText } from 'lucide-react';
import api from '../services/api';

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = (p = 1) => {
    setLoading(true);
    api.getAuditLogs(p).then(d => { setLogs(d.logs); setTotal(d.total); setPage(p); setLoading(false); });
  };
  useEffect(() => { load(); }, []);

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Audit Logs</h1>
      <p className="page-subtitle">Track all admin actions and system events</p>
      <div className="table-wrapper">
        <table>
          <thead><tr><th>Actor</th><th>Action</th><th>Resource</th><th>Details</th><th>Date</th></tr></thead>
          <tbody>
            {logs.map(l => (
              <tr key={l.id}>
                <td><span className={`badge ${l.actor_type === 'admin' ? 'badge-info' : 'badge-neutral'}`}>{l.actor_type}</span> {l.actor_id}</td>
                <td style={{ fontWeight: 500 }}>{l.action}</td>
                <td style={{ color: 'var(--text-muted)' }}>{l.resource_type} {l.resource_id ? `#${l.resource_id.slice(0,8)}` : ''}</td>
                <td style={{ fontSize: 11, fontFamily: 'monospace', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {l.details ? JSON.stringify(l.details).slice(0, 60) : '—'}
                </td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(l.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={5} className="empty-state">No logs yet</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        {page > 1 && <button className="page-btn" onClick={() => load(page-1)}>Prev</button>}
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Page {page}</span>
        <button className="page-btn" onClick={() => load(page+1)}>Next</button>
      </div>
    </div>
  );
}
