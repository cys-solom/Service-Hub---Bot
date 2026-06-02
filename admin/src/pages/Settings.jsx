import { useState, useEffect } from 'react';
import { Save, User, Key, Shield, Settings as SettingsIcon, AlertTriangle, RotateCcw } from 'lucide-react';
import api from '../services/api';
import { useStore } from '../store';


function DangerZone({ msg, setMsg }) {
  const [step, setStep] = useState(0); // 0=idle, 1=first click, 2=confirm
  const [busy, setBusy] = useState(false);
  const [lastReset, setLastReset] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.getResetStatus().then(d => { if (d.has_reset) setLastReset(d.data); }).catch(() => {});
  }, []);

  const handleReset = async () => {
    if (step === 0) { setStep(1); return; }
    if (step === 1) { setStep(2); return; }
    // step 2 — execute
    setBusy(true);
    try {
      const res = await api.resetDashboard();
      setResult(res.counts);
      setMsg({ type: 'success', text: `✅ ${res.message}` });
      setStep(0);
      api.getResetStatus().then(d => { if (d.has_reset) setLastReset(d.data); });
    } catch (e) {
      setMsg({ type: 'error', text: `❌ ${e.message}` });
    }
    setBusy(false);
  };

  const labels = ['🔴 Reset Dashboard', '⚠️ Are you sure?', '💀 CONFIRM FULL RESET'];
  const colors = ['rgba(255,69,58,0.12)', 'rgba(255,159,10,0.15)', '#ff453a'];
  const textColors = ['#ff453a', '#ff9f0a', '#fff'];

  return (
    <div style={{
      marginTop: 32, padding: 24, borderRadius: 12,
      border: '2px solid rgba(255,69,58,0.3)', background: 'rgba(255,69,58,0.05)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <AlertTriangle size={20} color="#ff453a" />
        <h3 style={{ margin: 0, color: '#ff453a', fontSize: 16 }}>Danger Zone</h3>
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
        Reset all transactional data: <b>Orders, Payments, Deposits, Wallet balances, Support tickets, Stock sold items</b>.
        <br />Products, categories, settings, and admin accounts are <b>preserved</b>.
      </p>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button onClick={handleReset} disabled={busy}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer',
            fontWeight: 700, fontSize: 13, transition: 'all 0.2s',
            background: colors[step], color: textColors[step],
          }}>
          {busy ? '⏳ Resetting...' : labels[step]}
        </button>
        {step > 0 && (
          <button onClick={() => setStep(0)}
            style={{ padding: '10px 16px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--bg-card-hover)', color: 'var(--text-muted)', fontSize: 13 }}>
            ✕ Cancel
          </button>
        )}
      </div>

      {result && (
        <div style={{ marginTop: 16, padding: 14, background: 'rgba(48,209,88,0.08)', borderRadius: 8, border: '1px solid rgba(48,209,88,0.2)' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#30d158', marginBottom: 8 }}>✅ Reset Complete</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 6 }}>
            {Object.entries(result).map(([k, v]) => (
              <div key={k} style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {k.replace(/_/g, ' ')}: <b style={{ color: 'var(--text-primary)' }}>{v}</b>
              </div>
            ))}
          </div>
        </div>
      )}

      {lastReset && !result && (
        <div style={{ marginTop: 16, padding: 12, background: 'var(--bg-card)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            <RotateCcw size={12} style={{ marginRight: 4 }} />
            Last reset: <b>{new Date(lastReset.timestamp).toLocaleString()}</b>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
            {Object.entries(lastReset.counts || {}).map(([k, v]) => (
              <span key={k} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'var(--bg-card-hover)', color: 'var(--text-muted)' }}>
                {k.replace(/_/g, ' ')}: {v}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


export default function Settings() {
  const [tab, setTab] = useState('store');
  const [settings, setSettings] = useState([]);
  const [storeVars, setStoreVars] = useState({ support_user: '', store_name: '', channel_url: '', payment_timeout: '', force_channel_enabled: 'false', force_channel_url: '', force_channel_chat_id: '', force_group_enabled: 'false', force_group_url: '', force_group_chat_id: '' });
  const [storeSaving, setStoreSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [edits, setEdits] = useState({});

  // Account state
  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState({ display_name: '', username: '', telegram_id: '' });
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [msg, setMsg] = useState({ type: '', text: '' });
  const { setAdmin } = useStore();

  // Load profile
  useEffect(() => {
    api.getMe().then(data => {
      setProfile(data);
      setProfileForm({
        display_name: data.display_name || '',
        username: data.username || '',
        telegram_id: data.telegram_id || '',
      });
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // Load store settings
  useEffect(() => {
    api.getSettings('store').then(d => {
      const map = {};
      d.settings.forEach(s => { map[s.key] = s.value || ''; });
      setStoreVars(prev => ({ ...prev, ...map }));
    }).catch(() => {});
  }, []);

  // Load system settings
  useEffect(() => {
    if (tab === 'system') {
      setLoading(true);
      api.getSettings().then(d => { setSettings(d.settings); setLoading(false); }).catch(() => setLoading(false));
    }
  }, [tab]);

  const handleProfileSave = async () => {
    setMsg({ type: '', text: '' });
    try {
      const data = { ...profileForm };
      if (data.telegram_id === '') data.telegram_id = null;
      else data.telegram_id = parseInt(data.telegram_id) || null;

      const result = await api.updateProfile(data);
      setMsg({ type: 'success', text: '✅ Profile updated successfully!' });
      
      // Update store with new admin info
      if (result.admin) {
        setAdmin(result.admin);
      }
    } catch (e) {
      setMsg({ type: 'error', text: `❌ ${e.message}` });
    }
  };

  const handlePasswordChange = async () => {
    setMsg({ type: '', text: '' });

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMsg({ type: 'error', text: '❌ Passwords do not match' });
      return;
    }
    if (passwordForm.new_password.length < 6) {
      setMsg({ type: 'error', text: '❌ Password must be at least 6 characters' });
      return;
    }

    try {
      await api.changePassword(passwordForm.current_password, passwordForm.new_password);
      setMsg({ type: 'success', text: '✅ Password changed successfully!' });
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (e) {
      setMsg({ type: 'error', text: `❌ ${e.message}` });
    }
  };

  const handleStoreSave = async () => {
    setStoreSaving(true);
    setMsg({ type: '', text: '' });
    try {
      await Promise.all(
        Object.entries(storeVars).map(([key, val]) => api.updateSetting(key, val))
      );
      setMsg({ type: 'success', text: '✅ Store settings saved! Changes apply immediately to the bot.' });
    } catch (e) {
      setMsg({ type: 'error', text: `❌ ${e.message}` });
    }
    setStoreSaving(false);
  };

  const handleSettingSave = async (key) => {
    try {
      await api.updateSetting(key, edits[key]);
      setMsg({ type: 'success', text: `✅ Setting "${key}" saved` });
    } catch (e) {
      setMsg({ type: 'error', text: `❌ ${e.message}` });
    }
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  const groups = [...new Set(settings.map(s => s.group))];

  return (
    <div>
      <h1 className="page-title">Settings</h1>
      <p className="page-subtitle">Manage your account and application settings</p>

      <div className="tabs">
        <div className={`tab ${tab === 'store' ? 'active' : ''}`} onClick={() => setTab('store')}>
          🏪 Store
        </div>
        <div className={`tab ${tab === 'account' ? 'active' : ''}`} onClick={() => setTab('account')}>
          <User size={14} style={{ marginRight: 6 }} /> Account
        </div>
        <div className={`tab ${tab === 'password' ? 'active' : ''}`} onClick={() => setTab('password')}>
          <Key size={14} style={{ marginRight: 6 }} /> Password
        </div>
        <div className={`tab ${tab === 'system' ? 'active' : ''}`} onClick={() => setTab('system')}>
          <SettingsIcon size={14} style={{ marginRight: 6 }} /> System
        </div>
      </div>

      {msg.text && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 16, fontSize: 14,
          background: msg.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
          color: msg.type === 'success' ? 'var(--success)' : 'var(--danger)',
          border: `1px solid ${msg.type === 'success' ? 'var(--success)' : 'var(--danger)'}20`,
        }}>
          {msg.text}
        </div>
      )}

      {/* ===== STORE TAB ===== */}
      {tab === 'store' && (
        <div className="card" style={{ maxWidth: 640 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
            <div style={{ fontSize: 36 }}>🏪</div>
            <div>
              <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 2 }}>Store Settings</h3>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
                These values appear automatically in all bot messages. No restart needed.
              </p>
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">💬 Support Username</label>
            <input className="input"
              value={storeVars.support_user}
              onChange={e => setStoreVars({ ...storeVars, support_user: e.target.value })}
              placeholder="@YourTelegramUsername" />
            <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              Shown wherever <code>{'{support_user}'}</code> appears in messages
            </small>
          </div>

          <div className="input-group">
            <label className="input-label">🏪 Store Name</label>
            <input className="input"
              value={storeVars.store_name}
              onChange={e => setStoreVars({ ...storeVars, store_name: e.target.value })}
              placeholder="My Store" />
            <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              Shown wherever <code>{'{store_name}'}</code> appears in messages
            </small>
          </div>

          <div className="input-group">
            <label className="input-label">🔗 Channel / Group URL</label>
            <input className="input"
              value={storeVars.channel_url}
              onChange={e => setStoreVars({ ...storeVars, channel_url: e.target.value })}
              placeholder="https://t.me/yourchannel" />
            <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              Shown wherever <code>{'{channel_url}'}</code> appears in messages
            </small>
          </div>

          <div className="input-group">
            <label className="input-label">⏱ Payment Timeout (minutes)</label>
            <input className="input" type="number" min="5" max="120"
              value={storeVars.payment_timeout}
              onChange={e => setStoreVars({ ...storeVars, payment_timeout: e.target.value })}
              placeholder="30" style={{ maxWidth: 140 }} />
            <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              How long before an unpaid order expires
            </small>
          </div>

          {/* ── Forced Join Section ── */}
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 20, marginTop: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <span style={{ fontSize: 20 }}>📢</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>Forced Join</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Require users to join channel/group before using the bot</div>
              </div>
            </div>

            {/* Channel */}
            <div style={{ background: 'var(--bg-card-hover)', borderRadius: 12, padding: 16, marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 18 }}>📣</span>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>Channel</span>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <span style={{ fontSize: 12, color: storeVars.force_channel_enabled === 'true' ? 'var(--success)' : 'var(--text-muted)' }}>
                    {storeVars.force_channel_enabled === 'true' ? '✅ Enabled' : '⏸ Disabled'}
                  </span>
                  <div onClick={() => setStoreVars({ ...storeVars, force_channel_enabled: storeVars.force_channel_enabled === 'true' ? 'false' : 'true' })}
                    style={{
                      width: 44, height: 24, borderRadius: 12, cursor: 'pointer', transition: 'all .2s',
                      background: storeVars.force_channel_enabled === 'true' ? 'var(--success)' : 'var(--border)',
                      position: 'relative',
                    }}>
                    <div style={{
                      width: 18, height: 18, borderRadius: '50%', background: '#fff',
                      position: 'absolute', top: 3,
                      left: storeVars.force_channel_enabled === 'true' ? 23 : 3,
                      transition: 'left .2s',
                    }} />
                  </div>
                </label>
              </div>
              <div className="input-group" style={{ marginBottom: 8 }}>
                <label className="input-label" style={{ fontSize: 12 }}>Invite URL</label>
                <input className="input" style={{ fontSize: 13 }}
                  value={storeVars.force_channel_url}
                  onChange={e => setStoreVars({ ...storeVars, force_channel_url: e.target.value })}
                  placeholder="https://t.me/yourchannel" />
              </div>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label className="input-label" style={{ fontSize: 12 }}>Chat ID</label>
                <input className="input" style={{ fontSize: 13 }}
                  value={storeVars.force_channel_chat_id}
                  onChange={e => setStoreVars({ ...storeVars, force_channel_chat_id: e.target.value })}
                  placeholder="-1001234567890" />
              </div>
            </div>

            {/* Group */}
            <div style={{ background: 'var(--bg-card-hover)', borderRadius: 12, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 18 }}>👥</span>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>Group</span>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <span style={{ fontSize: 12, color: storeVars.force_group_enabled === 'true' ? 'var(--success)' : 'var(--text-muted)' }}>
                    {storeVars.force_group_enabled === 'true' ? '✅ Enabled' : '⏸ Disabled'}
                  </span>
                  <div onClick={() => setStoreVars({ ...storeVars, force_group_enabled: storeVars.force_group_enabled === 'true' ? 'false' : 'true' })}
                    style={{
                      width: 44, height: 24, borderRadius: 12, cursor: 'pointer', transition: 'all .2s',
                      background: storeVars.force_group_enabled === 'true' ? 'var(--success)' : 'var(--border)',
                      position: 'relative',
                    }}>
                    <div style={{
                      width: 18, height: 18, borderRadius: '50%', background: '#fff',
                      position: 'absolute', top: 3,
                      left: storeVars.force_group_enabled === 'true' ? 23 : 3,
                      transition: 'left .2s',
                    }} />
                  </div>
                </label>
              </div>
              <div className="input-group" style={{ marginBottom: 8 }}>
                <label className="input-label" style={{ fontSize: 12 }}>Invite URL</label>
                <input className="input" style={{ fontSize: 13 }}
                  value={storeVars.force_group_url}
                  onChange={e => setStoreVars({ ...storeVars, force_group_url: e.target.value })}
                  placeholder="https://t.me/+ABC123" />
              </div>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label className="input-label" style={{ fontSize: 12 }}>Chat ID</label>
                <input className="input" style={{ fontSize: 13 }}
                  value={storeVars.force_group_chat_id}
                  onChange={e => setStoreVars({ ...storeVars, force_group_chat_id: e.target.value })}
                  placeholder="-1001234567890" />
              </div>
            </div>
          </div>

          <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={handleStoreSave} disabled={storeSaving}>
            <Save size={14} /> {storeSaving ? 'Saving...' : 'Save Store Settings'}
          </button>
        </div>
      )}

      {/* ===== ACCOUNT TAB ===== */}
      {tab === 'account' && profile && (
        <div className="card" style={{ maxWidth: 600 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
            <div style={{
              width: 64, height: 64, borderRadius: 16,
              background: 'linear-gradient(135deg, var(--accent), var(--accent-hover))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 24, fontWeight: 700, color: '#fff',
            }}>
              {(profileForm.display_name || profileForm.username || 'A')[0].toUpperCase()}
            </div>
            <div>
              <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 2 }}>{profileForm.display_name || profileForm.username}</h3>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="badge badge-info">{profile.role || 'Admin'}</span>
                {profile.is_super && <span className="badge badge-success">Super Admin</span>}
              </div>
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Display Name</label>
            <input className="input" value={profileForm.display_name}
              onChange={e => setProfileForm({ ...profileForm, display_name: e.target.value })}
              placeholder="Your display name" />
          </div>

          <div className="input-group">
            <label className="input-label">Username</label>
            <input className="input" value={profileForm.username}
              onChange={e => setProfileForm({ ...profileForm, username: e.target.value })}
              placeholder="admin" />
            <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>Used for login</small>
          </div>

          <div className="input-group">
            <label className="input-label">Telegram ID</label>
            <input className="input" value={profileForm.telegram_id}
              onChange={e => setProfileForm({ ...profileForm, telegram_id: e.target.value })}
              placeholder="Your Telegram user ID (for bot notifications)" />
            <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>
              Get your ID from @userinfobot on Telegram
            </small>
          </div>

          <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
            <button className="btn btn-primary" onClick={handleProfileSave}>
              <Save size={14} /> Save Changes
            </button>
          </div>

          {profile.created_at && (
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)', fontSize: 12, color: 'var(--text-muted)' }}>
              Account created: {new Date(profile.created_at).toLocaleDateString()}
            </div>
          )}
        </div>
      )}

      {/* ===== PASSWORD TAB ===== */}
      {tab === 'password' && (
        <div className="card" style={{ maxWidth: 500 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10,
              background: 'var(--warning-bg)', color: 'var(--warning)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Shield size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 600 }}>Change Password</h3>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Update your admin panel password</p>
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Current Password</label>
            <input className="input" type="password" value={passwordForm.current_password}
              onChange={e => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
              placeholder="Enter current password" />
          </div>

          <div className="input-group">
            <label className="input-label">New Password</label>
            <input className="input" type="password" value={passwordForm.new_password}
              onChange={e => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
              placeholder="Enter new password (min 6 chars)" />
          </div>

          <div className="input-group">
            <label className="input-label">Confirm New Password</label>
            <input className="input" type="password" value={passwordForm.confirm_password}
              onChange={e => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
              placeholder="Confirm new password" />
          </div>

          <button className="btn btn-primary" onClick={handlePasswordChange} style={{ marginTop: 8 }}>
            <Key size={14} /> Change Password
          </button>
        </div>
      )}

      {/* ===== SYSTEM TAB ===== */}
      {tab === 'system' && (
        <>
          {groups.map(g => (
            <div key={g} className="card" style={{ marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16 }}>{g}</h3>
              {settings.filter(s => s.group === g).map(s => (
                <div key={s.key} className="flex items-center gap-3" style={{ marginBottom: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{s.key}</div>
                    {s.description && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.description}</div>}
                  </div>
                  <input className="input" style={{ width: 300 }}
                    value={edits[s.key] !== undefined ? edits[s.key] : (s.value || '')}
                    onChange={e => setEdits({ ...edits, [s.key]: e.target.value })} />
                  <button className="btn btn-primary btn-sm" onClick={() => handleSettingSave(s.key)}><Save size={13} /></button>
                </div>
              ))}
            </div>
          ))}
          {settings.length === 0 && <div className="empty-state"><h3>No system settings configured yet</h3></div>}

          {/* ── Danger Zone ── */}
          <DangerZone msg={msg} setMsg={setMsg} />
        </>
      )}
    </div>
  );
}
