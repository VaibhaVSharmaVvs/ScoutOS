import { useParams } from "react-router-dom";

import { useClubFit } from "../api/hooks";
import { Card, Empty, ErrorState, Loading, ScoreBar } from "../components/ui";

export function ClubFinder() {
  const playerId = Number(useParams().id);
  const { data, isLoading, error } = useClubFit(playerId);

  if (isLoading) return <Loading label="Ranking club fits…" />;
  if (error) return <ErrorState error={error} />;
  if (!data || data.results.length === 0) return <Empty>No club fits available for this player.</Empty>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-white/50">
        Best-fitting clubs for {data.player}, scored on tactical style, squad need, affordability
        and age profile.
      </p>
      <div className="grid md:grid-cols-2 gap-4">
        {data.results.map((c) => (
          <Card key={c.club}>
            <div className="flex items-center justify-between mb-4">
              <span className="font-semibold text-lg">{c.club}</span>
              <span className="text-2xl font-bold text-pitch-400">{c.overall_fit.toFixed(0)}</span>
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
