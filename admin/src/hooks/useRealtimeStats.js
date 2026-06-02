/**
 * Real-time WebSocket hook for dashboard live updates
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1')
  .replace('http://', 'ws://')
  .replace('https://', 'wss://') + '/ws';

export function useRealtimeStats() {
  const [stats, setStats] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setConnected(true);
      console.log('[WS] Connected');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'stats') {
          setStats(msg.data);
        } else if (msg.type === 'new_order') {
          // Could trigger a notification toast
          window.dispatchEvent(new CustomEvent('ws:new_order', { detail: msg.data }));
        } else if (msg.type === 'payment_confirmed') {
          window.dispatchEvent(new CustomEvent('ws:payment', { detail: msg.data }));
        }
      } catch (e) {
        console.error('[WS] Parse error', e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('[WS] Disconnected, reconnecting in 5s...');
      reconnectRef.current = setTimeout(connect, 5000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [connect]);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  return { stats, connected, sendPing };
}

export default useRealtimeStats;
