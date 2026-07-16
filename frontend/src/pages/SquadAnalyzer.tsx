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
        <h1 className="text-2xl font-bold mb-1">Squad Analyzer</h1>
        <p className="text-white/50 text-sm">
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
          className="w-full rounded-lg border border-white/15 bg-surface-800 px-4 py-3 outline-none focus:border-pitch-400"
        />
        {!club && debounced.trim().length >= 2 && (
          <div className="absolute z-20 mt-1 w-full rounded-lg border border-white/10 bg-surface-800 shadow-xl overflow-hidden">
            {search.isFetching && <div className="px-4 py-2 text-white/40 text-sm">Searching…</div>}
            {search.data?.length === 0 && <div className="px-4 py-2 text-white/40 text-sm">No clubs.</div>}
            {search.data?.map((c) => (
              <button
                key={c.id}
                onClick={() => { setClub(c); setQ(""); }}
                className="flex w-full items-center justify-between px-4 py-2 text-left hover:bg-white/5"
              >
                <span>{c.name}</span>
                <span className="text-xs text-white/40">{c.country}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {squad.isLoading && <Loading />}
      {squad.error && <ErrorState error={squad.error} />}
      {squad.data && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-6 text-sm">
            <Stat label="Squad size" value={String(squad.data.squad_size)} />
            <Stat label="Avg age" value={squad.data.avg_age?.toFixed(1) ?? "—"} />
            <Stat label="Squad value" value={money(squad.data.total_value_eur)} />
          </div>

          {squad.data.gaps.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-white/50">Thin positions:</span>
              {squad.data.gaps.map((g) => <Badge key={g} tone="amber">{g}</Badge>)}
            </div>
          )}

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {squad.data.depth.map((d) => (
              <Card key={d.position_group}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{d.position_group}</span>
                  {squad.data!.gaps.includes(d.position_group) && <Badge tone="amber">thin</Badge>}
                </div>
                <div className="mt-3 space-y-1 text-sm text-white/60">
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
      <div className="text-xs uppercase tracking-wide text-white/40">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}
