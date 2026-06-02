import { useState, useEffect, useRef } from 'react';
import { MessageSquare, CheckCircle, XCircle, Send, Clock, AlertCircle, Inbox, Trash2, ArrowUp, ArrowDown, X, RefreshCw } from 'lucide-react';
import api from '../services/api';

const STATUS_BADGE = { open: 'badge-warning', in_progress: 'badge-info', resolved: 'badge-success', closed: 'badge-neutral' };
const PRIORITY_BADGE = { urgent: 'badge-danger', high: 'badge-warning', normal: 'badge-info', low: 'badge-neutral' };
const STATUS_EMOJI = { open: '📬', in_progress: '⏳', resolved: '✅', closed: '🔒' };

export default function Support() {
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState('');
  const [toast, setToast] = useState(null);
  const chatEndRef = useRef(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [d, s] = await Promise.all([api.getTickets(status), api.getTicketStats()]);
      setTickets(d.tickets);
      setStats(s);
    } catch (e) { showToast('Failed to load', 'error'); }
    setLoading(false);
  };

  useEffect(() => { load(); }, [status]);

  useEffect(() => {
    if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [detail]);

  const sendReply = async () => {
    if (!reply.trim() || sending) return;
    setSending(true);
    try {
      const res = await api.replyTicket(detail.id, reply);
      setReply('');
      setDetail(prev => ({ ...prev, replies: res.replies, status: prev.status === 'open' ? 'in_progress' : prev.status }));
      showToast('Reply sent & user notified! 🔔');
      load(); // Refresh list
    } catch (e) { showToast('Failed to send', 'error'); }
    setSending(false);
  };

  const changeStatus = async (id, s) => {
    await api.updateTicketStatus(id, s);
    showToast(`Status → ${s}`);
    load();
    if (detail?.id === id) setDetail(prev => ({ ...prev, status: s }));
  };

  const changePriority = async (id, p) => {
    await api.updateTicketPriority(id, p);
    showToast(`Priority → ${p}`);
    load();
    if (detail?.id === id) setDetail(prev => ({ ...prev, priority: p }));
  };

  const deleteTicket = async (id) => {
    if (!confirm('Delete this ticket?')) return;
    await api.deleteTicket(id);
    showToast('Deleted');
    if (detail?.id === id) setDetail(null);
    load();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendReply();
    }
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Support Tickets</h1>
      <p className="page-subtitle">Manage customer support — replies are sent to Telegram instantly</p>

      {toast && (
        <div style={{
          position: 'fixed', top: 24, right: 24, zIndex: 9999, padding: '12px 20px', borderRadius: 10,
          background: toast.type === 'error' ? 'var(--danger)' : 'var(--success)',
          color: '#fff', fontWeight: 600, fontSize: 13, boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
        }}>{toast.msg}</div>
      )}

      {/* Stats */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total', value: stats.total || 0, icon: Inbox, bg: 'var(--accent-bg)', color: 'var(--accent)' },
          { label: 'Open', value: stats.open || 0, icon: AlertCircle, bg: 'var(--warning-bg)', color: 'var(--warning)' },
          { label: 'In Progress', value: stats.in_progress || 0, icon: Clock, bg: '#1e3a5f', color: '#60a5fa' },
          { label: 'Resolved', value: stats.resolved || 0, icon: CheckCircle, bg: 'var(--success-bg)', color: 'var(--success)' },
        ].map((s, i) => (
          <div className="stat-card" key={i}>
            <div><div className="stat-label">{s.label}</div><div className="stat-value">{s.value}</div></div>
            <div className="stat-icon" style={{ background: s.bg, color: s.color }}><s.icon size={22} /></div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: 16 }}>
        {[
          { v: '', label: 'All' },
          { v: 'open', label: `Open (${stats.open || 0})` },
          { v: 'in_progress', label: `In Progress (${stats.in_progress || 0})` },
          { v: 'resolved', label: 'Resolved' },
          { v: 'closed', label: 'Closed' },
        ].map(s => (
          <div key={s.v} className={`tab ${status === s.v ? 'active' : ''}`} onClick={() => setStatus(s.v)}>{s.label}</div>
        ))}
        <button className="btn btn-secondary btn-sm" style={{ marginLeft: 'auto' }} onClick={load}><RefreshCw size={14} /></button>
      </div>

      {/* Table */}
      <div className="table-wrapper">
        <table>
          <thead><tr><th>User</th><th>Subject</th><th>Priority</th><th>Status</th><th>Replies</th><th>Date</th><th>Actions</th></tr></thead>
          <tbody>
            {tickets.map(t => {
              const hasAdminReply = (t.replies || []).some(r => r.sender === 'admin');
              const lastReply = (t.replies || []).at(-1);
              const isWaiting = lastReply?.sender === 'user' && t.status !== 'closed';
              return (
                <tr key={t.id} style={{ cursor: 'pointer', background: isWaiting ? 'rgba(234, 179, 8, 0.05)' : undefined }}
                  onClick={() => setDetail(t)}>
                  <td>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{t.display_name || t.user}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t.user}</div>
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {isWaiting && <span style={{ color: 'var(--warning)', marginRight: 4 }}>●</span>}
                    {t.subject}
                  </td>
                  <td>
                    <select value={t.priority} onClick={e => e.stopPropagation()}
                      onChange={e => changePriority(t.id, e.target.value)}
                      style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', padding: '2px 6px', fontSize: 11 }}>
                      {['low', 'normal', 'high', 'urgent'].map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[t.status]}`}>{STATUS_EMOJI[t.status]} {t.status.replace('_', ' ')}</span>
                  </td>
                  <td style={{ textAlign: 'center' }}>{(t.replies || []).length}</td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(t.created_at).toLocaleString()}</td>
                  <td>
                    <div className="flex gap-2" onClick={e => e.stopPropagation()}>
                      <button className="btn btn-primary btn-sm" onClick={() => setDetail(t)}><MessageSquare size={13} /></button>
                      {t.status !== 'resolved' && <button className="btn btn-success btn-sm" onClick={() => changeStatus(t.id, 'resolved')}><CheckCircle size={13} /></button>}
                      <button className="btn btn-danger btn-sm" onClick={() => deleteTicket(t.id)}><Trash2 size={13} /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {tickets.length === 0 && <tr><td colSpan={7} className="empty-state">No tickets {status ? `with status "${status}"` : ''}</td></tr>}
          </tbody>
        </table>
      </div>

      {/* Chat Modal */}
      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}
            style={{ maxWidth: 650, maxHeight: '90vh', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>

            {/* Header */}
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16 }}>{detail.subject}</h3>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {detail.display_name || detail.user} &nbsp;
                  <span className={`badge ${STATUS_BADGE[detail.status]}`} style={{ fontSize: 10 }}>{detail.status.replace('_', ' ')}</span>
                  <span className={`badge ${PRIORITY_BADGE[detail.priority]}`} style={{ fontSize: 10, marginLeft: 4 }}>{detail.priority}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {detail.status !== 'resolved' && (
                  <button className="btn btn-success btn-sm" onClick={() => changeStatus(detail.id, 'resolved')} title="Resolve">
                    <CheckCircle size={14} />
                  </button>
                )}
                {detail.status !== 'closed' && (
                  <button className="btn btn-secondary btn-sm" onClick={() => changeStatus(detail.id, 'closed')} title="Close">
                    <XCircle size={14} />
                  </button>
                )}
                <button onClick={() => setDetail(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4 }}>
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Chat Messages */}
            <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px', minHeight: 300, maxHeight: '55vh' }}>
              {/* Initial message */}
              <div style={{
                padding: '10px 14px', marginBottom: 10, borderRadius: '4px 12px 12px 12px',
                background: 'var(--bg)', border: '1px solid var(--border)', maxWidth: '85%',
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                  👤 {detail.display_name || detail.user} · {new Date(detail.created_at).toLocaleString()}
                </div>
                <div style={{ fontSize: 13, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{detail.message}</div>
              </div>

              {/* Replies */}
              {(detail.replies || []).filter((r, i) => i > 0 || r.sender === 'admin').map((r, i) => {
                const isAdmin = r.sender === 'admin';
                return (
                  <div key={i} style={{
                    padding: '10px 14px', marginBottom: 10, maxWidth: '85%',
                    borderRadius: isAdmin ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
                    background: isAdmin ? 'var(--accent-bg)' : 'var(--bg)',
                    border: `1px solid ${isAdmin ? 'var(--accent)' : 'var(--border)'}`,
                    marginLeft: isAdmin ? 'auto' : 0,
                  }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                      {isAdmin ? '👨‍💼 Admin' : `👤 ${detail.display_name || detail.user}`} · {r.timestamp ? new Date(r.timestamp).toLocaleString() : ''}
                    </div>
                    <div style={{ fontSize: 13, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{r.message}</div>
                  </div>
                );
              })}
              <div ref={chatEndRef} />
            </div>

            {/* Reply Input */}
            {detail.status !== 'closed' && (
              <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8 }}>
                <textarea
                  className="input"
                  value={reply}
                  onChange={e => setReply(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your reply... (Enter to send)"
                  rows={2}
                  style={{ flex: 1, resize: 'none', fontSize: 13 }}
                />
                <button
                  className="btn btn-primary"
                  onClick={sendReply}
                  disabled={sending || !reply.trim()}
                  style={{ alignSelf: 'flex-end', padding: '8px 16px' }}
                >
                  <Send size={16} />
                </button>
              </div>
            )}

            {detail.status === 'closed' && (
              <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                🔒 This ticket is closed.
                <button className="btn btn-secondary btn-sm" style={{ marginLeft: 8 }}
                  onClick={() => changeStatus(detail.id, 'open')}>Reopen</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
