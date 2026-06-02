import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useStore } from '../store';
import {
  LayoutDashboard, FolderTree, Package, Boxes, ShoppingCart,
  Users, CreditCard, Terminal, MessageSquare, Grid3X3,
  Ticket, LifeBuoy, Settings, FileText,
  Globe, Bell, Truck, Users2, Database, Sun, Moon,
  Menu, LogOut, ChevronLeft, DollarSign, Key
} from 'lucide-react';

const navSections = [
  { title: 'Overview', items: [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  ]},
  { title: 'Store', items: [
    { path: '/products', icon: Package, label: 'Products' },
    { path: '/stock', icon: Boxes, label: 'Stock' },
    { path: '/orders', icon: ShoppingCart, label: 'Orders' },
    { path: '/payments', icon: CreditCard, label: 'Payments' },
    { path: '/deposits', icon: DollarSign, label: 'Deposits' },
    { path: '/delivery', icon: Truck, label: 'Delivery' },
  ]},
  { title: 'Bot CMS', items: [
    { path: '/commands', icon: Terminal, label: 'Commands' },
    { path: '/messages', icon: MessageSquare, label: 'Messages' },
    { path: '/buttons', icon: Grid3X3, label: 'Buttons' },
  ]},
  { title: 'Marketing', items: [
    { path: '/coupons', icon: Ticket, label: 'Coupons' },
    { path: '/referrals', icon: Users2, label: 'Referrals' },
    { path: '/resellers', icon: Key, label: 'Reseller API' },
  ]},
  { title: 'System', items: [
    { path: '/users', icon: Users, label: 'Users' },
    { path: '/support', icon: LifeBuoy, label: 'Support' },
    { path: '/providers', icon: Globe, label: 'Providers' },
    { path: '/notifications', icon: Bell, label: 'Notifications' },
    { path: '/audit', icon: FileText, label: 'Audit Logs' },
    { path: '/settings', icon: Settings, label: 'Settings' },
    { path: '/backups', icon: Database, label: 'Backups' },
  ]},
];

export default function Layout() {
  const { theme, toggleTheme, sidebarOpen, toggleSidebar, admin, logout } = useStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
        <div className="sidebar-logo">
          <div className="logo-icon">S</div>
          <span className="logo-text">Service Hub</span>
        </div>
        <nav className="sidebar-nav">
          {navSections.map((section) => (
            <div key={section.title}>
              <div className="nav-section-title">{section.title}</div>
              {section.items.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/'}
                  className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                  <item.icon />
                  <span className="nav-label">{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <button className="btn btn-icon btn-secondary" onClick={toggleSidebar}>
              {sidebarOpen ? <ChevronLeft size={18} /> : <Menu size={18} />}
            </button>
          </div>
          <div className="topbar-right">
            <button className="btn btn-icon btn-secondary" onClick={toggleTheme}>
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              {admin?.display_name || 'Admin'}
            </span>
            <button className="btn btn-icon btn-secondary" onClick={handleLogout}>
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
