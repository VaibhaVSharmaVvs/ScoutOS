import { Group } from "@visx/group";
import { ParentSize } from "@visx/responsive";
import { scaleLinear, scalePoint } from "@visx/scale";
import { motion } from "motion/react";
import { useMemo, useState } from "react";

import { money } from "../lib/format";
import { useReducedMotion } from "../lib/useReducedMotion";

export interface ValuePoint {
  label: string;
  value: number;
}

// Custom line chart on the same primitives bklit uses (@visx + Motion), styled
// with the floodlit tokens. Unlike bklit's date×count LineChart this keeps a
// MONEY y-axis and a CATEGORICAL x-axis — the two things our value/career charts
// need. Same API as before ({ data, color }) so call sites are unchanged.

const ACCENT = "#34d399";
const HEIGHT = 240;
const M = { top: 14, right: 18, bottom: 26, left: 58 };

export function ValueChart({ data, color = ACCENT }: { data: ValuePoint[]; color?: string }) {
  if (data.length === 0) return null;
  return (
    <div style={{ width: "100%", height: HEIGHT }}>
      <ParentSize>
        {({ width }) => (width > 0 ? <Chart width={width} data={data} color={color} /> : null)}
      </ParentSize>
    </div>
  );
}

function Chart({ width, data, color }: { width: number; data: ValuePoint[]; color: string }) {
  const reduced = useReducedMotion();
  const [hover, setHover] = useState<number | null>(null);

  const iw = Math.max(1, width - M.left - M.right);
  const ih = HEIGHT - M.top - M.bottom;

  const x = useMemo(
    () => scalePoint<string>({ domain: data.map((d) => d.label), range: [0, iw], padding: 0.5 }),
    [data, iw],
  );

  // Money y-axis. Domain spans the data (not forced to 0) so small movements in
  // a high value stay visible — but never dips below 0.
  const y = useMemo(() => {
    const vals = data.map((d) => d.value);
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const pad = (max - min) * 0.18 || max * 0.1 || 1;
    return scaleLinear<number>({
      domain: [Math.max(0, min - pad), max + pad],
      range: [ih, 0],
      nice: true,
    });
  }, [data, ih]);

  const px = (d: ValuePoint) => x(d.label) ?? 0;
  const py = (d: ValuePoint) => y(d.value);
  const path = data.map((d, i) => `${i ? "L" : "M"} ${px(d)} ${py(d)}`).join(" ");
  const yTicks = y.ticks(4);
  // thin x labels to ~6 so dense monthly histories don't collide
  const step = Math.max(1, Math.ceil(data.length / 6));

  const hv = hover != null ? data[hover] : null;

  return (
    <div style={{ position: "relative", width, height: HEIGHT }}>
      <svg width={width} height={HEIGHT} role="img" aria-label="Value over time">
        <Group left={M.left} top={M.top}>
          {/* horizontal gridlines + money labels */}
          {yTicks.map((t) => (
            <g key={t}>
              <line x1={0} x2={iw} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
              <text
                x={-10}
                y={y(t)}
                textAnchor="end"
                dominantBaseline="middle"
                fill="var(--ink-3)"
                fontSize={11}
                className="tnum"
              >
                {money(t)}
              </text>
            </g>
          ))}

          {/* categorical x labels */}
          {data.map((d, i) =>
            i % step === 0 || i === data.length - 1 ? (
              <text
                key={`${d.label}-${i}`}
                x={px(d)}
                y={ih + 18}
                textAnchor="middle"
                fill="var(--ink-3)"
                fontSize={11}
              >
                {d.label}
              </text>
            ) : null,
          )}

          {/* hover crosshair */}
          {hv && (
            <line x1={px(hv)} x2={px(hv)} y1={0} y2={ih} stroke="var(--line-strong)" strokeWidth={1} />
          )}

          {/* the line — Motion draws it on with pathLength */}
          <motion.path
            d={path}
            fill="none"
            stroke={color}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={reduced ? false : { pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
          />

          {/* data points */}
          {data.map((d, i) => (
            <motion.circle
              key={`${d.label}-${i}`}
              cx={px(d)}
              cy={py(d)}
              r={hover === i ? 5 : 3}
              fill={color}
              initial={reduced ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: reduced ? 0 : 0.32 + i * 0.02, duration: 0.3 }}
            />
          ))}

          {/* one overlay captures the mouse and snaps to the nearest point */}
          <rect
            x={0}
            y={0}
            width={iw}
            height={ih}
            fill="transparent"
            onMouseMove={(e) => {
              const mx = e.clientX - e.currentTarget.getBoundingClientRect().left;
              let best = 0;
              let bd = Infinity;
              data.forEach((d, i) => {
                const dx = Math.abs(px(d) - mx);
                if (dx < bd) {
                  bd = dx;
                  best = i;
                }
              });
              setHover(best);
            }}
            onMouseLeave={() => setHover(null)}
          />
        </Group>
      </svg>

      {/* tooltip — HTML overlay so text is crisp; positioned over the hovered point */}
      {hv && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-md border border-strong bg-surface-overlay px-2.5 py-1.5 text-caption shadow-lg"
          style={{ left: M.left + px(hv), top: M.top + py(hv) - 8 }}
        >
          <div className="text-ink-3">{hv.label}</div>
          <div className="tnum font-semibold" style={{ color }}>
            {money(hv.value)}
          </div>
        </div>
      )}
    </div>
  );
}
