import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import type { RadarMetric } from "../api/types";

export function StatRadar({ metrics }: { metrics: RadarMetric[] }) {
  const data = metrics.map((m) => ({ axis: m.label, pct: Math.round(m.percentile * 100) }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} outerRadius="70%">
        <PolarGrid stroke="rgba(255,255,255,0.12)" />
        <PolarAngleAxis dataKey="axis" tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }} />
        {/* fixed 0 (centre) -> 100 (edge) so every player is on the same scale */}
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} tickCount={5} />
        <Radar dataKey="pct" stroke="#22c55e" fill="#22c55e" fillOpacity={0.35} />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
          formatter={(v) => [`${v}th pct`, "vs position"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
