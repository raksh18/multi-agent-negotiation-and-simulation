import { Link } from 'react-router-dom';
import { loadScenarios } from '../lib/api';
import { useAsync } from '../hooks/useAsync';
import { ErrorBox, Loading } from '../components/Status';
import OfflineNotice from '../components/OfflineNotice';

export default function ScenarioSelect() {
  const { data: result, error, loading, retry } = useAsync(() => loadScenarios(), []);

  const data = result?.data;
  return (
    <div>
      <h1 className="text-3xl font-bold">Choose a negotiation scenario</h1>
      <p className="mt-2 max-w-2xl text-ink-soft">
        Watch AI agents negotiate with each other, or step in and negotiate against them yourself.
      </p>

      <div className="mt-6">
        {result?.offline && <OfflineNotice />}
        {loading && <Loading label="Loading scenarios…" />}
        {error && <ErrorBox message={error} onRetry={retry} />}
        {data && data.length === 0 && <p className="text-ink-soft">The server has no scenarios yet.</p>}
        <div className="grid gap-4 md:grid-cols-3">
          {data?.map((s) => (
            <Link key={s.id} to={`/configure/${s.id}`} className="card block p-5 transition-colors hover:border-teal">
              <h2 className="text-lg font-semibold">{s.name}</h2>
              <p className="mt-2 text-sm text-ink-soft">{s.description}</p>
              <p className="mt-4 text-xs text-ink-soft">{s.agents.map((a) => a.role).join(' vs ')}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
