import { useParams } from "react-router-dom";

import { useClubFit } from "../api/hooks";
import { Card, Empty, ErrorState, Loading, ScoreBar } from "../components/ui";

export function ClubFinder() {
  const playerId = Number(useParams().id);
  const { data, isLoading, error } = useClubFit(playerId);

  if (isLoading) return <Loading label="Ranking club fits" />;
  if (error) return <ErrorState error={error} />;
  if (!data || data.results.length === 0) return <Empty>No club fits available for this player.</Empty>;

  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-3">
        Best-fitting clubs for {data.player}, scored on tactical style, squad need, affordability
        and age profile. Current club excluded.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {data.results.map((c) => (
          <Card key={c.club}>
            <div className="mb-4 flex items-center justify-between">
              <span className="text-h4 font-medium">{c.club}</span>
              <span className="tnum text-h2 font-semibold text-accent">
                {c.overall_fit.toFixed(0)}
              </span>
            </div>
            <div className="space-y-3">
              <ScoreBar label="Tactical" value={c.tactical_fit} />
              <ScoreBar label="Squad need" value={c.squad_fit} />
              <ScoreBar label="Financial" value={c.financial_fit} />
              <ScoreBar label="Age fit" value={c.age_fit} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
