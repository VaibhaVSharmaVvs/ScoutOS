import { useState } from "react";

import { useClubSearch, useSquadAnalysis } from "../api/hooks";
import { Badge, Card, Empty, ErrorState, Loading } from "../components/ui";
import { money } from "../lib/format";
import { useDebounced } from "../lib/useDebounced";
import type { ClubHit } from "../api/types";

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

      <div className="relative max-w-md">
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

      {squad.isLoading && <Loading />}
      {squad.error && <ErrorState error={squad.error} />}
      {squad.data && (
        <div className="space-y-5">
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
              <Card key={d.position_group}>
                <div className="flex items-center justify-between">
                  <span className="font-medium">{d.position_group}</span>
                  {squad.data!.gaps.includes(d.position_group) && <Badge tone="warning">thin</Badge>}
                </div>
                <div className="tnum mt-3 space-y-1 text-sm text-ink-3">
                  <div>{d.squad_size} players · {d.regulars} regulars</div>
                  <div>avg age {d.avg_age?.toFixed(1) ?? "—"}</div>
                  <div>{money(d.total_value_eur)}</div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {!club && !squad.isLoading && <Empty>Search and select a club to analyze.</Empty>}
    </div>
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
