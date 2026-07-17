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
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>
            {radar.data ? `${radar.data.focus} profile · percentile vs position` : "Style profile"}
          </SectionTitle>
          {radar.isLoading && <Loading />}
          {radar.error && <ErrorState error={radar.error} />}
          {radar.data && (
            <>
              <StatRadar metrics={radar.data.metrics} />
              {radar.data.note && (
                <p className="mt-2 text-caption text-warning/80">{radar.data.note}</p>
              )}
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="eyebrow mb-1.5">Strengths</div>
                  <div className="flex flex-wrap gap-1">
                    {radar.data.strengths.length ? (
                      radar.data.strengths.map((s) => <Badge key={s} tone="accent">{s}</Badge>)
                    ) : (
                      <span className="text-ink-muted">—</span>
                    )}
                  </div>
                </div>
                <div>
                  <div className="eyebrow mb-1.5">Weaknesses</div>
                  <div className="flex flex-wrap gap-1">
                    {radar.data.weaknesses.length ? (
                      radar.data.weaknesses.map((s) => <Badge key={s} tone="warning">{s}</Badge>)
                    ) : (
                      <span className="text-ink-muted">—</span>
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
              <div className="mb-5 flex items-baseline gap-3">
                <span className="tnum text-h1 font-semibold text-ink">
                  {money(value.data.predicted_value_eur)}
                </span>
                {value.data.actual_value_eur != null && (
                  <span className="tnum text-sm text-ink-3">
                    listed {money(value.data.actual_value_eur)}
                  </span>
                )}
              </div>
              <div className="eyebrow mb-2.5">Top drivers</div>
              <DriverList drivers={value.data.drivers} />
            </>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Potential · +3 years</SectionTitle>
          {potential.isLoading && <Loading />}
          {potential.isError && <Empty>No current market value — growth can’t be projected.</Empty>}
          {potential.data && (
            <>
              <div className="mb-5 flex items-baseline gap-3">
                <span className="tnum text-h1 font-semibold text-ink">
                  {money(potential.data.predicted_value_eur)}
                </span>
                <span className="tnum text-sm text-ink-3">
                  from {money(potential.data.current_value_eur)}
                </span>
              </div>
              <DriverList drivers={potential.data.drivers} />
            </>
          )}
        </Card>

        <Card>
          <SectionTitle>Position · from playing style</SectionTitle>
          {position.isLoading && <Loading />}
          {position.error && <ErrorState error={position.error} />}
          {position.data && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge tone="accent">Primary · {position.data.primary}</Badge>
                {position.data.secondary && <Badge>2nd · {position.data.secondary}</Badge>}
              </div>
              <div>
                <div className="eyebrow mb-1.5">Playable</div>
                <div className="flex flex-wrap gap-1">
                  {position.data.playable.map((p) => <Badge key={p}>{p}</Badge>)}
                </div>
              </div>
              {position.data.side_aware && (
                <div className="text-sm text-ink-3">
                  Side-aware ({position.data.side_aware.foot}-footed):{" "}
                  <span className="text-ink">{position.data.side_aware.primary}</span>
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
        {explain.isLoading && <Loading label="Generating report" />}
        {explain.error && <ErrorState error={explain.error} />}
        {explain.data && (
          <>
            <p className="whitespace-pre-line leading-relaxed text-ink-2">
              {explain.data.narrative}
            </p>
            {explain.data.provider !== "anthropic" && (
              <p className="mt-3 text-caption text-warning/70">
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
