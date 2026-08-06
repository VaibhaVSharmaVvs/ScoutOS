import { motion } from "motion/react";
import { useRef } from "react";
import { Link } from "react-router-dom";

import { usePlayerSearch } from "../api/hooks";
import type { PlayerHit } from "../api/types";
import { SearchBar } from "../components/SearchBar";
import { Avatar, Monogram, Skeleton } from "../components/ui";
import { age, money } from "../lib/format";
import { useReducedMotion } from "../lib/useReducedMotion";

const FEATURED = [
  "Erling Haaland",
  "Jude Bellingham",
  "Vinicius Junior",
  "Rodri",
  "Florian Wirtz",
  "Lautaro Martinez",
];

const HERO_SEARCH_ID = "hero-search";

export function Home() {
  const reduced = useReducedMotion();
  const stagger = reduced
    ? {}
    : { initial: "hidden" as const, animate: "show" as const, variants: container };

  return (
    // One screen, no page scroll: hero flexes to fill, the two rails sit compact
    // at the bottom. Anything that can't fit on a very short viewport is clipped.
    <div className="flex h-full flex-col overflow-hidden">
      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section className="relative isolate flex min-h-0 flex-1 items-center justify-center overflow-hidden border-b border-line">
        <HeroBackdrop />
        <motion.div
          {...stagger}
          className="relative flex max-w-3xl flex-col items-center px-5 py-6 text-center"
        >
          <Rise reduced={reduced}>
            <span className="eyebrow inline-flex items-center gap-2 text-accent">
              <TargetGlyph />
              AI-powered scouting platform
            </span>
          </Rise>
          <Rise reduced={reduced}>
            <h1
              className="mt-4 font-semibold"
              style={{ fontSize: "clamp(32px, 5.5vw, 60px)", lineHeight: 1.03, letterSpacing: "-0.035em" }}
            >
              Scout <span className="text-accent">smarter.</span>
              <br />
              Build better teams.
            </h1>
          </Rise>
          <Rise reduced={reduced}>
            <p className="mx-auto mt-4 max-w-xl text-sm text-ink-2 sm:text-base">
              AI-powered scouting across Europe’s top five leagues — market value, potential, playing
              style, position, and club fit, each explained by the model’s own drivers.
            </p>
          </Rise>
          <Rise reduced={reduced} className="mt-6 flex w-full justify-center">
            <SearchBar variant="hero" id={HERO_SEARCH_ID} />
          </Rise>
        </motion.div>
      </section>

      {/* ── FEATURED ─────────────────────────────────────────────────────── */}
      <section className="w-full shrink-0">
        <div className="mx-auto max-w-6xl px-5 pt-5">
          <FeaturedRail reduced={reduced} />
        </div>
      </section>

      {/* ── WHAT YOU GET ─────────────────────────────────────────────────── */}
      <section className="w-full shrink-0">
        <div className="mx-auto max-w-6xl px-5 py-5">
          <h2 className="eyebrow mb-3 flex items-center gap-2">
            <span className="h-px w-6 bg-[var(--line-strong)]" />
            What you get on every player
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {CAPABILITIES.map((c, i) => (
              <FeatureCard key={c.title} {...c} reduced={reduced} index={i} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

/* ── motion helpers ──────────────────────────────────────────────────────── */
const EASE: [number, number, number, number] = [0.23, 1, 0.32, 1];
const container = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.04 } } };
const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
};

function Rise({
  children,
  reduced,
  className,
}: {
  children: React.ReactNode;
  reduced: boolean;
  className?: string;
}) {
  return (
    <motion.div variants={reduced ? undefined : item} className={className}>
      {children}
    </motion.div>
  );
}

/* ── hero backdrop: floodlit, no photo needed ────────────────────────────── */
function HeroBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
      {/* fine grid, fading upward like a pitch receding under the lights */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px)",
          backgroundSize: "46px 46px",
          maskImage: "radial-gradient(120% 90% at 50% 0%, #000 30%, transparent 78%)",
          WebkitMaskImage: "radial-gradient(120% 90% at 50% 0%, #000 30%, transparent 78%)",
        }}
      />
      {/* green floodlight glow, top-left */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(52% 60% at 14% 6%, rgba(52,211,153,0.16), transparent 60%)" }}
      />
      {/* cool light spill, top-right */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(48% 60% at 88% 0%, rgba(150,200,255,0.08), transparent 55%)" }}
      />
      {/* soft floodlight cone from top-centre */}
      <div
        className="absolute inset-x-0 top-0 h-[70%]"
        style={{ background: "radial-gradient(60% 100% at 50% -10%, rgba(255,255,255,0.05), transparent 70%)" }}
      />
      {/* base + bottom vignette for depth */}
      <div
        className="absolute inset-0"
        style={{ background: "linear-gradient(180deg, transparent 55%, var(--canvas) 100%)" }}
      />
    </div>
  );
}

