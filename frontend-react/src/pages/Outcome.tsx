import { Link, useParams } from 'react-router-dom';
import { Download } from 'lucide-react';
import clsx from 'clsx';
import { api } from '../lib/api';
import { useAsync } from '../hooks/useAsync';
import { ErrorBox, Loading } from '../components/Status';
import ConcessionChart from '../components/ConcessionChart';
import { downloadReportPDF, downloadTranscriptCSV, downloadTranscriptJSON } from '../lib/report';
import { agentColor, formatValue, humanize } from '../lib/utils';

export default function Outcome() {
  const { sessionId = '' } = useParams();
  const { data, error, loading, retry } = useAsync(
    async () => {
      const [report, transcript] = await Promise.all([api.getReport(sessionId), api.getTranscript(sessionId)]);
      return { report, transcript };
    },
    [sessionId],
  );

  if (loading) return <Loading label="Building report…" />;
  if (error || !data) return <ErrorBox message={error ?? 'Report not found'} onRetry={retry} />;

  const { report, transcript } = data;
  const agreed = report.status === 'agreement';
  const terms = Object.entries(report.terms);

  return (
    <div className="space-y-6">
      <div className={clsx('rounded-lg border p-5', agreed ? 'border-teal/30 bg-teal-tint' : 'border-brick/30 bg-brick-tint')}>
        <h1 className="text-3xl font-bold">{agreed ? 'Agreement reached' : report.status === 'deadlock' ? 'Ended in deadlock' : 'Negotiation broke down'}</h1>
        <p className="mt-1 text-sm text-ink-soft">{report.scenario_name} · {report.rounds_elapsed} rounds · {report.mode} mode</p>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed">{report.summary}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button className="btn-primary" onClick={() => downloadReportPDF(report, transcript)}><Download className="h-4 w-4" /> Report (PDF)</button>
        <button className="btn-ghost" onClick={() => downloadTranscriptCSV(sessionId, transcript)}><Download className="h-4 w-4" /> Transcript (CSV)</button>
        <button className="btn-ghost" onClick={() => downloadTranscriptJSON(sessionId, transcript)}><Download className="h-4 w-4" /> Transcript (JSON)</button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card p-5">
          <h2 className="text-lg font-semibold">Final terms</h2>
          {terms.length === 0 ? <p className="mt-2 text-sm text-ink-soft">No terms were agreed.</p> : (
            <dl className="mt-3 divide-y divide-line text-sm">
              {terms.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 py-2"><dt className="text-ink-soft">{humanize(k)}</dt><dd className="font-medium">{formatValue(v)}</dd></div>
              ))}
            </dl>
          )}
        </section>

        <section className="card p-5">
          <h2 className="text-lg font-semibold">Objective satisfaction</h2>
          <div className="mt-3 space-y-4">
            {report.agents.map((a, i) => (
              <div key={a.agent_id}>
                <div className="flex justify-between text-sm"><span className="font-medium">{a.name}</span><span>{Math.round(a.satisfaction)}%</span></div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-paper">
                  <div className="h-full rounded-full" style={{ width: `${a.satisfaction}%`, background: agentColor(i) }} />
                </div>
                <p className="mt-1 text-xs text-ink-soft">{a.concessions_made} concessions{a.notes ? ` · ${a.notes}` : ''}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="card p-5">
        <h2 className="mb-3 text-lg font-semibold">Concession timeline</h2>
        <ConcessionChart points={report.concession_timeline} agents={report.agents} />
      </section>

      <div className="flex gap-3">
        <Link className="btn-ghost" to={`/arena/${sessionId}`}>Back to transcript</Link>
        <Link className="btn-primary" to="/">New negotiation</Link>
      </div>
    </div>
  );
}
