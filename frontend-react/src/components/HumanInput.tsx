import { useState } from 'react';
import type { Action, Offer, OfferField } from '../types';

interface Props {
  agentName: string;
  fields: OfferField[];
  disabled: boolean;
  onSubmit: (action: Action, message: string, offer: Offer | null) => boolean;
}

const ACTIONS: { value: Action; label: string }[] = [
  { value: 'offer', label: 'Make an offer' },
  { value: 'counter', label: 'Counter' },
  { value: 'accept', label: 'Accept' },
  { value: 'reject', label: 'Reject' },
];

export default function HumanInput({ agentName, fields, disabled, onSubmit }: Props) {
  const [action, setAction] = useState<Action>('counter');
  const [message, setMessage] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const needsTerms = action === 'offer' || action === 'counter';

  const submit = () => {
    let offer: Offer | null = null;
    if (needsTerms) {
      offer = {};
      for (const f of fields) {
        const raw = values[f.key]?.trim();
        if (!raw) continue;
        offer[f.key] = f.type === 'number' ? Number(raw) : raw;
      }
      if (Object.keys(offer).length === 0) offer = null;
    }
    if (onSubmit(action, message.trim(), offer)) {
      setMessage('');
      setValues({});
    }
  };

  const canSend = !disabled && message.trim().length > 0;

  return (
    <form className="card space-y-3 p-4" onSubmit={(e) => { e.preventDefault(); if (canSend) submit(); }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">Your turn as {agentName}</h2>
        <div className="flex gap-1" role="radiogroup" aria-label="Action">
          {ACTIONS.map((a) => (
            <button key={a.value} type="button" role="radio" aria-checked={action === a.value}
              className={`rounded-md border px-3 py-1 text-xs font-medium ${action === a.value ? 'border-teal bg-teal-tint text-teal-dark' : 'border-line bg-white text-ink-soft hover:bg-paper'}`}
              onClick={() => setAction(a.value)}>{a.label}</button>
          ))}
        </div>
      </div>

      {needsTerms && fields.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {fields.map((f) => (
            <label key={f.key} className="text-xs text-ink-soft">
              {f.label}{f.unit ? ` (${f.unit})` : ''}
              <input className="input mt-1" type={f.type === 'number' ? 'number' : 'text'} value={values[f.key] ?? ''}
                onChange={(e) => setValues({ ...values, [f.key]: e.target.value })} />
            </label>
          ))}
        </div>
      )}

      <label className="block text-xs text-ink-soft">
        Message
        <textarea className="input mt-1" rows={3} value={message} onChange={(e) => setMessage(e.target.value)}
          placeholder="Explain your position or respond to the last offer" />
      </label>
      <div className="flex justify-end">
        <button type="submit" className="btn-primary" disabled={!canSend}>Send</button>
      </div>
    </form>
  );
}
