import { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, Save } from 'lucide-react';
import ReactFlow, { addEdge, Background, Controls, MiniMap, useNodesState, useEdgesState } from 'reactflow';
import 'reactflow/dist/style.css';
import api from '../services/api';

const NODE_TYPES_LIST = ['start', 'message', 'condition', 'action', 'input', 'delay', 'end'];
const NODE_COLORS = { start: '#10b981', message: '#6366f1', condition: '#f59e0b', action: '#3b82f6', input: '#8b5cf6', delay: '#64748b', end: '#ef4444' };

export default function Flows() {
  const [flows, setFlows] = useState([]);
  const [selectedFlow, setSelectedFlow] = useState('');
  const [loading, setLoading] = useState(true);
  const [newFlowName, setNewFlowName] = useState('');

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => { api.getFlows().then(d => { setFlows(d.flows); setLoading(false); }); }, []);

  const loadFlow = async (flowId) => {
    setSelectedFlow(flowId);
    const d = await api.getFlow(flowId);
    setNodes(d.nodes.map(n => ({
      id: n.id, type: 'default', position: n.position,
      data: { label: `${n.type.toUpperCase()}: ${n.label}` },
      style: { background: NODE_COLORS[n.type] || '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 600 },
    })));
    setEdges(d.edges.map(e => ({ id: e.id, source: e.source, target: e.target, label: e.label || '', animated: true,
      style: { stroke: 'var(--accent)' }, labelStyle: { fontSize: 10, fill: 'var(--text-muted)' } })));
  };

  const onConnect = useCallback((params) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: 'var(--accent)' } }, eds)), []);

  const addNode = (type) => {
    const id = `node_${Date.now()}`;
    setNodes(nds => [...nds, {
      id, type: 'default',
      position: { x: 250 + Math.random() * 200, y: 100 + Math.random() * 200 },
      data: { label: `${type.toUpperCase()}: New` },
      style: { background: NODE_COLORS[type], color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontWeight: 600 },
    }]);
  };

  const saveFlow = async () => {
    const flowNodes = nodes.map(n => ({
      id: n.id, type: n.data.label.split(':')[0].toLowerCase().trim(),
      label: n.data.label.split(':').slice(1).join(':').trim() || 'node',
      position: n.position, config: {},
    }));
    const flowEdges = edges.map(e => ({ source: e.source, target: e.target, label: e.label, condition: '' }));
    await api.saveFlow(selectedFlow, { nodes: flowNodes, edges: flowEdges });
    alert('Flow saved!');
  };

  const createFlow = async () => {
    if (!newFlowName) return;
    await api.saveFlow(newFlowName, { nodes: [], edges: [] });
    setNewFlowName('');
    const d = await api.getFlows();
    setFlows(d.flows);
    setSelectedFlow(newFlowName);
  };

  const deleteFlow = async (id) => {
    if (!confirm('Delete this flow?')) return;
    await api.deleteFlow(id);
    const d = await api.getFlows();
    setFlows(d.flows);
    if (selectedFlow === id) { setSelectedFlow(''); setNodes([]); setEdges([]); }
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="loading" /></div>;

  return (
    <div>
      <h1 className="page-title">Flow Builder</h1>
      <p className="page-subtitle">Visual automation builder — create purchase, payment, and onboarding flows</p>

      <div className="toolbar">
        <div className="toolbar-left">
          <select className="select" style={{ width: 250 }} value={selectedFlow} onChange={e => loadFlow(e.target.value)}>
            <option value="">Select a flow...</option>
            {flows.map(f => <option key={f.flow_id} value={f.flow_id}>{f.flow_id} ({f.node_count} nodes)</option>)}
          </select>
          {selectedFlow && <>
            <button className="btn btn-primary btn-sm" onClick={saveFlow}><Save size={14} /> Save</button>
            <button className="btn btn-danger btn-sm" onClick={() => deleteFlow(selectedFlow)}><Trash2 size={14} /></button>
          </>}
        </div>
        <div className="toolbar-right">
          <input className="input" style={{ width: 160 }} value={newFlowName} onChange={e => setNewFlowName(e.target.value)} placeholder="new_flow_name" />
          <button className="btn btn-primary btn-sm" onClick={createFlow}><Plus size={14} /> Create</button>
        </div>
      </div>

      {selectedFlow && (
        <div className="flex gap-2 mb-4" style={{ flexWrap: 'wrap' }}>
          {NODE_TYPES_LIST.map(t => (
            <button key={t} className="btn btn-sm" onClick={() => addNode(t)}
              style={{ background: NODE_COLORS[t], color: '#fff', border: 'none' }}>
              + {t}
            </button>
          ))}
        </div>
      )}

      <div style={{ height: 500, border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', background: 'var(--bg-secondary)' }}>
        {selectedFlow ? (
          <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
            onConnect={onConnect} fitView>
            <Background color="var(--border)" gap={20} />
            <Controls style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }} />
            <MiniMap style={{ background: 'var(--bg-card)' }} nodeColor="#6366f1" />
          </ReactFlow>
        ) : (
          <div className="empty-state" style={{ paddingTop: 160 }}>
            <h3>Select or create a flow to start building</h3>
          </div>
        )}
      </div>
    </div>
  );
}
