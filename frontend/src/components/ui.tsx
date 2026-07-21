// Shared primitives for the floodlit terminal: quiet surfaces, chalk-line
// structure, one accent, tabular data. States are first-class.

import type { ReactNode } from "react";

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-12 text-ink-3 text-sm">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/10 border-t-accent" />
      {label}
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
      Couldn’t load this — {msg}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-10 text-center text-sm text-ink-muted">{children}</div>;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-md border border-line bg-surface p-5 ${className}`}>{children}</div>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 className="eyebrow mb-3">{children}</h2>;
}

export function Badge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "accent" | "warning";
}) {
  const tones = {
    default: "bg-white/[0.06] text-ink-2 border-line",
    accent: "bg-accent-soft text-accent border-accent/20",
    warning: "bg-warning/10 text-warning border-warning/20",
  };
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-caption font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

/** 0–100 score meter. Accent when strong, amber mid, red weak. */
export function ScoreBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const color = pct >= 66 ? "bg-accent" : pct >= 40 ? "bg-warning" : "bg-danger";
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-sm text-ink-2">{label}</span>
        <span className="tnum text-sm font-medium text-ink">{value.toFixed(0)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className={`h-full rounded-full ${color} transition-[width] duration-500 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
