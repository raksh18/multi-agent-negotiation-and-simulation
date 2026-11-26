import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { Turn } from '../types';
import { formatValue, humanize } from '../lib/utils';
import StanceBadge from './StanceBadge';

interface Props { turn: Turn; color: string; isYou: boolean }

export default function TranscriptMessage({ turn, color, isYou }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <article className="card p-4" style={{ borderLeft: `4px solid ${color}` }}>
      <header className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-semibold" style={{ color }}>{turn.agent_name}{isYou && ' (you)'}</span>
        <span className="text-ink-faint">Round {turn.round}</span>
        <span className="rounded bg-paper px-1.5 py-0.5 text-xs font-medium capitalize text-ink-soft">{turn.action}</span>
        <StanceBadge stance={turn.stance} />
      </header>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{turn.message}</p>

      {turn.offer && Object.keys(turn.offer).length > 0 && (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 rounded-md bg-paper p-3 text-sm sm:grid-cols-3">
          {Object.entries(turn.offer).map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs text-ink-soft">{humanize(k)}</dt>
              <dd className="font-medium">{formatValue(v)}</dd>
            </div>
          ))}
        </dl>
      )}

      {turn.reasoning && (
        <div className="mt-3">
          <button className="flex items-center gap-1 text-xs font-medium text-ink-soft hover:text-ink" onClick={() => setOpen(!open)} aria-expanded={open}>
            {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />} Agent reasoning
          </button>
          {open && <p className="mt-1 whitespace-pre-wrap rounded-md bg-paper p-3 text-xs leading-relaxed text-ink-soft">{turn.reasoning}</p>}
        </div>
      )}
    </article>
  );
}
