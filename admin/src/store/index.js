import { create } from 'zustand';

export const useStore = create((set) => ({
  // Auth
  admin: JSON.parse(localStorage.getItem('admin') || 'null'),
  isAuthenticated: !!localStorage.getItem('token'),
  setAdmin: (admin) => {
    localStorage.setItem('admin', JSON.stringify(admin));
    set({ admin, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('admin');
    set({ admin: null, isAuthenticated: false });
  },

  // Theme
  theme: localStorage.getItem('theme') || 'dark',
  toggleTheme: () => set((s) => {
    const next = s.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    return { theme: next };
  }),

  // Sidebar
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  // Notifications
  toasts: [],
  addToast: (msg, type = 'info') => set((s) => ({
    toasts: [...s.toasts, { id: Date.now(), msg, type }],
  })),
  removeToast: (id) => set((s) => ({
    toasts: s.toasts.filter((t) => t.id !== id),
  })),
}));
