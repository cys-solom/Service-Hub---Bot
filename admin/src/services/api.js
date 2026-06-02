const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('token') || '';
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  clearToken() {
    this.token = '';
    localStorage.removeItem('token');
  }

  async request(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `API Error ${res.status}`);
    }
    return res.json();
  }

  get(path) { return this.request(path); }
  post(path, data) { return this.request(path, { method: 'POST', body: JSON.stringify(data) }); }
  put(path, data) { return this.request(path, { method: 'PUT', body: JSON.stringify(data) }); }
  del(path, data) {
    const opts = { method: 'DELETE' };
    if (data) opts.body = JSON.stringify(data);
    return this.request(path, opts);
  }

  // Auth
  async login(username, password) {
    const data = await this.post('/auth/login', { username, password });
    this.setToken(data.access_token);
    return data;
  }

  // Dashboard
  getStats() { return this.get('/dashboard/stats'); }
  getChart(days = 14) { return this.get(`/dashboard/chart?days=${days}`); }

  // Categories
  getCategories() { return this.get('/categories'); }
  createCategory(data) { return this.post('/categories', data); }
  updateCategory(id, data) { return this.put(`/categories/${id}`, data); }
  deleteCategory(id) { return this.del(`/categories/${id}`); }

  // Products
  getProducts(categoryId) { return this.get(`/products${categoryId ? `?category_id=${categoryId}` : ''}`); }
  createProduct(data) { return this.post('/products', data); }
  updateProduct(id, data) { return this.put(`/products/${id}`, data); }
  deleteProduct(id) { return this.del(`/products/${id}`); }
  reorderProducts(items) { return this.put('/products/reorder', { items }); }

  // Stock
  getStock(productId, page = 1) { return this.get(`/stock?product_id=${productId}&page=${page}`); }
  getStockSummary() { return this.get('/stock/summary'); }
  addStockBulk(data) { return this.post('/stock/bulk', data); }
  addStockSingle(data) { return this.post('/stock/single', data); }
  updateStockItem(id, data) { return this.put(`/stock/${id}`, data); }
  deleteStockItem(id) { return this.del(`/stock/${id}`); }
  exportStock(productId) { return this.get(`/stock/export?product_id=${productId}`); }
  restoreStock(id) { return this.post(`/stock/${id}/restore`); }
  deleteSoldStock(productId) { return this.del(`/stock/sold?product_id=${productId}`); }
  bulkDeleteStock(ids) { return this.del('/stock/bulk', { ids }); }

  // Orders
  getOrders(page = 1, status = '') { return this.get(`/orders?page=${page}${status ? `&status=${status}` : ''}`); }
  getOrder(id) { return this.get(`/orders/${id}`); }
  updateOrderStatus(id, status) { return this.put(`/orders/${id}/status`, { status }); }
  approveOrder(id) { return this.post(`/orders/${id}/approve`); }
  rejectOrder(id, reason = 'Rejected by admin') { return this.post(`/orders/${id}/reject`, { reason }); }
  deleteOrder(id) { return this.del(`/orders/${id}`); }
  bulkDeleteOrders(ids) { return this.del('/orders/bulk', { ids }); }

  // Payments
  getPaymentMethods() { return this.get('/payments/methods'); }
  createPaymentMethod(data) { return this.post('/payments/methods', data); }
  updatePaymentMethod(id, data) { return this.put(`/payments/methods/${id}`, data); }
  getPayments(page = 1, type = '', status = '') { return this.get(`/payments?page=${page}${type ? `&type=${type}` : ''}${status ? `&status=${status}` : ''}`); }
  verifyPayment(id) { return this.put(`/payments/${id}/verify`); }
  approveDeposit(id) { return this.post(`/payments/${id}/approve`); }
  rejectDeposit(id) { return this.post(`/payments/${id}/reject`); }
  bulkDeletePayments(ids) { return this.del('/payments/bulk', { ids }); }

  // Users
  getUsers(page = 1, search = '') { return this.get(`/users?page=${page}${search ? `&search=${search}` : ''}`); }
  toggleBan(id, banned) { return this.put(`/users/${id}/ban`, { is_banned: banned }); }
  updateBalance(id, amount, op, note = '') { return this.put(`/users/${id}/balance`, { amount, operation: op, note }); }
  getUserDetails(id) { return this.get(`/users/${id}/details`); }

  // Commands
  getCommands() { return this.get('/commands'); }
  createCommand(data) { return this.post('/commands', data); }
  updateCommand(id, data) { return this.put(`/commands/${id}`, data); }
  deleteCommand(id) { return this.del(`/commands/${id}`); }

  // Messages
  getMessages() { return this.get('/messages'); }
  createMessage(data) { return this.post('/messages', data); }
  updateMessage(id, data) { return this.put(`/messages/${id}`, data); }
  deleteMessage(id) { return this.del(`/messages/${id}`); }

  // Buttons
  getButtons() { return this.get('/buttons'); }
  createButton(data) { return this.post('/buttons', data); }
  updateButton(id, data) { return this.put(`/buttons/${id}`, data); }

  // Reply Keyboard Buttons
  getReplyButtons() { return this.get('/reply-buttons'); }
  createReplyButton(data) { return this.post('/reply-buttons', data); }
  updateReplyButton(id, data) { return this.put(`/reply-buttons/${id}`, data); }
  deleteReplyButton(id) { return this.del(`/reply-buttons/${id}`); }

  // Coupons
  getCoupons() { return this.get('/coupons'); }
  createCoupon(data) { return this.post('/coupons', data); }
  updateCoupon(id, data) { return this.put(`/coupons/${id}`, data); }
  deleteCoupon(id) { return this.del(`/coupons/${id}`); }


  // Settings
  getSettings(group = '') { return this.get(`/settings${group ? `?group=${group}` : ''}`); }
  updateSetting(key, value) { return this.put(`/settings/${key}`, { value }); }
  resetDashboard() { return this.post('/settings/reset-dashboard'); }
  getResetStatus() { return this.get('/settings/reset-status'); }

  // Audit
  getAuditLogs(page = 1) { return this.get(`/audit?page=${page}`); }

  // Languages
  getLanguages() { return this.get('/languages'); }
  getTranslations(code) { return this.get(`/languages/translations/${code}`); }
  saveTranslations(code, data) { return this.put(`/languages/translations/${code}`, data); }

  // Providers
  getProviders() { return this.get('/providers'); }
  createProvider(data) { return this.post('/providers', data); }
  updateProvider(id, data) { return this.put(`/providers/${id}`, data); }

  // Notifications
  getNotifications() { return this.get('/notifications'); }
  createNotification(data) { return this.post('/notifications', data); }

  // Referrals
  getReferrals() { return this.get('/referrals'); }
  getReferralStats() { return this.get('/referrals/stats'); }
  getReferralSettings() { return this.get('/referrals/settings'); }
  updateReferralSettings(data) { return this.put('/referrals/settings', data); }
  updateReferralCommission(id, percent) { return this.put(`/referrals/${id}/commission`, { commission_percent: percent }); }
  updateReferralStatus(id, status) { return this.put(`/referrals/${id}/status`, { status }); }
  bulkDeleteReferrals(ids) { return this.del('/referrals/bulk', { ids }); }

  // Resellers
  getResellers() { return this.get('/resellers'); }
  getResellerStats() { return this.get('/resellers/stats'); }
  createReseller(data) { return this.post('/resellers', data); }
  updateReseller(id, data) { return this.put(`/resellers/${id}`, data); }
  deleteReseller(id) { return this.del(`/resellers/${id}`); }
  regenerateKey(id) { return this.post(`/resellers/${id}/regenerate`); }
  resellerDeposit(id, amount, note = '') { return this.post(`/resellers/${id}/deposit`, { amount, note }); }
  resellerDeduct(id, amount, note = '') { return this.post(`/resellers/${id}/deduct`, { amount, note }); }
  getResellerTransactions(id, page = 1) { return this.get(`/resellers/${id}/transactions?page=${page}`); }
  getWholesalePrices() { return this.get('/resellers/wholesale-prices'); }
  setWholesalePrice(productId, price) { return this.put(`/resellers/wholesale-prices/${productId}`, { wholesale_price: price }); }

  // Delivery
  getDeliveryRules() { return this.get('/delivery'); }
  createDeliveryRule(data) { return this.post('/delivery', data); }

  // Backups
  getBackups() { return this.get('/backups'); }
  createBackup() { return this.post('/backups/create'); }
  deleteBackup(id) { return this.del(`/backups/${id}`); }

  // Support Tickets
  getTickets(status = '', page = 1) { return this.get(`/support?status=${status}&page=${page}`); }
  getTicketStats() { return this.get('/support/stats'); }
  replyTicket(id, message) { return this.post(`/support/${id}/reply`, { message }); }
  updateTicketStatus(id, status) { return this.put(`/support/${id}/status`, { status }); }
  updateTicketPriority(id, priority) { return this.put(`/support/${id}/priority`, { priority }); }
  deleteTicket(id) { return this.del(`/support/${id}`); }

  // Profile / Account
  getMe() { return this.get('/auth/me'); }
  changePassword(currentPassword, newPassword) {
    return this.put('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }
  async updateProfile(data) {
    const result = await this.put('/auth/update-profile', data);
    if (result.access_token) {
      this.setToken(result.access_token);
    }
    return result;
  }
}

export const api = new ApiService();
export default api;

