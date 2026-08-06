import { useState } from "react";

import type { RadarData, RadarMetric as BklitMetric } from "./charts/radar-context";
import { useRadar } from "./charts/radar-context";
import { RadarArea } from "./charts/radar-area";
import { RadarAxis } from "./charts/radar-axis";
import { RadarChart } from "./charts/radar-chart";
import { RadarGrid } from "./charts/radar-grid";
import { RadarLabels } from "./charts/radar-labels";

import type { RadarMetric } from "../api/types";
import { useReducedMotion } from "../lib/useReducedMotion";

// The floodlit accent — the single-series colour for a player's profile polygon.
const ACCENT = "#34d399";

/**
 * Hover layer: an invisible hit target on each metric vertex that, on hover,
 * reveals that stat's percentile as a haloed number (no box — a dark text
 * outline keeps it legible over the grid). Restores the per-stat readout the
 * old Recharts tooltip gave. Lives inside <RadarChart> so it can read the
 * radar context (vertex positions + values).
 */
function RadarValueTips() {
  const { metrics, data, getPointPosition } = useRadar();
  const [hover, setHover] = useState<number | null>(null);
  const series = data[0];
  if (!series) return null;

  return (
    <g>
      {metrics.map((m, i) => {
        const value = Math.round(series.values[m.key] ?? 0);
        const { x, y } = getPointPosition(i, series.values[m.key] ?? 0);
        // push the readout a touch further out from centre so it clears the dot
        const out = Math.hypot(x, y) || 1;
        const lx = x + (x / out) * 14;
        const ly = y + (y / out) * 14;
        return (
          <g key={m.key}>
            {hover === i && (
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                dominantBaseline="middle"
                style={{
                  fill: ACCENT,
                  fontSize: 13,
                  fontWeight: 600,
                  paintOrder: "stroke",
                  stroke: "var(--canvas)",
                  strokeWidth: 3.5,
                  strokeLinejoin: "round",
                }}
              >
                {value}
                <tspan style={{ fill: "var(--ink-3)", fontSize: 9, fontWeight: 500 }}>
                  {" "}
                  pct
                </tspan>
              </text>
            )}
            <circle
              cx={x}
              cy={y}
              r={16}
              fill="transparent"
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
            >
              <title>{`${m.label}: ${value}th percentile`}</title>
            </circle>
          </g>
        );
      })}
    </g>
  );
}

/**
 * Player percentile radar, rendered with bklit (@visx + Motion). One series =
 * the player, plotted 0 (centre) → 100 (edge) so every profile is on the same
 * fixed scale and nothing is visually inflated.
 */
export function StatRadar({ metrics }: { metrics: RadarMetric[] }) {
  const reduced = useReducedMotion();

  // bklit's axes are {key,label}; the series carries a values map keyed by axis.
  const axes: BklitMetric[] = metrics.map((m) => ({ key: m.metric, label: m.label }));
  const series: RadarData[] = [
    {
      label: "vs position",
      color: ACCENT,
      values: Object.fromEntries(
        metrics.map((m) => [m.metric, Math.round(m.percentile * 100)]),
      ),
    },
  ];

  return (
    <div className="mx-auto w-full max-w-[340px]">
      <RadarChart data={series} metrics={axes} animate={!reduced} levels={5} margin={56}>
        <RadarGrid showLabels={false} />
        <RadarAxis />
        <RadarArea index={0} color={ACCENT} showPoints showGlow={!reduced} />
        <RadarLabels fontSize={11} />
        <RadarValueTips />
      </RadarChart>
    </div>
  );
}
