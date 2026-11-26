// ---- Shared types. These mirror the backend Pydantic schemas (app/schemas/negotiation.py).
// If a teammate renames a field, change it here and TypeScript will point to every place affected.

export type Mode = 'simulation' | 'practice';
export type Personality = 'aggressive' | 'collaborative' | 'risk-averse';
export type Action = 'offer' | 'counter' | 'accept' | 'reject';
/** Free-form string from the backend; StanceBadge handles known values and falls back gracefully. */
export type Stance = string;
export type OfferValue = string | number;
export type Offer = Record<string, OfferValue>;

export interface ScenarioParam {
  key: string;
  label: string;
  type: 'number' | 'text' | 'textarea';
  required: boolean;
  placeholder?: string;
  help?: string;
}

export interface OfferField {
  key: string;
  label: string;
  type: 'number' | 'text';
  unit?: string;
}

export interface AgentConfig {
  id: string;
  name: string;
  role: string;
  goals: string[];
  constraints: string[];
  personality: Personality;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  agents: AgentConfig[];
  parameters: ScenarioParam[];   // scenario-level inputs, e.g. total budget, project requirements
  offer_fields: OfferField[];    // structured terms a human can propose in Practice Mode
  default_max_rounds: number;
}

export interface AgentOverride {
  id: string;
  name: string;
  goals: string[];
  personality: Personality;
}

export interface CreateSessionRequest {
  scenario_id: string;
  mode: Mode;
  user_agent_id: string | null;
  max_rounds: number;
  parameters: Record<string, string | number>;
  agents: AgentOverride[];
}

export interface Session {
  session_id: string;
  scenario_id: string;
  scenario_name: string;
  mode: Mode;
  user_agent_id: string | null;
  max_rounds: number;
  agents: AgentConfig[];
  offer_fields: OfferField[];
}

export interface Turn {
  round: number;
  agent_id: string;
  agent_name: string;
  action: Action;
  message: string;
  reasoning: string | null;
  stance: Stance;
  offer: Offer | null;
  timestamp: string;
}

export interface Metrics {
  round: number;
  max_rounds: number;
  stances: Record<string, Stance>;
  satisfaction: Record<string, number>; // 0-100 per agent
}

export type SessionStatus = 'agreement' | 'breakdown' | 'deadlock';

export interface AgentResult {
  agent_id: string;
  name: string;
  satisfaction: number; // 0-100
  concessions_made: number;
  notes: string | null;
}

export interface ConcessionPoint {
  round: number;
  agent_id: string;
  value: number;
  label: string | null; // what the value measures, e.g. "Price (USD)"
}

export interface OutcomeReport {
  session_id: string;
  scenario_name: string;
  mode: Mode;
  status: SessionStatus;
  rounds_elapsed: number;
  terms: Record<string, OfferValue>;
  summary: string;
  agents: AgentResult[];
  concession_timeline: ConcessionPoint[];
}

// ---- WebSocket messages
export type ServerEvent =
  | { type: 'thinking'; agent_id: string }
  | { type: 'turn'; turn: Turn }
  | { type: 'metrics'; metrics: Metrics }
  | { type: 'awaiting_human'; agent_id: string }
  | { type: 'deadlock'; message: string }
  | { type: 'finished'; status: SessionStatus }
  | { type: 'error'; message: string };

export type ClientEvent =
  | { type: 'start' }
  | { type: 'human_turn'; action: Action; message: string; offer: Offer | null };
