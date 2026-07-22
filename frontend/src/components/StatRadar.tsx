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
import { useReducedMotion } from "../lib/useReducedMotion";

export function StatRadar({ metrics }: { metrics: RadarMetric[] }) {
  const reduced = useReducedMotion();
  const data = metrics.map((m) => ({ axis: m.label, pct: Math.round(m.percentile * 100) }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} outerRadius="70%">
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis dataKey="axis" tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 12 }} />
        {/* fixed 0 (centre) -> 100 (edge) so every player is on the same scale */}
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} tickCount={5} />
        <Radar
          dataKey="pct"
          stroke="#34d399"
          fill="#34d399"
          fillOpacity={0.28}
          strokeWidth={2}
          isAnimationActive={!reduced}
          animationDuration={550}
          animationEasing="ease-out"
        />
        <Tooltip
          contentStyle={{
            background: "#1d282d",
            border: "1px solid rgba(255,255,255,0.13)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(v) => [`${v}th pct`, "vs position"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
