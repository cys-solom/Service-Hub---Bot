import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, FolderTree } from 'lucide-react';
import api from '../services/api';

export default function Categories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [form, setForm] = useState({ name: '', slug: '', description: '', is_visible: true });

  const load = () => api.getCategories().then(d => { setCategories(d.categories); setLoading(false); });
  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    try {
      if (modal === 'edit') await api.updateCategory(form.id, form);
      else await api.createCategory(form);
      setModal(null);
      load();
    } catch (e) { alert(e.message); }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this category and all its products?')) return;
    await api.deleteCategory(id);
    load();
  };

  const openEdit = (cat) => { setForm({ ...cat }); setModal('edit'); };
  const openCreate = () => { setForm({ name: '', slug: '', description: '', is_visible: true }); setModal('create'); };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Categories</h1>
      <p className="page-subtitle">Manage your product categories</p>

      <div className="toolbar">
        <div className="toolbar-left">
          <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{categories.length} categories</span>
        </div>
        <button className="btn btn-primary" onClick={openCreate}><Plus size={16} /> Add Category</button>
      </div>

      <div className="table-wrapper">
        <table>
          <thead><tr><th>Name</th><th>Slug</th><th>Products</th><th>Stock</th><th>Visible</th><th>Actions</th></tr></thead>
          <tbody>
            {categories.map(c => (
              <tr key={c.id}>
                <td style={{ fontWeight: 600 }}><FolderTree size={14} style={{ marginRight: 8, opacity: .5 }} />{c.name}</td>
                <td style={{ color: 'var(--text-muted)' }}>{c.slug}</td>
                <td>{c.products_count}</td>
                <td><span className={`badge ${c.stock_available > 0 ? 'badge-success' : 'badge-danger'}`}>{c.stock_available}</span></td>
                <td>{c.is_visible ? <span className="badge badge-success">Yes</span> : <span className="badge badge-danger">No</span>}</td>
                <td>
                  <div className="flex gap-2">
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(c)}><Edit2 size={13} /></button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(c.id)}><Trash2 size={13} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {categories.length === 0 && <tr><td colSpan={6} className="empty-state">No categories yet</td></tr>}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">{modal === 'edit' ? 'Edit Category' : 'New Category'}</h2>
            <div className="input-group">
              <label className="input-label">Name</label>
              <input className="input" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="input-group">
              <label className="input-label">Slug</label>
              <input className="input" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })} placeholder="auto-generated" />
            </div>
            <div className="input-group">
              <label className="input-label">Description</label>
              <textarea className="textarea" value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="input-group flex items-center gap-3">
              <label className="input-label" style={{ marginBottom: 0 }}>Visible</label>
              <div className={`toggle ${form.is_visible ? 'active' : ''}`} onClick={() => setForm({ ...form, is_visible: !form.is_visible })} />
            </div>
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
