import { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, ShoppingCart, DollarSign, Package, AlertTriangle, Clock } from 'lucide-react';
import api from '../services/api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [chart, setChart] = useState(null);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {});
    api.getChart().then(setChart).catch(() => {});
  }, []);

  if (!stats) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  const statCards = [
    { label: 'Total Revenue', value: `$${stats.total_revenue}`, icon: DollarSign, color: '#10b981', bg: 'var(--success-bg)' },
    { label: 'Today Revenue', value: `$${stats.today_revenue}`, icon: DollarSign, color: '#3b82f6', bg: 'var(--info-bg)' },
    { label: 'Total Orders', value: stats.total_orders, icon: ShoppingCart, color: '#8b5cf6', bg: 'var(--accent-bg)' },
    { label: 'Today Orders', value: stats.today_orders, icon: Clock, color: '#f59e0b', bg: 'var(--warning-bg)' },
    { label: 'Total Users', value: stats.total_users, icon: Users, color: '#6366f1', bg: 'var(--accent-bg)' },
    { label: 'Stock Available', value: stats.stock_available, icon: Package, color: '#10b981', bg: 'var(--success-bg)' },
    { label: 'Pending Orders', value: stats.pending_orders, icon: AlertTriangle, color: '#f59e0b', bg: 'var(--warning-bg)' },
    { label: 'Open Tickets', value: stats.open_tickets, icon: AlertTriangle, color: '#ef4444', bg: 'var(--danger-bg)' },
  ];

  const chartData = chart ? chart.labels.map((l, i) => ({
    name: l, orders: chart.orders[i], revenue: chart.revenue[i],
  })) : [];

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">Welcome back! Here's your store overview.</p>

      <div className="stats-grid">
        {statCards.map((s) => (
          <div key={s.label} className="stat-card">
            <div>
              <div className="stat-label">{s.label}</div>
              <div className="stat-value">{s.value}</div>
            </div>
            <div className="stat-icon" style={{ background: s.bg, color: s.color }}>
              <s.icon size={22} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="chart-card">
          <div className="chart-title">Revenue (14 days)</div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
              <YAxis stroke="var(--text-muted)" fontSize={12} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }} />
              <Line type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="chart-card">
          <div className="chart-title">Orders (14 days)</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
              <YAxis stroke="var(--text-muted)" fontSize={12} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }} />
              <Bar dataKey="orders" fill="#8b5cf6" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Recent Orders</h3>
          {stats.recent_orders?.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead><tr><th>Order</th><th>User</th><th>Amount</th><th>Status</th></tr></thead>
                <tbody>
                  {stats.recent_orders.map((o) => (
                    <tr key={o.id}>
                      <td style={{ fontWeight: 500 }}>{o.order_number}</td>
                      <td>{o.username}</td>
                      <td>${o.total}</td>
                      <td><span className={`badge badge-${o.status === 'delivered' ? 'success' : o.status === 'pending' ? 'warning' : 'info'}`}>{o.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p style={{ color: 'var(--text-muted)' }}>No orders yet</p>}
        </div>

        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Low Stock Alerts</h3>
          {stats.low_stock?.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead><tr><th>Product</th><th>Available</th></tr></thead>
                <tbody>
                  {stats.low_stock.map((s, i) => (
                    <tr key={i}>
                      <td>{s.name}</td>
                      <td><span className="badge badge-danger">{s.available} left</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p style={{ color: 'var(--text-muted)' }}>All products well stocked</p>}
        </div>
      </div>
    </div>
  );
}
