// Small shared UI primitives: states, cards, badges, score bars.

import type { ReactNode } from "react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-white/50 py-10 justify-center">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-pitch-400" />
      {label}
    </div>
  );
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-red-300 text-sm">
      Couldn’t load this — {msg}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="text-white/40 text-sm py-8 text-center">{children}</div>;
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-white/10 bg-surface-800/60 p-5 ${className}`}>
      {children}
    </div>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-sm font-semibold uppercase tracking-wide text-white/50 mb-3">{children}</h2>;
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "green" | "amber" }) {
  const tones = {
    default: "bg-white/10 text-white/80",
    green: "bg-pitch-500/20 text-pitch-400",
    amber: "bg-amber-500/20 text-amber-300",
  };
  return <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

/** Horizontal 0–100 score bar with a label. */
export function ScoreBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pctWidth = Math.max(0, Math.min(100, (value / max) * 100));
  const color = pctWidth >= 66 ? "bg-pitch-400" : pctWidth >= 40 ? "bg-amber-400" : "bg-red-400";
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-white/70">{label}</span>
        <span className="font-mono text-white/90">{value.toFixed(0)}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pctWidth}%` }} />
      </div>
    </div>
  );
}
