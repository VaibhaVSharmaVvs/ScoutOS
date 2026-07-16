import { useParams } from "react-router-dom";

import {
  useExplain,
  useMarketValues,
  usePosition,
  usePotential,
  useRadar,
  useValue,
} from "../api/hooks";
import { DriverList } from "../components/DriverList";
import { StatRadar } from "../components/StatRadar";
import { ValueChart } from "../components/ValueChart";
import { Badge, Card, Empty, ErrorState, Loading, SectionTitle } from "../components/ui";
import { money } from "../lib/format";

export function PlayerOverview() {
  const playerId = Number(useParams().id);
  const radar = useRadar(playerId);
  const value = useValue(playerId);
  const potential = usePotential(playerId);
  const position = usePosition(playerId);
  const mv = useMarketValues(playerId);
  const explain = useExplain(playerId);

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <SectionTitle>Style profile (percentile vs position)</SectionTitle>
          {radar.isLoading && <Loading />}
          {radar.error && <ErrorState error={radar.error} />}
          {radar.data && (
            <>
              <StatRadar metrics={radar.data.metrics} />
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-white/40 mb-1">Strengths</div>
                  <div className="flex flex-wrap gap-1">
                    {radar.data.strengths.length ? (
                      radar.data.strengths.map((s) => <Badge key={s} tone="green">{s}</Badge>)
                    ) : (
                      <span className="text-white/30">—</span>
                    )}
                  </div>
                </div>
                <div>
                  <div className="text-white/40 mb-1">Weaknesses</div>
                  <div className="flex flex-wrap gap-1">
                    {radar.data.weaknesses.length ? (
                      radar.data.weaknesses.map((s) => <Badge key={s} tone="amber">{s}</Badge>)
                    ) : (
                      <span className="text-white/30">—</span>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </Card>

        <Card>
          <SectionTitle>Predicted market value</SectionTitle>
          {value.isLoading && <Loading />}
          {value.error && <ErrorState error={value.error} />}
          {value.data && (
            <>
              <div className="flex items-baseline gap-3 mb-4">
                <span className="text-3xl font-bold text-pitch-400">
                  {money(value.data.predicted_value_eur)}
                </span>
                {value.data.actual_value_eur != null && (
                  <span className="text-sm text-white/40">
                    listed {money(value.data.actual_value_eur)}
                  </span>
                )}
              </div>
              <div className="text-xs uppercase tracking-wide text-white/40 mb-2">Top drivers</div>
              <DriverList drivers={value.data.drivers} />
            </>
          )}
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <SectionTitle>Potential (+3 years)</SectionTitle>
          {potential.isLoading && <Loading />}
          {potential.isError && <Empty>No current market value — growth can’t be projected.</Empty>}
          {potential.data && (
            <>
              <div className="flex items-baseline gap-3 mb-4">
                <span className="text-2xl font-bold text-pitch-400">
                  {money(potential.data.predicted_value_eur)}
                </span>
                <span className="text-sm text-white/40">
                  from {money(potential.data.current_value_eur)}
                </span>
              </div>
              <DriverList drivers={potential.data.drivers} />
            </>
          )}
        </Card>

        <Card>
          <SectionTitle>Position (from playing style)</SectionTitle>
          {position.isLoading && <Loading />}
          {position.error && <ErrorState error={position.error} />}
          {position.data && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge tone="green">Primary: {position.data.primary}</Badge>
                {position.data.secondary && <Badge>2nd: {position.data.secondary}</Badge>}
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-white/40 mb-1">Playable</div>
                <div className="flex flex-wrap gap-1">
                  {position.data.playable.map((p) => <Badge key={p}>{p}</Badge>)}
                </div>
              </div>
              {position.data.side_aware && (
                <div className="text-sm text-white/50">
                  Side-aware ({position.data.side_aware.foot}-footed):{" "}
                  <span className="text-white/80">{position.data.side_aware.primary}</span>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <SectionTitle>Market-value history</SectionTitle>
        {mv.isLoading && <Loading />}
        {mv.data && mv.data.length > 1 ? (
          <ValueChart data={mv.data.map((d) => ({ label: d.as_of.slice(0, 7), value: d.value_eur }))} />
        ) : (
          !mv.isLoading && <Empty>Not enough valuation history to chart.</Empty>
        )}
      </Card>

      <Card>
        <SectionTitle>AI scouting report</SectionTitle>
        {explain.isLoading && <Loading label="Generating report…" />}
        {explain.error && <ErrorState error={explain.error} />}
        {explain.data && (
          <>
            <p className="text-white/80 leading-relaxed whitespace-pre-line">
              {explain.data.narrative}
            </p>
            {explain.data.provider !== "anthropic" && (
              <p className="mt-3 text-xs text-amber-300/80">
                Generated without an LLM (no API key configured) — this echoes the grounded model
                outputs. Set ANTHROPIC_API_KEY on the backend for full narratives.
              </p>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
