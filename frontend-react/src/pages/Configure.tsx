import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import clsx from 'clsx';
import { api, loadScenario } from '../lib/api';
import { useAsync } from '../hooks/useAsync';
import { ErrorBox, Loading } from '../components/Status';
import OfflineNotice from '../components/OfflineNotice';
import { agentColor } from '../lib/utils';
import type { AgentOverride, Mode, Personality, Scenario } from '../types';

const PERSONALITIES: { value: Personality; label: string; hint: string }[] = [
  { value: 'aggressive', label: 'Aggressive', hint: 'Pushes hard, concedes slowly' },
  { value: 'collaborative', label: 'Collaborative', hint: 'Looks for win-win trades' },
  { value: 'risk-averse', label: 'Risk-averse', hint: 'Prefers safe, certain deals' },
];

export default function Configure() {
  const { scenarioId = '' } = useParams();
  const { data: result, error, loading, retry } = useAsync(() => loadScenario(scenarioId), [scenarioId]);
  const scenario = result?.data;

  if (loading) return <Loading label="Loading scenario…" />;
  if (error || !scenario) return <ErrorBox message={error ?? 'Scenario not found'} onRetry={retry} />;
  return <>{result?.offline && <OfflineNotice />}<ConfigForm scenario={scenario} /></>;
}

