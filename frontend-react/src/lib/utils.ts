import type { OfferValue } from '../types';

// One colour per agent, assigned by position so the same agent is always the same colour.
export const AGENT_COLORS = ['#0F766E', '#B7791F', '#6D4AA8', '#B4332E', '#2B6CB0', '#4D7C0F'];
export const agentColor = (index: number) => AGENT_COLORS[index % AGENT_COLORS.length];

export const formatValue = (v: OfferValue): string =>
  typeof v === 'number' ? v.toLocaleString() : String(v);

export const humanize = (key: string) =>
  key.replace(/[_-]+/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
