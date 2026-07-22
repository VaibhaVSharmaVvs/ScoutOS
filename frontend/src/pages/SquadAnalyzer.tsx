import { useState } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { useClubSearch, useSquadAnalysis } from "../api/hooks";
import { Badge, Card, ErrorState, Loading, SectionTitle } from "../components/ui";
import { money } from "../lib/format";
import { useDebounced } from "../lib/useDebounced";
import { useReducedMotion } from "../lib/useReducedMotion";
import type { ClubHit, PositionDepth } from "../api/types";

const SUGGESTIONS = ["Manchester City", "Arsenal", "Real Madrid", "Bayern Munich"];

export function SquadAnalyzer() {
  const [q, setQ] = useState("");
  const [club, setClub] = useState<ClubHit | null>(null);
  const debounced = useDebounced(q, 300);
  const search = useClubSearch(debounced);
  const squad = useSquadAnalysis(club?.id ?? null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h2 font-semibold">Squad Analyzer</h1>
        <p className="mt-1 text-sm text-ink-3">
          Pick a club to see per-position depth, age profile and squad-value, with thin positions
          flagged (current season).
        </p>
      </div>

      <div className="max-w-md">
        <div className="relative">
          <input
            value={club ? club.name : q}
            onChange={(e) => {
              setClub(null);
              setQ(e.target.value);
            }}
            placeholder="Search clubs…"
            className="w-full rounded-md border border-line bg-input px-3 py-2.5 text-sm text-ink placeholder-ink-muted outline-none transition-colors focus:border-accent/60"
          />
          {!club && debounced.trim().length >= 2 && (
            <div className="absolute z-20 mt-1.5 w-full overflow-hidden rounded-md border border-line bg-surface-overlay shadow-2xl shadow-black/40">
              {search.isFetching && <div className="px-4 py-2 text-sm text-ink-muted">Searching…</div>}
              {search.data?.length === 0 && <div className="px-4 py-2 text-sm text-ink-muted">No clubs.</div>}
              {search.data?.map((c) => (
                <button
                  key={c.id}
                  onClick={() => { setClub(c); setQ(""); }}
                  className="flex w-full items-center justify-between px-4 py-2 text-left transition-colors hover:bg-white/[0.05]"
                >
                  <span className="text-sm">{c.name}</span>
                  <span className="text-caption text-ink-3">{c.country}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {/* suggestions sit right under the field, not stranded mid-page (HIGH-04) */}
        {!club && !squad.isLoading && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-caption text-ink-3">Try</span>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setQ(s)}
                className="rounded-sm border border-line bg-white/[0.04] px-2.5 py-1 text-caption text-ink-2 transition-colors hover:border-strong hover:text-ink"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {squad.isLoading && <Loading label="Analyzing squad" />}
      {squad.error && <ErrorState error={squad.error} onRetry={() => squad.refetch()} />}

      {squad.data && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-8">
            <Stat label="Squad size" value={String(squad.data.squad_size)} />
            <Stat label="Avg age" value={squad.data.avg_age?.toFixed(1) ?? "—"} />
            <Stat label="Squad value" value={money(squad.data.total_value_eur)} />
          </div>

          {squad.data.gaps.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-ink-3">Thin positions</span>
              {squad.data.gaps.map((g) => <Badge key={g} tone="warning">{g}</Badge>)}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {squad.data.depth.map((d) => (
              <PositionCard key={d.position_group} d={d} thin={squad.data!.gaps.includes(d.position_group)} />
            ))}
          </div>

          <Card>
            <SectionTitle>Depth vs age</SectionTitle>
            <p className="mb-3 text-caption text-ink-3">
              Each dot is a player — value against age. Clusters on the right flag an ageing group.
            </p>
            <DepthScatter depth={squad.data.depth} />
          </Card>
        </div>
      )}

    </div>
  );
}

function PositionCard({ d, thin }: { d: PositionDepth; thin: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className={d.players.length ? "card-hover" : ""}>
      <button
        className="flex w-full items-center justify-between"
        onClick={() => d.players.length && setOpen((o) => !o)}
        disabled={!d.players.length}
      >
        <span className="font-medium">{d.position_group}</span>
        {thin ? <Badge tone="warning">thin</Badge> : d.players.length > 0 && (
          <span className="text-caption text-ink-3">{open ? "hide" : "roster"}</span>
        )}
      </button>
      <div className="tnum mt-3 space-y-1 text-sm text-ink-3">
        <div>{d.squad_size} players · {d.regulars} regulars</div>
        <div>avg age {d.avg_age?.toFixed(1) ?? "—"}</div>
        <div>{money(d.total_value_eur)}</div>
      </div>
      {open && (
        <ul className="mt-3 space-y-1.5 border-t border-line pt-3 fade-in">
          {d.players.map((p) => (
            <li key={p.player_id} className="flex items-center justify-between gap-2 text-sm">
              <Link to={`/player/${p.player_id}`} className="truncate text-ink-2 hover:text-ink">
                {p.name}
              </Link>
              <span className="tnum shrink-0 text-caption text-ink-3">
                {p.age?.toFixed(0) ?? "—"}y · {money(p.value_eur)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

const POS_COLOR: Record<string, string> = {
  GK: "#8b95a1",
  DEF: "#6aa4ff",
  MID: "#34d399",
  FWD: "#f0a63a",
};

function DepthScatter({ depth }: { depth: PositionDepth[] }) {
  const reduced = useReducedMotion();
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.06)" />
        <XAxis
          type="number" dataKey="age" name="age" domain={[16, 40]}
          tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 12 }}
          axisLine={{ stroke: "rgba(255,255,255,0.08)" }} tickLine={false}
          label={{ value: "age", position: "insideBottom", offset: -2, fill: "rgba(255,255,255,0.5)", fontSize: 11 }}
        />
        <YAxis
          type="number" dataKey="value" name="value"
          tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 12 }}
          tickFormatter={(v) => money(v)} width={56}
          axisLine={false} tickLine={false}
        />
        <ZAxis range={[50, 50]} />
        <Tooltip
          cursor={{ stroke: "rgba(255,255,255,0.13)" }}
          contentStyle={{ background: "#1d282d", border: "1px solid rgba(255,255,255,0.13)", borderRadius: 8, fontSize: 12 }}
          formatter={(v, n) => (n === "value" ? [money(Number(v)), "value"] : [String(v), String(n)])}
          labelFormatter={() => ""}
        />
        {depth.filter((d) => d.players.length).map((d) => (
          <Scatter
            key={d.position_group}
            name={d.position_group}
            data={d.players.map((p) => ({ age: p.age, value: p.value_eur, name: p.name }))}
            fill={POS_COLOR[d.position_group] ?? "#8b95a1"}
            fillOpacity={0.85}
            isAnimationActive={!reduced}
            animationDuration={550}
            animationEasing="ease-out"
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="eyebrow mb-1">{label}</div>
      <div className="tnum text-h3 font-semibold">{value}</div>
    </div>
  );
}
