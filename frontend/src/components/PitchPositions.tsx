// A football pitch with the player's positions as coloured dots:
// primary = green, secondary = yellow, other playable = red, rest = grey.
// Works with both the granular (side-aware) and side-agnostic position sets.

import type { PositionPrediction } from "../api/types";

// position -> pitch coordinates (x 0-100 defence→attack, y 0-100 left→right flank).
// role-only names (Full-Back, Winger) map to both flanks.
const COORDS: Record<string, [number, number][]> = {
  Goalkeeper: [[6, 50]],
  "Centre-Back": [[22, 50]],
  "Left-Back": [[24, 16]],
  "Right-Back": [[24, 84]],
  "Full-Back": [[24, 16], [24, 84]],
  "Defensive Midfield": [[40, 50]],
  "Central Midfield": [[54, 50]],
  "Attacking Midfield": [[68, 50]],
  "Left Winger": [[72, 15]],
  "Right Winger": [[72, 85]],
  Winger: [[72, 15], [72, 85]],
  "Centre-Forward": [[88, 50]],
};

const GREEN = "rgb(var(--accent))";
const YELLOW = "rgb(var(--warning))";
const RED = "rgb(var(--danger))";
const GREY = "rgba(255,255,255,0.20)";
const LINE = "rgba(255,255,255,0.16)";

const VB_W = 320;
const VB_H = 190;
const M = 14;
const FW = VB_W - 2 * M;
const FH = VB_H - 2 * M;
const sx = (x: number) => M + (x / 100) * FW;
const sy = (y: number) => M + (y / 100) * FH;

export function PitchPositions({ data }: { data: PositionPrediction }) {
  const src = data.side_aware?.probs ?? data.probs;
  const entries = Object.entries(src).sort((a, b) => b[1] - a[1]);
  const top = entries[0]?.[1] ?? 1;
  const playable = entries.filter(([, p]) => p >= 0.03 && p >= 0.1 * top).map(([n]) => n);

  const colorFor = (name: string) => {
    const i = playable.indexOf(name);
    return i === 0 ? GREEN : i === 1 ? YELLOW : i >= 2 ? RED : GREY;
  };

  // draw non-playable first (grey, small) so playable dots sit on top
  const names = Object.keys(src).filter((n) => COORDS[n]);
  const ordered = [...names].sort((a, b) => playable.indexOf(a) - playable.indexOf(b));

  const cx = M + FW / 2;
  const cy = M + FH / 2;
  const boxW = FW * 0.13;
  const boxH = FH * 0.5;

  return (
    <div>
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="w-full" role="img" aria-label="Position map">
        {/* pitch */}
        <rect x={M} y={M} width={FW} height={FH} rx="4" fill="rgba(255,255,255,0.015)" stroke={LINE} />
        <line x1={cx} y1={M} x2={cx} y2={M + FH} stroke={LINE} />
        <circle cx={cx} cy={cy} r={FH * 0.16} fill="none" stroke={LINE} />
        <circle cx={cx} cy={cy} r="1.6" fill={LINE} />
        {/* penalty boxes */}
        <rect x={M} y={cy - boxH / 2} width={boxW} height={boxH} fill="none" stroke={LINE} />
        <rect x={M + FW - boxW} y={cy - boxH / 2} width={boxW} height={boxH} fill="none" stroke={LINE} />
        {/* dots */}
        {ordered.flatMap((name) =>
          COORDS[name].map(([x, y], i) => {
            const color = colorFor(name);
            const playing = playable.includes(name);
            return (
              <circle
                key={`${name}-${i}`}
                cx={sx(x)}
                cy={sy(y)}
                r={playing ? 8 : 5.5}
                fill={color}
                stroke={playing ? "rgba(0,0,0,0.35)" : "none"}
                strokeWidth={playing ? 1 : 0}
              >
                <title>{name}</title>
              </circle>
            );
          }),
        )}
      </svg>
      <Legend show={playable.length} />
    </div>
  );
}

function Legend({ show }: { show: number }) {
  const items = [
    { c: GREEN, t: "Primary" },
    { c: YELLOW, t: "Secondary" },
    { c: RED, t: "Other" },
  ].slice(0, Math.max(1, Math.min(3, show)));
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1">
      {items.map((it) => (
        <span key={it.t} className="flex items-center gap-1.5 text-caption text-ink-3">
          <span className="h-2 w-2 rounded-full" style={{ background: it.c }} />
          {it.t}
        </span>
      ))}
    </div>
  );
}
