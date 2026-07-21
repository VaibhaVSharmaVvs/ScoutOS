// Model driving-factors in scout language (MED-02): "pushes up · strong", not a
// raw "▲ 1.18". Magnitude is a calm near-white bar (MED-01); the exact weight is
// available on hover for power users.

import type { Driver } from "../api/types";
import { driverStrength } from "../lib/format";

export function DriverList({ drivers }: { drivers: Driver[] }) {
  const max = Math.max(...drivers.map((d) => d.weight), 0.001);
  return (
    <ul className="space-y-2.5">
      {drivers.map((d) => {
        const up = d.effect !== "decreases";
        const strength = driverStrength(d.weight);
        return (
          <li key={d.feature} className="flex items-center gap-3" title={`weight ${d.weight.toFixed(2)}`}>
            <span className="w-36 shrink-0 truncate text-sm text-ink-2">{d.label}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full bg-ink-2"
                style={{ width: `${(d.weight / max) * 100}%` }}
              />
            </div>
            <span className="flex w-28 shrink-0 items-center justify-end gap-1 text-caption">
              <span className={up ? "text-accent" : "text-danger"}>{up ? "▲" : "▼"}</span>
              <span className="text-ink-3">
                pushes {up ? "up" : "down"} · {strength}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
