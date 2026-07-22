import { useParams } from "react-router-dom";

import {
  useExplain,
  useMarketValues,
  usePlayer,
  usePosition,
  usePotential,
  useRadar,
  useValue,
} from "../api/hooks";
import { DriverList } from "../components/DriverList";
import { StatRadar } from "../components/StatRadar";
import { ValueChart } from "../components/ValueChart";
import {
  Badge,
  Card,
  Empty,
  ErrorState,
  Skeleton,
  SkeletonLines,
  SectionTitle,
} from "../components/ui";
import { money } from "../lib/format";
import type { PositionPrediction } from "../api/types";

export function PlayerOverview() {
  const playerId = Number(useParams().id);
  const radar = useRadar(playerId);
  const value = useValue(playerId);
  const potential = usePotential(playerId);
  const position = usePosition(playerId);
  const mv = useMarketValues(playerId);
  const explain = useExplain(playerId);
  const player = usePlayer(playerId); // reuse cached profile for the header's TM value

  const est = value.data;
  // reconcile against the SAME Transfermarkt figure the header shows (CRIT-03),
  // not the model's training-season snapshot.
  const tmValue = player.data?.market_value_eur ?? est?.actual_value_eur ?? null;
  const deltaPct =
    tmValue != null && tmValue > 0 && est
      ? Math.round(((est.predicted_value_eur - tmValue) / tmValue) * 100)
      : null;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>
            {radar.data ? `${radar.data.focus} profile · percentile vs position` : "Style profile"}
          </SectionTitle>
          {radar.isLoading && <Skeleton className="h-[300px] w-full rounded-md" />}
          {radar.error && <ErrorState error={radar.error} onRetry={() => radar.refetch()} />}
          {radar.data && (
            <>
              <StatRadar metrics={radar.data.metrics} />
              {radar.data.note && (
                <p className="mt-2 text-caption text-warning/90">{radar.data.note}</p>
              )}
              <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="eyebrow mb-1.5">Strengths</div>
                  <div className="flex flex-wrap gap-1">
                    {radar.data.strengths.length ? (
                      radar.data.strengths.map((s) => <Badge key={s} tone="accent">{s}</Badge>)
                    ) : (
                      <span className="text-ink-3">—</span>
                    )}
                  </div>
                </div>
                <div>
                  <div className="eyebrow mb-1.5">Weaknesses</div>
                  <div className="flex flex-wrap gap-1">
                    {radar.data.weaknesses.length ? (
                      radar.data.weaknesses.map((s) => <Badge key={s} tone="warning">{s}</Badge>)
                    ) : (
                      <span className="text-ink-3">—</span>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </Card>

        <Card>
          <SectionTitle>ScoutOS estimate</SectionTitle>
          {value.isLoading && (
            <>
              <Skeleton className="mb-5 h-8 w-40" />
              <SkeletonLines rows={5} />
            </>
          )}
          {value.error && <ErrorState error={value.error} onRetry={() => value.refetch()} />}
          {est && (
            <>
              <div className="mb-1 flex items-baseline gap-3">
                <span className="tnum text-h1 font-semibold text-ink">
                  {money(est.predicted_value_eur)}
                </span>
              </div>
              {/* reconcile against the header's Transfermarkt value (CRIT-03) */}
              {deltaPct != null && (
                <p className="mb-4 text-sm text-ink-3">
                  {Math.abs(deltaPct)}% {deltaPct < 0 ? "below" : "above"} the{" "}
                  {money(tmValue)} Transfermarkt value
                  {est.drivers[0] && <> · biggest factor: {est.drivers[0].label}</>}
                </p>
              )}
              <div className="eyebrow mb-2.5">Top drivers</div>
              <DriverList drivers={est.drivers} />
            </>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionTitle>Potential · +3 years</SectionTitle>
          {potential.isLoading && (
            <>
              <Skeleton className="mb-5 h-7 w-36" />
              <SkeletonLines rows={4} />
            </>
          )}
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
          {position.isLoading && <SkeletonLines rows={4} />}
          {position.error && <ErrorState error={position.error} onRetry={() => position.refetch()} />}
          {position.data && <PositionFit data={position.data} />}
        </Card>
      </div>

      <Card>
        <SectionTitle>Market-value history</SectionTitle>
        {mv.isLoading && <Skeleton className="h-[240px] w-full rounded-md" />}
        {mv.data && mv.data.length > 1 ? (
          <ValueChart data={mv.data.map((d) => ({ label: d.as_of.slice(0, 7), value: d.value_eur }))} />
        ) : (
          !mv.isLoading && <Empty>Not enough valuation history to chart.</Empty>
        )}
      </Card>

      <ScoutingReport
        provider={explain.data?.provider}
        narrative={explain.data?.narrative}
        loading={explain.isLoading}
        value={est}
        potential={potential.data}
        position={position.data}
      />
    </div>
  );
}

/** Ranked "role fit" from the model's per-position probabilities. Uses the
 *  granular side-aware positions when foot is known, and shows only positions
 *  the player is somewhat playable in (noise filtered relative to the top). */
function PositionFit({ data }: { data: PositionPrediction }) {
  const src = data.side_aware?.probs ?? data.probs;
  const entries = Object.entries(src).sort((a, b) => b[1] - a[1]);
  const top = entries[0]?.[1] ?? 1;
  const ranked = entries
    .filter(([, p]) => p >= 0.03 && p >= 0.1 * top)
    .slice(0, 6)
    .map(([name, p]) => ({ name, fit: Math.round(p * 100) }));

  if (ranked.length === 0) return <div className="text-sm text-ink-3">No clear role from style.</div>;

  return (
    <>
      <ol className="space-y-3">
        {ranked.map((r, i) => (
          <li key={r.name} className="flex items-center gap-3">
            <span className="tnum w-5 shrink-0 text-caption text-ink-3">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="w-28 shrink-0 text-sm text-ink">{r.name}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
              <div className="h-full rounded-full bg-accent" style={{ width: `${r.fit}%` }} />
            </div>
            <span className="tnum w-8 shrink-0 text-right text-sm font-medium text-ink">{r.fit}</span>
          </li>
        ))}
      </ol>
      {data.side_aware && (
        <p className="mt-3 text-caption text-ink-3">Side inferred from {data.side_aware.foot} foot.</p>
      )}
    </>
  );
}

/** AI report when a real LLM is wired; otherwise a clean grounded "Model
 *  summary" built from the model outputs — never the raw dev stub (MED-05). */
function ScoutingReport({
  provider,
  narrative,
  loading,
  value,
  potential,
  position,
}: {
  provider?: string;
  narrative?: string;
  loading: boolean;
  value?: { predicted_value_eur: number; drivers: { label: string }[] };
  potential?: { predicted_value_eur: number } | undefined;
  position?: { primary: string; secondary: string | null } | undefined;
}) {
  const isReal = provider === "anthropic";
  return (
    <Card>
      <div className="mb-3 flex items-center gap-2">
        <h2 className="eyebrow">{isReal ? "AI scouting report" : "Model summary"}</h2>
        {!isReal && !loading && <Badge>Full narrative unavailable</Badge>}
      </div>
      {loading && <SkeletonLines rows={4} />}
      {!loading && isReal && (
        <p className="whitespace-pre-line leading-relaxed text-ink-2">{narrative}</p>
      )}
      {!loading && !isReal && (
        <ul className="space-y-2 text-sm text-ink-2">
          {value && (
            <li>
              Model values the player at <b className="text-ink">{money(value.predicted_value_eur)}</b>
              {value.drivers[0] && <> — driven most by {value.drivers[0].label}.</>}
            </li>
          )}
          {potential && (
            <li>
              Projected to <b className="text-ink">{money(potential.predicted_value_eur)}</b> over the
              next three years.
            </li>
          )}
          {position && (
            <li>
              Reads as a <b className="text-ink">{position.primary}</b>
              {position.secondary && <> (also {position.secondary})</> } from playing style.
            </li>
          )}
        </ul>
      )}
    </Card>
  );
}
