// Signed model driving-factors: accent = pushes up, red = pushes down.

import type { Driver } from "../api/types";

export function DriverList({ drivers }: { drivers: Driver[] }) {
  const max = Math.max(...drivers.map((d) => d.weight), 0.001);
  return (
    <ul className="space-y-2.5">
      {drivers.map((d) => {
        const up = d.effect !== "decreases";
        return (
          <li key={d.feature} className="flex items-center gap-3">
            <span className="w-36 shrink-0 truncate text-sm text-ink-2">{d.label}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className={`h-full rounded-full ${up ? "bg-accent" : "bg-danger"}`}
                style={{ width: `${(d.weight / max) * 100}%` }}
              />
            </div>
            <span
              className={`tnum w-14 text-right text-caption ${up ? "text-accent" : "text-danger"}`}
            >
              {up ? "▲" : "▼"} {d.weight.toFixed(2)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
