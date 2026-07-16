// Signed model driving-factors: green = pushes up, red = pushes down.

import type { Driver } from "../api/types";

export function DriverList({ drivers }: { drivers: Driver[] }) {
  const max = Math.max(...drivers.map((d) => d.weight), 0.001);
  return (
    <ul className="space-y-2">
      {drivers.map((d) => {
        const up = d.effect !== "decreases";
        return (
          <li key={d.feature} className="flex items-center gap-3">
            <span className="w-40 shrink-0 text-sm text-white/70 capitalize">{d.label}</span>
            <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className={`h-full rounded-full ${up ? "bg-pitch-400" : "bg-red-400"}`}
                style={{ width: `${(d.weight / max) * 100}%` }}
              />
            </div>
            <span className={`text-xs w-16 text-right ${up ? "text-pitch-400" : "text-red-400"}`}>
              {up ? "▲" : "▼"} {d.weight.toFixed(2)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