function ConfigForm({ scenario }: { scenario: Scenario }) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('simulation');
  const [userAgentId, setUserAgentId] = useState<string | null>(null);
  const [maxRounds, setMaxRounds] = useState(scenario.default_max_rounds);
  const [params, setParams] = useState<Record<string, string>>({});
  const [agents, setAgents] = useState<AgentOverride[]>(
    scenario.agents.map((a) => ({ id: a.id, name: a.name, goals: a.goals, personality: a.personality })),
  );
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (mode === 'practice' && !userAgentId) setUserAgentId(scenario.agents[0]?.id ?? null);
  }, [mode, userAgentId, scenario.agents]);

  const updateAgent = (id: string, patch: Partial<AgentOverride>) =>
    setAgents((prev) => prev.map((a) => (a.id === id ? { ...a, ...patch } : a)));

  const missing = scenario.parameters.filter((p) => p.required && !params[p.key]?.trim());
  const canStart = missing.length === 0 && maxRounds > 0 && !submitting;

  const start = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const parameters: Record<string, string | number> = {};
      for (const p of scenario.parameters) {
        const raw = params[p.key]?.trim();
        if (raw) parameters[p.key] = p.type === 'number' ? Number(raw) : raw;
      }
      const { session_id } = await api.createSession({
        scenario_id: scenario.id, mode, max_rounds: maxRounds, parameters, agents,
        user_agent_id: mode === 'practice' ? userAgentId : null,
      });
      navigate(`/arena/${session_id}`);
    } catch (e) {
      const msg = (e as Error).message;
      setSubmitError(msg.startsWith('500') || msg.includes('Failed to fetch') ? 'Could not reach the negotiation server. Start the backend on port 8000 and try again.' : msg);
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">{scenario.name}</h1>
        <p className="mt-2 max-w-2xl text-ink-soft">{scenario.description}</p>
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">How do you want to run it?</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {([
            ['simulation', 'Simulation', 'Watch the agents negotiate with each other.'],
            ['practice', 'Practice', 'Take one role and negotiate against the AI agents.'],
          ] as [Mode, string, string][]).map(([value, title, text]) => (
            <button key={value} type="button" onClick={() => setMode(value)} aria-pressed={mode === value}
              className={clsx('card p-4 text-left', mode === value && 'border-teal bg-teal-tint')}>
              <p className="font-semibold">{title}</p>
              <p className="mt-1 text-sm text-ink-soft">{text}</p>
            </button>
          ))}
        </div>
      </section>

      {scenario.parameters.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Scenario details</h2>
          <div className="card grid gap-4 p-4 md:grid-cols-2">
            {scenario.parameters.map((p) => (
              <label key={p.key} className={clsx('text-sm font-medium', p.type === 'textarea' && 'md:col-span-2')}>
                {p.label}{p.required && <span className="text-brick"> *</span>}
                {p.type === 'textarea' ? (
                  <textarea className="input mt-1 font-normal" rows={4} placeholder={p.placeholder} value={params[p.key] ?? ''}
                    onChange={(e) => setParams({ ...params, [p.key]: e.target.value })} />
                ) : (
                  <input className="input mt-1 font-normal" type={p.type === 'number' ? 'number' : 'text'} placeholder={p.placeholder}
                    value={params[p.key] ?? ''} onChange={(e) => setParams({ ...params, [p.key]: e.target.value })} />
                )}
                {p.help && <span className="mt-1 block text-xs font-normal text-ink-soft">{p.help}</span>}
              </label>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Agents</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {scenario.agents.map((base, i) => {
            const a = agents.find((x) => x.id === base.id)!;
            const isYou = mode === 'practice' && userAgentId === base.id;
            return (
              <div key={base.id} className="card p-4" style={{ borderTop: `4px solid ${agentColor(i)}` }}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <input className="input font-semibold" aria-label={`${base.role} name`} value={a.name} onChange={(e) => updateAgent(base.id, { name: e.target.value })} />
                    <p className="mt-1 text-xs text-ink-soft">{base.role}</p>
                  </div>
                  {mode === 'practice' && (
                    <button type="button" className={isYou ? 'btn-primary' : 'btn-ghost'} onClick={() => setUserAgentId(base.id)}>
                      {isYou ? 'You play this role' : 'Play this role'}
                    </button>
                  )}
                </div>

                <label className="mt-4 block text-xs font-medium text-ink-soft">
                  Goals (one per line)
                  <textarea className="input mt-1 font-normal text-ink" rows={4} value={a.goals.join('\n')}
                    onChange={(e) => updateAgent(base.id, { goals: e.target.value.split('\n').filter((g) => g.trim()) })} />
                </label>

                {base.constraints.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-medium text-ink-soft">Constraints</p>
                    <ul className="mt-1 list-disc pl-5 text-sm">{base.constraints.map((c) => <li key={c}>{c}</li>)}</ul>
                  </div>
                )}

                {!isYou && (
                  <fieldset className="mt-4">
                    <legend className="text-xs font-medium text-ink-soft">Personality</legend>
                    <div className="mt-1 grid gap-2 sm:grid-cols-3">
                      {PERSONALITIES.map((p) => (
                        <button key={p.value} type="button" aria-pressed={a.personality === p.value}
                          onClick={() => updateAgent(base.id, { personality: p.value })}
                          className={clsx('rounded-md border p-2 text-left text-xs', a.personality === p.value ? 'border-teal bg-teal-tint' : 'border-line hover:bg-paper')}>
                          <span className="block font-semibold">{p.label}</span>
                          <span className="text-ink-soft">{p.hint}</span>
                        </button>
                      ))}
                    </div>
                  </fieldset>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className="max-w-xs">
        <label className="text-sm font-medium">
          Maximum rounds
          <input className="input mt-1" type="number" min={1} value={maxRounds} onChange={(e) => setMaxRounds(Number(e.target.value))} />
        </label>
        <p className="mt-1 text-xs text-ink-soft">If no deal is reached by then, the orchestrator declares a breakdown.</p>
      </section>

      {submitError && <ErrorBox message={submitError} />}
      <div className="flex items-center gap-3">
        <button className="btn-primary" disabled={!canStart} onClick={start}>{submitting ? 'Starting…' : 'Start negotiation'}</button>
        {missing.length > 0 && <span className="text-sm text-ink-soft">Fill in: {missing.map((m) => m.label).join(', ')}</span>}
      </div>
    </div>
  );
}
