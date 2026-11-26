import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { AgentResult, ConcessionPoint } from '../types';
import { agentColor } from '../lib/utils';

interface Props { points: ConcessionPoint[]; agents: AgentResult[] }

/** Round-by-round value of each agent's offers, so you can see who moved and when. */
export default function ConcessionChart({ points, agents }: Props) {
  if (points.length === 0) return <p className="text-sm text-ink-soft">No numeric offers were made, so there is no concession timeline.</p>;

  const rounds = Array.from(new Set(points.map((p) => p.round))).sort((a, b) => a - b);
  const data = rounds.map((round) => {
    const row: Record<string, number | undefined> = { round };
    for (const p of points) if (p.round === round) row[p.agent_id] = p.value;
    return row;
  });
  const label = points.find((p) => p.label)?.label ?? 'Offer value';

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid stroke="#D5DCE3" strokeDasharray="3 3" />
          <XAxis dataKey="round" label={{ value: 'Round', position: 'insideBottom', offset: -4 }} />
          <YAxis label={{ value: label, angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          {agents.map((a, i) => (
            <Line key={a.agent_id} type="monotone" dataKey={a.agent_id} name={a.name} stroke={agentColor(i)} strokeWidth={2} connectNulls dot />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
