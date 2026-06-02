import { useState, useEffect } from 'react';
import { Plus, Bell } from 'lucide-react';
import api from '../services/api';

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [logs, setLogs] = useState([]);
  const [tab, setTab] = useState('templates');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (tab === 'templates') api.getNotifications().then(d => { setNotifications(d.notifications); setLoading(false); });
  }, [tab]);

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Notifications</h1>
      <p className="page-subtitle">Configure notification templates and view delivery logs</p>
      <div className="tabs">
        <div className={`tab ${tab === 'templates' ? 'active' : ''}`} onClick={() => setTab('templates')}>Templates</div>
        <div className={`tab ${tab === 'logs' ? 'active' : ''}`} onClick={() => setTab('logs')}>Logs</div>
      </div>
      <div className="table-wrapper">
        <table>
          <thead><tr><th>Type</th><th>Target</th><th>Channel</th><th>Enabled</th></tr></thead>
          <tbody>
            {notifications.map(n => (
              <tr key={n.id}>
                <td style={{ fontWeight: 600 }}>{n.type}</td>
                <td><span className={`badge ${n.target === 'admin' ? 'badge-info' : 'badge-neutral'}`}>{n.target}</span></td>
                <td>{n.channel}</td>
                <td><div className={`toggle ${n.is_enabled ? 'active' : ''}`} /></td>
              </tr>
            ))}
            {notifications.length === 0 && <tr><td colSpan={4} className="empty-state">No notification templates</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
