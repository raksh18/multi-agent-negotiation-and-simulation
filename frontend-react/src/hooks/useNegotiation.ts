import { useCallback, useEffect, useRef, useState } from 'react';
import { wsUrl } from '../lib/api';
import type { Action, ClientEvent, Metrics, Offer, ServerEvent, SessionStatus, Turn } from '../types';

export type RunState = 'connecting' | 'running' | 'awaiting_human' | 'finished' | 'error';

export interface NegotiationState {
  runState: RunState;
  turns: Turn[];
  metrics: Metrics | null;
  thinkingAgentId: string | null;
  awaitingAgentId: string | null;
  deadlockMessage: string | null;
  finalStatus: SessionStatus | null;
  error: string | null;
}

const initial: NegotiationState = {
  runState: 'connecting', turns: [], metrics: null, thinkingAgentId: null,
  awaitingAgentId: null, deadlockMessage: null, finalStatus: null, error: null,
};

/** Owns the WebSocket for one negotiation session and folds server events into UI state. */
export function useNegotiation(sessionId: string) {
  const [state, setState] = useState<NegotiationState>(initial);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setState(initial);
    const ws = new WebSocket(wsUrl(sessionId));
    socketRef.current = ws;
    let finished = false;

    ws.onopen = () => {
      const msg: ClientEvent = { type: 'start' };
      ws.send(JSON.stringify(msg));
      setState((s) => ({ ...s, runState: 'running' }));
    };

    ws.onmessage = (e) => {
      let ev: ServerEvent;
      try { ev = JSON.parse(e.data); } catch { return; }
      if (ev.type === 'finished') finished = true;
      setState((s) => {
        switch (ev.type) {
          case 'thinking':
            return { ...s, runState: 'running', thinkingAgentId: ev.agent_id, awaitingAgentId: null };
          case 'turn':
            return { ...s, turns: [...s.turns, ev.turn], thinkingAgentId: null };
          case 'metrics':
            return { ...s, metrics: ev.metrics };
          case 'awaiting_human':
            return { ...s, runState: 'awaiting_human', awaitingAgentId: ev.agent_id, thinkingAgentId: null };
          case 'deadlock':
            return { ...s, deadlockMessage: ev.message };
          case 'finished':
            return { ...s, runState: 'finished', finalStatus: ev.status, thinkingAgentId: null, awaitingAgentId: null };
          case 'error':
            return { ...s, runState: 'error', error: ev.message, thinkingAgentId: null };
          default:
            return s;
        }
      });
    };

    ws.onerror = () =>
      setState((s) => (s.runState === 'finished' ? s : { ...s, runState: 'error', error: 'Could not connect to the negotiation server.' }));
    ws.onclose = () => {
      if (!finished) setState((s) => (s.runState === 'finished' || s.runState === 'error' ? s : { ...s, runState: 'error', error: 'Connection to the server was lost.' }));
    };

    return () => { ws.onclose = null; ws.onerror = null; ws.close(); };
  }, [sessionId]);

  const sendHumanTurn = useCallback((action: Action, message: string, offer: Offer | null) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    const msg: ClientEvent = { type: 'human_turn', action, message, offer };
    ws.send(JSON.stringify(msg));
    setState((s) => ({ ...s, runState: 'running', awaitingAgentId: null }));
    return true;
  }, []);

  return { ...state, sendHumanTurn };
}
