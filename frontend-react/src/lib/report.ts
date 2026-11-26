import { jsPDF } from 'jspdf';
import type { OutcomeReport, Turn } from '../types';
import { formatValue, humanize } from './utils';

function save(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadTranscriptJSON(sessionId: string, turns: Turn[]) {
  save(new Blob([JSON.stringify(turns, null, 2)], { type: 'application/json' }), `transcript-${sessionId}.json`);
}

export function downloadTranscriptCSV(sessionId: string, turns: Turn[]) {
  const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const header = ['round', 'agent', 'action', 'stance', 'message', 'reasoning', 'offer', 'timestamp'];
  const rows = turns.map((t) =>
    [t.round, t.agent_name, t.action, t.stance, t.message, t.reasoning, t.offer ? JSON.stringify(t.offer) : '', t.timestamp].map(esc).join(','),
  );
  save(new Blob([[header.join(','), ...rows].join('\n')], { type: 'text/csv' }), `transcript-${sessionId}.csv`);
}

export function downloadReportPDF(report: OutcomeReport, turns: Turn[]) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  const M = 48;
  let y = M;

  const ensure = (h: number) => { if (y + h > H - M) { doc.addPage(); y = M; } };
  const heading = (text: string) => {
    ensure(30); y += 10;
    doc.setFont('helvetica', 'bold'); doc.setFontSize(13); doc.text(text, M, y); y += 18;
  };
  const paragraph = (text: string, size = 10, bold = false) => {
    doc.setFont('helvetica', bold ? 'bold' : 'normal'); doc.setFontSize(size);
    for (const line of doc.splitTextToSize(text, W - M * 2) as string[]) {
      ensure(size + 4); doc.text(line, M, y); y += size + 4;
    }
  };

  doc.setFont('helvetica', 'bold'); doc.setFontSize(20);
  doc.text('Negotiation report', M, y); y += 24;
  paragraph(`${report.scenario_name} (${report.mode} mode)`, 11);
  paragraph(`Result: ${humanize(report.status)} after ${report.rounds_elapsed} rounds`, 11, true);

  heading('Summary');
  paragraph(report.summary);

  heading('Final agreement terms');
  const entries = Object.entries(report.terms);
  if (entries.length === 0) paragraph('No terms were agreed.');
  entries.forEach(([k, v]) => paragraph(`${humanize(k)}: ${formatValue(v)}`));

  heading('Objective satisfaction by agent');
  report.agents.forEach((a) => {
    paragraph(`${a.name}: ${Math.round(a.satisfaction)}% satisfied, ${a.concessions_made} concessions`, 10, true);
    if (a.notes) paragraph(a.notes);
  });

  heading('Transcript');
  turns.forEach((t) => {
    paragraph(`Round ${t.round} - ${t.agent_name} (${t.action})`, 10, true);
    paragraph(t.message);
    if (t.offer) paragraph(`Offer: ${Object.entries(t.offer).map(([k, v]) => `${humanize(k)} ${formatValue(v)}`).join('; ')}`);
    y += 4;
  });

  doc.save(`negotiation-report-${report.session_id}.pdf`);
}
