import type { RadarData, RadarMetric as BklitMetric } from "./charts/radar-context";
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
      </RadarChart>
    </div>
  );
}