function focusHeroSearch() {
  window.scrollTo({ top: 0, behavior: "smooth" });
  document.getElementById(HERO_SEARCH_ID)?.focus({ preventScroll: true });
}

/* ── featured players carousel ───────────────────────────────────────────── */
function FeaturedRail({ reduced }: { reduced: boolean }) {
  const rail = useRef<HTMLDivElement>(null);
  const nudge = (dir: 1 | -1) =>
    rail.current?.scrollBy({ left: dir * 260 * 2, behavior: "smooth" });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="eyebrow flex items-center gap-2">
          <span className="h-px w-6 bg-[var(--line-strong)]" />
          Featured players
        </h2>
        <button
          onClick={focusHeroSearch}
          className="group inline-flex items-center gap-1 text-caption text-ink-3 transition-colors hover:text-accent"
        >
          Find any player
          <span className="transition-transform group-hover:translate-x-0.5">→</span>
        </button>
      </div>

      <div className="relative">
        <RailArrow dir={-1} onClick={() => nudge(-1)} />
        <div
          ref={rail}
          className="flex gap-3.5 overflow-x-auto scroll-smooth pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {FEATURED.map((name, i) => (
            <FeaturedCard key={name} name={name} index={i} reduced={reduced} />
          ))}
        </div>
        <RailArrow dir={1} onClick={() => nudge(1)} />
      </div>
    </div>
  );
}

function RailArrow({ dir, onClick }: { dir: 1 | -1; onClick: () => void }) {
  return (
    <button
      aria-label={dir === 1 ? "Scroll right" : "Scroll left"}
      onClick={onClick}
      className={`absolute top-1/2 z-10 hidden -translate-y-1/2 place-items-center rounded-full border border-strong bg-surface-overlay text-ink-2 backdrop-blur transition-colors hover:border-accent/50 hover:text-accent sm:grid ${
        dir === 1 ? "-right-3" : "-left-3"
      }`}
      style={{ height: 34, width: 34 }}
    >
      {dir === 1 ? "›" : "‹"}
    </button>
  );
}

function FeaturedCard({ name, index, reduced }: { name: string; index: number; reduced: boolean }) {
  const { data } = usePlayerSearch(name);
  const hit: PlayerHit | undefined = data?.find((p) => p.full_name === name) ?? data?.[0];
  const a = age(hit?.birth_year);

  const body = (
    <div className="group flex h-[112px] w-[236px] shrink-0 gap-3 rounded-lg border border-line bg-surface p-3 transition-all duration-200 hover:-translate-y-0.5 hover:border-strong hover:shadow-[0_10px_30px_-14px_rgba(0,0,0,0.7)]">
      {hit ? (
        <Avatar src={hit.image_url} name={name} h={88} />
      ) : (
        <Skeleton className="h-[88px] w-[68px] rounded-md" />
      )}
      <div className="flex min-w-0 flex-1 flex-col justify-between py-0.5">
        <div className="min-w-0">
          <div className="truncate font-semibold leading-tight text-ink">{name}</div>
          <div className="mt-1 truncate text-caption text-ink-3">
            {hit?.primary_position ?? "—"}
          </div>
          <div className="truncate text-caption text-ink-3">{hit?.nationality ?? " "}</div>
        </div>
        <div>
          <div className="tnum text-h4 font-semibold text-accent">{money(hit?.market_value_eur)}</div>
          {a != null && <div className="tnum text-caption text-ink-3">age {a}</div>}
        </div>
      </div>
    </div>
  );

  const card = hit ? (
    <Link to={`/player/${hit.id}`} className="block">
      {body}
    </Link>
  ) : (
    body
  );

  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: reduced ? 0 : 0.05 * index, ease: EASE }}
    >
      {card}
    </motion.div>
  );
}

