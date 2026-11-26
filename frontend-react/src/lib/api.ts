import { LOCAL_SCENARIOS } from '../data/scenarios';
import type { CreateSessionRequest, OutcomeReport, Scenario, Session, Turn } from '../types';

const API = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
    } catch { /* body was not JSON */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// Endpoints: align these paths with app/routers/negotiation.py
export const api = {
  listScenarios: () => request<Scenario[]>('/api/scenarios'),
  getScenario: (id: string) => request<Scenario>(`/api/scenarios/${id}`),
  createSession: (body: CreateSessionRequest) =>
    request<{ session_id: string }>('/api/negotiations', { method: 'POST', body: JSON.stringify(body) }),
  getSession: (id: string) => request<Session>(`/api/negotiations/${id}`),
  getTranscript: (id: string) => request<Turn[]>(`/api/negotiations/${id}/transcript`),
  getReport: (id: string) => request<OutcomeReport>(`/api/negotiations/${id}/report`),
};

export function wsUrl(sessionId: string): string {
  const custom = import.meta.env.VITE_WS_URL as string | undefined;
  if (custom) return `${custom}/ws/negotiations/${sessionId}`;
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/negotiations/${sessionId}`;
}

/** Scenarios from the backend; falls back to the built-in templates if the backend is unreachable. */
export async function loadScenarios(): Promise<{ data: Scenario[]; offline: boolean }> {
  try {
    const data = await api.listScenarios();
    if (data.length > 0) return { data, offline: false };
  } catch { /* fall through to local templates */ }
  return { data: LOCAL_SCENARIOS, offline: true };
}

export async function loadScenario(id: string): Promise<{ data: Scenario | null; offline: boolean }> {
  try {
    return { data: await api.getScenario(id), offline: false };
  } catch { /* fall through to local templates */ }
  return { data: LOCAL_SCENARIOS.find((s) => s.id === id) ?? null, offline: true };
}
