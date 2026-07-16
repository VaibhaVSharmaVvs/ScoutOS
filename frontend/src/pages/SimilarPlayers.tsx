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
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-white/50">Style basis:</span>
        {(["current", "career"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded px-3 py-1 text-sm ${
              mode === m ? "bg-pitch-500/30 text-pitch-400" : "bg-white/5 text-white/60 hover:text-white"
            }`}
          >
            {m === "current" ? "Current season" : "Career"}
          </button>
        ))}
      </div>

      {isLoading && <Loading />}
      {error && <ErrorState error={error} />}
      {data && data.results.length === 0 && <Empty>No similar players found.</Empty>}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {data?.results.map((s) => (
          <Link key={s.player_id} to={`/player/${s.player_id}`}>
            <Card className="hover:border-pitch-400/50 transition-colors h-full">
              <div className="flex items-start justify-between">
                <div className="font-semibold">{s.player}</div>
                <span className="text-pitch-400 font-mono text-sm">{pct(s.similarity)}</span>
              </div>
              <div className="text-xs text-white/40 mt-1">
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