/* ── "what you get" feature cards, each with a mini-visual ────────────────── */
const CAPABILITIES = [
  {
    title: "Value & potential",
    body: "A model estimate with the drivers behind it, and a three-year projection.",
    icon: <TrendGlyph />,
    visual: <Sparkline />,
  },
  {
    title: "Style & position",
    body: "A position-appropriate percentile profile and the roles the player fits.",
    icon: <TargetGlyph />,
    visual: <MiniRadar />,
  },
  {
    title: "Similar players & club fit",
    body: "Stylistic matches and the clubs where a move makes sense.",
    icon: <PeopleGlyph />,
    visual: <ClubBadges />,
  },
] as const;

function FeatureCard({
  title,
  body,
  icon,
  visual,
  index,
  reduced,
}: (typeof CAPABILITIES)[number] & { index: number; reduced: boolean }) {
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: reduced ? 0 : 0.5 + 0.06 * index, ease: EASE }}
      className="flex items-center justify-between gap-4 rounded-lg border border-line bg-surface p-4"
    >
      <div className="min-w-0">
        <span className="mb-2.5 inline-grid h-8 w-8 place-items-center rounded-md border border-accent/25 bg-accent-soft text-accent">
          {icon}
        </span>
        <div className="font-medium text-ink">{title}</div>
        <p className="mt-1 text-sm text-ink-3">{body}</p>
      </div>
      <div className="shrink-0">{visual}</div>
    </motion.div>
  );
}

/* ── mini-visuals ─────────────────────────────────────────────────────────── */
function Sparkline() {
  const ys = [30, 26, 31, 20, 24, 13, 17, 8, 6];
  const w = 104;
  const h = 48;
  const stepX = w / (ys.length - 1);
  const pts = ys.map((y, i) => [i * stepX, y] as const);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"} ${x.toFixed(1)} ${y}`).join(" ");
  const area = `${line} L ${w} ${h} L 0 ${h} Z`;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden>
      <defs>
        <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgb(var(--accent))" stopOpacity="0.28" />
          <stop offset="100%" stopColor="rgb(var(--accent))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#spark)" />
      <path d={line} fill="none" stroke="rgb(var(--accent))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={w} cy={ys[ys.length - 1]} r="2.6" fill="rgb(var(--accent))" />
    </svg>
  );
}

function MiniRadar() {
  const cx = 48;
  const cy = 48;
  const r = 32;
  const labels = ["ATT", "TEC", "TAC", "DEF", "PHY"];
  const fills = [0.98, 0.66, 0.58, 0.5, 0.78]; // an attacker-ish profile
  const angle = (i: number) => (-90 + i * 72) * (Math.PI / 180);
  const pt = (i: number, rad: number) => [cx + rad * Math.cos(angle(i)), cy + rad * Math.sin(angle(i))] as const;
  const ring = labels.map((_, i) => pt(i, r).join(",")).join(" ");
  const shape = fills.map((f, i) => pt(i, r * f).join(",")).join(" ");
  return (
    <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden>
      <polygon points={ring} fill="none" stroke="var(--line-strong)" strokeWidth="1" />
      <polygon points={labels.map((_, i) => pt(i, r * 0.5).join(",")).join(" ")} fill="none" stroke="var(--line)" strokeWidth="1" />
      <polygon points={shape} fill="rgb(var(--accent) / 0.22)" stroke="rgb(var(--accent))" strokeWidth="1.5" />
      {labels.map((l, i) => {
        const [x, y] = pt(i, r + 8);
        return (
          <text key={l} x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize="7" fill="var(--ink-3)">
            {l}
          </text>
        );
      })}
    </svg>
  );
}

function ClubBadges() {
  const clubs = ["MCI", "BAR", "RMA", "BAY", "JUV"];
  return (
    <div className="flex items-center">
      {clubs.map((c, i) => (
        <span key={c} className={i ? "-ml-2" : ""} style={{ zIndex: clubs.length - i }}>
          <Monogram name={c} size={30} shape="circle" />
        </span>
      ))}
    </div>
  );
}

/* ── glyphs ──────────────────────────────────────────────────────────────── */
function TargetGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M12 1v3M12 20v3M1 12h3M20 12h3" strokeLinecap="round" />
    </svg>
  );
}

function TrendGlyph() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 17l6-6 4 4 8-8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M17 7h4v4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PeopleGlyph() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" strokeLinecap="round" />
      <path d="M16 6.5a3 3 0 0 1 0 5.5M17.5 19c0-2-.8-3.6-2-4.6" strokeLinecap="round" />
    </svg>
  );
}
