import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useStore } from './store';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Categories from './pages/Categories';
import Products from './pages/Products';
import Stock from './pages/Stock';
import Orders from './pages/Orders';
import Users from './pages/Users';
import Payments from './pages/Payments';
import Commands from './pages/Commands';
import Messages from './pages/Messages';
import Buttons from './pages/Buttons';
import Coupons from './pages/Coupons';
import Support from './pages/Support';
import Settings from './pages/Settings';
import AuditLogs from './pages/AuditLogs';
import Providers from './pages/Providers';
import Notifications from './pages/Notifications';
import Delivery from './pages/Delivery';
import Referrals from './pages/Referrals';
import Backups from './pages/Backups';
import Deposits from './pages/Deposits';
import Resellers from './pages/Resellers';
import './index.css';

function ProtectedRoute({ children }) {
  const isAuthenticated = useStore((s) => s.isAuthenticated);
  return isAuthenticated ? children : <Navigate to="/login" />;
}

export default function App() {
  const theme = useStore((s) => s.theme);

  return (
    <div data-theme={theme}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="categories" element={<Categories />} />
            <Route path="products" element={<Products />} />
            <Route path="stock" element={<Stock />} />
            <Route path="orders" element={<Orders />} />
            <Route path="users" element={<Users />} />
            <Route path="payments" element={<Payments />} />
            <Route path="deposits" element={<Deposits />} />
            <Route path="commands" element={<Commands />} />
            <Route path="messages" element={<Messages />} />
            <Route path="buttons" element={<Buttons />} />
            <Route path="coupons" element={<Coupons />} />
            <Route path="support" element={<Support />} />
            <Route path="settings" element={<Settings />} />
            <Route path="audit" element={<AuditLogs />} />
            <Route path="providers" element={<Providers />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="delivery" element={<Delivery />} />
            <Route path="referrals" element={<Referrals />} />
            <Route path="backups" element={<Backups />} />
            <Route path="resellers" element={<Resellers />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}
