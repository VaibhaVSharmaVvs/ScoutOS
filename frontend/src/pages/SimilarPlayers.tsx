import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useSimilar } from "../api/hooks";
import { Avatar, Badge, Card, EmptyState, ErrorState, Loading } from "../components/ui";
import { age, money, pct } from "../lib/format";

export function SimilarPlayers() {
  const playerId = Number(useParams().id);
  const [mode, setMode] = useState<"current" | "career">("current");
  const { data, isLoading, error, refetch } = useSimilar(playerId, mode);

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
      {error && <ErrorState error={error} onRetry={() => refetch()} />}
      {data && data.results.length === 0 && (
        <EmptyState title="No close stylistic matches" hint="Try the career basis, or a player with more minutes." />
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data?.results.map((s, i) => {
          const a = age(s.birth_year);
          return (
            <div key={s.player_id} className="rise" style={{ animationDelay: `${i * 40}ms` }}>
              <Link to={`/player/${s.player_id}`}>
                <Card className="card-hover group h-full">
                  <div className="flex items-center gap-3">
                    <Avatar src={s.image_url} name={s.player} size={32} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">{s.player}</div>
                      <div className="tnum mt-0.5 truncate text-caption text-ink-3">
                        {s.position_group ?? "—"}
                        {a ? ` · age ${a}` : ""} · {money(s.market_value_eur)}
                      </div>
                    </div>
                    <span className="tnum text-sm font-semibold text-ink">{pct(s.similarity)}</span>
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
            </div>
          );
        })}
      </div>
    </div>
  );
}
