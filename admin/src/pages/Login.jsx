import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store';
import api from '../services/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setAdmin } = useStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.login(username, password);
      setAdmin(data.admin);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="logo">
          <div className="logo-icon-lg">S</div>
          <h1>Service Hub</h1>
          <p>Admin Dashboard</p>
        </div>
        {error && <div className="login-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">Username</label>
            <input className="input" type="text" value={username}
              onChange={(e) => setUsername(e.target.value)} placeholder="admin" required />
          </div>
          <div className="input-group">
            <label className="input-label">Password</label>
            <input className="input" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)} placeholder="Enter password" required />
          </div>
          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}
            disabled={loading}>
            {loading ? <div className="loading" /> : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
