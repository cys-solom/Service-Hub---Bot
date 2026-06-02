import { useState, useEffect } from 'react';
import { Plus, Edit2, CreditCard, Check } from 'lucide-react';
import api from '../services/api';

export default function Payments() {
  const [tab, setTab] = useState('methods');
  const [methods, setMethods] = useState([]);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({
    name: '', code: '', type: 'crypto', is_enabled: true,
    wallet_address: '', fee_percent: 0, fee_fixed: 0,
    min_amount: 0, max_amount: 99999, instructions: '',
  });

  const loadMethods = () => api.getPaymentMethods().then(d => { setMethods(d.methods); setLoading(false); });
  const loadPayments = () => api.getPayments().then(d => { setPayments(d.payments); setLoading(false); });

  useEffect(() => { tab === 'methods' ? loadMethods() : loadPayments(); }, [tab]);

  const handleSave = async () => {
    if (modal === 'edit') await api.updatePaymentMethod(form.id, form);
    else await api.createPaymentMethod(form);
    setModal(null); loadMethods();
  };

  const verifyPayment = async (id) => {
    await api.verifyPayment(id); loadPayments();
  };

  return (
    <div>
      <h1 className="page-title">Payments</h1>
      <p className="page-subtitle">Configure payment methods and manage transactions</p>

      <div className="tabs">
        <div className={`tab ${tab === 'methods' ? 'active' : ''}`} onClick={() => setTab('methods')}>Payment Methods</div>
        <div className={`tab ${tab === 'history' ? 'active' : ''}`} onClick={() => setTab('history')}>Payment History</div>
      </div>

      {tab === 'methods' && (
        <>
          <div className="toolbar">
            <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{methods.length} methods</span>
            <button className="btn btn-primary" onClick={() => {
              setForm({ name: '', code: '', type: 'crypto', is_enabled: true, wallet_address: '', fee_percent: 0, fee_fixed: 0, min_amount: 0, max_amount: 99999, instructions: '' });
              setModal('create');
            }}><Plus size={16} /> Add Method</button>
          </div>
          <div className="table-wrapper">
            <table>
              <thead><tr><th>Name</th><th>Code</th><th>Type</th><th>Address</th><th>Fee</th><th>Enabled</th><th>Actions</th></tr></thead>
              <tbody>
                {methods.map(m => (
                  <tr key={m.id}>
                    <td style={{ fontWeight: 600 }}><CreditCard size={14} style={{ marginRight: 8, opacity: .5 }} />{m.name}</td>
                    <td><span className="badge badge-neutral">{m.code}</span></td>
                    <td>{m.type}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.wallet_address || '—'}</td>
                    <td>{m.fee_percent}% + ${m.fee_fixed}</td>
                    <td>
                      <div className={`toggle ${m.is_enabled ? 'active' : ''}`}
                        onClick={async () => { await api.updatePaymentMethod(m.id, { ...m, is_enabled: !m.is_enabled }); loadMethods(); }} />
                    </td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => { setForm({ ...m }); setModal('edit'); }}><Edit2 size={13} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === 'history' && (
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Method</th><th>Amount</th><th>Status</th><th>TX Hash</th><th>Date</th><th>Actions</th></tr></thead>
            <tbody>
              {payments.map(p => (
                <tr key={p.id}>
                  <td><span className="badge badge-neutral">{p.method_code}</span></td>
                  <td>${p.amount}</td>
                  <td><span className={`badge ${p.status === 'confirmed' ? 'badge-success' : p.status === 'pending' ? 'badge-warning' : 'badge-danger'}`}>{p.status}</span></td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.tx_hash || p.tx_note || '—'}</td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(p.created_at).toLocaleString()}</td>
                  <td>
                    {p.status === 'pending' && <button className="btn btn-success btn-sm" onClick={() => verifyPayment(p.id)}><Check size={13} /> Verify</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ minWidth: 500 }}>
            <h2 className="modal-title">{modal === 'edit' ? 'Edit' : 'New'} Payment Method</h2>
            <div className="grid-2">
              <div className="input-group"><label className="input-label">Name</label>
                <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
              <div className="input-group"><label className="input-label">Code</label>
                <input className="input" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} placeholder="usdt_trc20" /></div>
            </div>
            <div className="grid-2">
              <div className="input-group"><label className="input-label">Type</label>
                <select className="select" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
                  <option value="crypto">Crypto</option><option value="internal">Internal (Wallet)</option><option value="manual">Manual</option>
                </select></div>
              <div className="input-group"><label className="input-label">Wallet Address</label>
                <input className="input" value={form.wallet_address || ''} onChange={e => setForm({ ...form, wallet_address: e.target.value })} /></div>
            </div>
            <div className="grid-3">
              <div className="input-group"><label className="input-label">Fee %</label>
                <input className="input" type="number" step="0.1" value={form.fee_percent} onChange={e => setForm({ ...form, fee_percent: parseFloat(e.target.value) })} /></div>
              <div className="input-group"><label className="input-label">Fee Fixed</label>
                <input className="input" type="number" step="0.01" value={form.fee_fixed} onChange={e => setForm({ ...form, fee_fixed: parseFloat(e.target.value) })} /></div>
              <div className="input-group"><label className="input-label">Min Amount</label>
                <input className="input" type="number" value={form.min_amount} onChange={e => setForm({ ...form, min_amount: parseFloat(e.target.value) })} /></div>
            </div>
            <div className="input-group"><label className="input-label">Payment Instructions</label>
              <textarea className="textarea" value={form.instructions || ''} onChange={e => setForm({ ...form, instructions: e.target.value })}
                placeholder="Instructions shown to user during payment..." /></div>
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
