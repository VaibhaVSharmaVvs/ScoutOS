import { useParams } from "react-router-dom";

import { useClubFit } from "../api/hooks";
import { Card, EmptyState, ErrorState, Loading, ScoreBar, scoreLevel } from "../components/ui";

export function ClubFinder() {
  const playerId = Number(useParams().id);
  const { data, isLoading, error, refetch } = useClubFit(playerId);

  if (isLoading) return <Loading label="Ranking club fits" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.results.length === 0)
    return <EmptyState title="No club fits available" hint="This player has no current-season profile to match against." />;

  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-3">
        Best-fitting clubs for {data.player}, scored on tactical style, squad need, affordability
        and age profile. Current club excluded.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {data.results.map((c, i) => {
          const level = scoreLevel(c.overall_fit);
          const [, scoreColor] = level.cls.split(" ");
          return (
            <div key={c.club} className="rise" style={{ animationDelay: `${i * 40}ms` }}>
              <Card className="card-hover">
                <div className="mb-4 flex items-baseline justify-between">
                  <span className="text-h4 font-medium">{c.club}</span>
                  <span className="flex items-baseline gap-2">
                    <span className={`text-caption ${scoreColor}`}>{level.word} fit</span>
                    <span className={`tnum text-h2 font-semibold ${scoreColor}`}>
                      {c.overall_fit.toFixed(0)}
                    </span>
                  </span>
                </div>
                <div className="space-y-3">
                  <ScoreBar label="Tactical" value={c.tactical_fit} />
                  <ScoreBar label="Squad need" value={c.squad_fit} />
                  <ScoreBar label="Financial" value={c.financial_fit} />
                  <ScoreBar label="Age fit" value={c.age_fit} />
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
}
