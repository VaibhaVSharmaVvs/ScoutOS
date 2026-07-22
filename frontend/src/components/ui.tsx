// Shared primitives for the floodlit terminal: quiet surfaces, chalk-line
// structure, one accent, tabular data. States are first-class.

import { useState, type ReactNode } from "react";

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-12 text-ink-3 text-sm">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/10 border-t-accent" />
      {label}
    </div>
  );
}

/** Skeleton block — shimmer shaped like the content it stands in for (HIGH-02). */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-white/[0.06] ${className}`} />;
}

export function SkeletonLines({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2.5">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-1.5 flex-1" />
        </div>
      ))}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="rounded-md border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
      <div>Couldn’t load this — {msg}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded-sm border border-danger/40 px-2.5 py-1 text-caption text-danger transition-colors hover:bg-danger/10"
        >
          Try again
        </button>
      )}
    </div>
  );
}

/** Small inline empty note — for a card body, not a whole page. */
export function Empty({ children }: { children: ReactNode }) {
  return <div className="py-8 text-center text-sm text-ink-3">{children}</div>;
}

/** Full empty state: pitch-marking glyph, headline, sub-line, optional action. */
export function EmptyState({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 py-14 text-center">
      <PitchGlyph />
      <div className="text-h4 font-medium text-ink">{title}</div>
      {hint && <div className="max-w-sm text-sm text-ink-3">{hint}</div>}
      {children && <div className="mt-1 flex flex-wrap justify-center gap-2">{children}</div>}
    </div>
  );
}

function PitchGlyph() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" className="text-ink-muted">
      <rect x="2.5" y="6.5" width="35" height="27" rx="2" stroke="currentColor" strokeWidth="1.2" />
      <line x1="20" y1="6.5" x2="20" y2="33.5" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="20" cy="20" r="5" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
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

/** Preferred-foot icon: two feet, the strong foot(s) in accent, the other dim.
 *  left/right -> one green foot; both -> both green. Renders nothing if unknown. */
export function Feet({ foot }: { foot: string | null | undefined }) {
  const f = (foot ?? "").toLowerCase();
  if (!["left", "right", "both"].includes(f)) return null;
  const leftOn = f === "left" || f === "both";
  const rightOn = f === "right" || f === "both";
  const label = f === "both" ? "Two-footed" : `${f[0].toUpperCase()}${f.slice(1)}-footed`;
  const on = "rgb(var(--accent))";
  const off = "rgba(255,255,255,0.20)";
  return (
    <span className="inline-flex items-center gap-0.5" title={label} aria-label={label}>
      <Foot fill={leftOn ? on : off} mirror />
      <Foot fill={rightOn ? on : off} />
    </span>
  );
}

function Foot({ fill, mirror = false }: { fill: string; mirror?: boolean }) {
  return (
    <svg
      width="13" height="16" viewBox="0 0 24 30" fill={fill}
      style={mirror ? { transform: "scaleX(-1)" } : undefined}
    >
      {/* sole (ball down to heel) */}
      <path d="M12 9c-3.7 0-5.9 3.4-5.9 8.4 0 5 2.2 10.6 5.9 10.6s5.9-5.6 5.9-10.6C17.9 12.4 15.7 9 12 9z" />
      {/* toes arced across the top — big toe inner (left on a right foot) */}
      <circle cx="7.4" cy="6.4" r="2.1" />
      <circle cx="11.6" cy="4.5" r="1.8" />
      <circle cx="15.4" cy="4.7" r="1.6" />
      <circle cx="18.6" cy="6.3" r="1.4" />
    </svg>
  );
}

/** Player photo when we have one, else a monogram fallback (and on load error).
 *  `shape` circle for list icons, rounded for the larger profile portrait. */
export function Avatar({
  src,
  name,
  size = 36,
  shape = "circle",
}: {
  src?: string | null;
  name: string;
  size?: number;
  shape?: "circle" | "rounded";
}) {
  const [failed, setFailed] = useState(false);
  const radius = shape === "circle" ? "9999px" : "var(--radius-md)";
  if (!src || failed) return <Monogram name={name} size={size} shape={shape} />;
  return (
    <img
      src={src}
      alt={name}
      loading="lazy"
      onError={() => setFailed(true)}
      className="shrink-0 object-cover object-top"
      style={{
        height: size,
        width: size,
        borderRadius: radius,
        border: "1px solid var(--line-strong)",
        background: "var(--surface-2)",
      }}
    />
  );
}

/** Deterministic monogram avatar from a name — a stand-in crest (MED-03). */
export function Monogram({
  name,
  size = 36,
  shape = "circle",
}: {
  name: string;
  size?: number;
  shape?: "circle" | "rounded";
}) {
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
  const hue = [...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);
  return (
    <span
      className="grid shrink-0 place-items-center font-semibold text-ink"
      style={{
        height: size,
        width: size,
        fontSize: size * 0.36,
        background: `hsl(${hue} 24% 22%)`,
        border: "1px solid var(--line-strong)",
        borderRadius: shape === "circle" ? "9999px" : "var(--radius-md)",
      }}
    >
      {initials}
    </span>
  );
}

const LEVELS = [
  { min: 66, word: "strong", cls: "bg-accent text-accent" },
  { min: 40, word: "fair", cls: "bg-warning text-warning" },
  { min: 0, word: "weak", cls: "bg-danger text-danger" },
] as const;

export function scoreLevel(value: number, max = 100) {
  const pct = (value / max) * 100;
  return LEVELS.find((l) => pct >= l.min) ?? LEVELS[LEVELS.length - 1];
}

/** 0–100 score meter — colour AND a word, so quality isn't colour-only (HIGH-06). */
export function ScoreBar({ label, value, max = 100 }: { label: string; value: number; max?: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const level = scoreLevel(value, max);
  const [bar, text] = level.cls.split(" ");
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-sm text-ink-2">{label}</span>
        <span className="flex items-baseline gap-1.5">
          <span className={`text-caption ${text}`}>{level.word}</span>
          <span className="tnum text-sm font-medium text-ink">{value.toFixed(0)}</span>
        </span>
      </div>
      <div className="relative h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
        {/* threshold tick at the strong/fair boundary (66) as a second cue */}
        <span className="absolute inset-y-0 left-[66%] w-px bg-white/20" />
        <div
          className={`h-full rounded-full ${bar} transition-[width] duration-500 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
