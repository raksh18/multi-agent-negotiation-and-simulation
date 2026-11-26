import { useEffect, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { useAsync } from '../hooks/useAsync';
import { useNegotiation } from '../hooks/useNegotiation';
import { ErrorBox, Loading } from '../components/Status';
import TranscriptMessage from '../components/TranscriptMessage';
import MetricsPanel from '../components/MetricsPanel';
import HumanInput from '../components/HumanInput';
import { agentColor } from '../lib/utils';
import type { Session } from '../types';

export default function Arena() {
  const { sessionId = '' } = useParams();
  const { data: session, error, loading, retry } = useAsync(() => api.getSession(sessionId), [sessionId]);

  if (loading) return <Loading label="Loading negotiation…" />;
  if (error || !session) return <ErrorBox message={error ?? 'Session not found'} onRetry={retry} />;
  return <ArenaView session={session} />;
}

function ArenaView({ session }: { session: Session }) {
  const neg = useNegotiation(session.session_id);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [neg.turns.length, neg.thinkingAgentId, neg.runState]);

  const indexOf = (id: string) => Math.max(0, session.agents.findIndex((a) => a.id === id));
  const thinking = session.agents.find((a) => a.id === neg.thinkingAgentId);
  const yourAgent = session.agents.find((a) => a.id === (neg.awaitingAgentId ?? session.user_agent_id));

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">{session.scenario_name}</h1>
          <p className="text-sm text-ink-soft">{session.mode === 'practice' ? 'Practice mode' : 'Simulation mode'}</p>
        </div>
        {neg.runState === 'finished' && (
          <Link className="btn-primary" to={`/outcome/${session.session_id}`}>View outcome report</Link>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          {neg.turns.length === 0 && neg.runState !== 'error' && <Loading label="Waiting for the first offer…" />}
          {neg.turns.map((t, i) => (
            <TranscriptMessage key={i} turn={t} color={agentColor(indexOf(t.agent_id))} isYou={t.agent_id === session.user_agent_id} />
          ))}

          {thinking && <p className="text-sm italic text-ink-soft" role="status">{thinking.name} is thinking…</p>}
          {neg.runState === 'error' && <ErrorBox message={neg.error ?? 'Unknown error'} />}

          {neg.runState === 'finished' && (
            <div className="card p-4 text-sm">
              Negotiation ended: <strong>{neg.finalStatus}</strong>.{' '}
              <Link className="font-medium text-teal underline" to={`/outcome/${session.session_id}`}>See the full report</Link>
            </div>
          )}

          {neg.runState === 'awaiting_human' && yourAgent && (
            <HumanInput agentName={yourAgent.name} fields={session.offer_fields} disabled={false} onSubmit={neg.sendHumanTurn} />
          )}
          <div ref={bottomRef} />
        </div>

        <MetricsPanel agents={session.agents} metrics={neg.metrics} maxRounds={session.max_rounds}
          turnCount={neg.turns.length} thinkingAgentId={neg.thinkingAgentId} deadlockMessage={neg.deadlockMessage} />
      </div>
    </div>
  );
}
