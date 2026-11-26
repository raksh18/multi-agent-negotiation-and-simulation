import { Loader2 } from 'lucide-react';

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-ink-soft" role="status">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-brick/30 bg-brick-tint p-4 text-sm" role="alert">
      <p className="font-medium text-brick">Something went wrong</p>
      <p className="mt-1 text-ink-soft">{message}</p>
      {onRetry && <button className="btn-ghost mt-3" onClick={onRetry}>Try again</button>}
    </div>
  );
}
