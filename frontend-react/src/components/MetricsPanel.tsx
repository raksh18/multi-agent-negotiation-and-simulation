import type { AgentConfig, Metrics } from '../types';
import { agentColor } from '../lib/utils';
import StanceBadge from './StanceBadge';

interface Props {
  agents: AgentConfig[];
  metrics: Metrics | null;
  maxRounds: number;
  turnCount: number;
  thinkingAgentId: string | null;
  deadlockMessage: string | null;
}

export default function MetricsPanel({ agents, metrics, maxRounds, turnCount, thinkingAgentId, deadlockMessage }: Props) {
  const round = metrics?.round ?? 0;
  const max = metrics?.max_rounds ?? maxRounds;
  const pct = max > 0 ? Math.min(100, (round / max) * 100) : 0;

  return (
    <aside className="space-y-4" aria-label="Live negotiation metrics">
      <section className="card p-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold">Round</h2>
          <span className="text-sm text-ink-soft">{round} of {max}</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-paper" role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={round}>
          <div className="h-full rounded-full bg-teal transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-2 text-xs text-ink-soft">{turnCount} messages exchanged</p>
      </section>

      {deadlockMessage && (
        <section className="rounded-lg border border-brass/40 bg-brass-tint p-4 text-sm">
          <h2 className="font-semibold text-brass">Deadlock detected</h2>
          <p className="mt-1 text-ink-soft">{deadlockMessage}</p>
        </section>
      )}

      <section className="card divide-y divide-line">
        <h2 className="p-4 pb-3 text-sm font-semibold">Agents</h2>
        {agents.map((a, i) => {
          const stance = metrics?.stances[a.id];
          const sat = metrics?.satisfaction[a.id];
          return (
            <div key={a.id} className="p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: agentColor(i) }} />
                  <span className="text-sm font-medium">{a.name}</span>
                </div>
                {stance && <StanceBadge stance={stance} />}
              </div>
              <p className="mt-0.5 text-xs text-ink-soft">{a.role} · {a.personality}</p>
              {thinkingAgentId === a.id && <p className="mt-1 text-xs italic text-teal">Thinking…</p>}
              {sat !== undefined && (
                <div className="mt-2">
                  <div className="flex justify-between text-xs text-ink-soft"><span>Objective satisfaction</span><span>{Math.round(sat)}%</span></div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-paper">
                    <div className="h-full rounded-full transition-all" style={{ width: `${sat}%`, background: agentColor(i) }} />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </section>
    </aside>
  );
}
