import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useSimilar } from "../api/hooks";
import { Badge, Card, Empty, ErrorState, Loading } from "../components/ui";
import { pct } from "../lib/format";

export function SimilarPlayers() {
  const playerId = Number(useParams().id);
  const [mode, setMode] = useState<"current" | "career">("current");
  const { data, isLoading, error } = useSimilar(playerId, mode);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-1 text-sm">
        <span className="mr-1 text-ink-3">Style basis</span>
        {(["current", "career"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-sm px-3 py-1 transition-colors ${
              mode === m ? "bg-accent-soft text-accent" : "text-ink-3 hover:text-ink"
            }`}
          >
            {m === "current" ? "Current season" : "Career"}
          </button>
        ))}
      </div>

      {isLoading && <Loading />}
      {error && <ErrorState error={error} />}
      {data && data.results.length === 0 && <Empty>No similar players found.</Empty>}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data?.results.map((s) => (
          <Link key={s.player_id} to={`/player/${s.player_id}`}>
            <Card className="h-full transition-colors hover:border-strong">
              <div className="flex items-start justify-between gap-2">
                <div className="font-medium">{s.player}</div>
                <span className="tnum text-sm font-semibold text-accent">{pct(s.similarity)}</span>
              </div>
              <div className="mt-1 text-caption text-ink-3">
                {s.position_group ?? "—"}
                {s.season ? ` · ${s.season}` : ""}
              </div>
              {s.shared_traits && s.shared_traits.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {s.shared_traits.slice(0, 4).map((t) => (
                    <Badge key={t.feature}>{t.label}</Badge>
                  ))}
                </div>
              )}
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
