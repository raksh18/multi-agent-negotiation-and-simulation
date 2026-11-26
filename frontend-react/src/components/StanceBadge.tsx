import clsx from 'clsx';
import type { Stance } from '../types';

const STYLES: Record<string, string> = {
  accepting: 'bg-teal-tint text-teal-dark',
  flexible: 'bg-teal-tint text-teal-dark',
  conceding: 'bg-brass-tint text-brass',
  firm: 'bg-brass-tint text-brass',
  rejecting: 'bg-brick-tint text-brick',
};

export default function StanceBadge({ stance }: { stance: Stance }) {
  return (
    <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium', STYLES[stance.toLowerCase()] ?? 'bg-paper text-ink-soft')}>
      {stance}
    </span>
  );
}
