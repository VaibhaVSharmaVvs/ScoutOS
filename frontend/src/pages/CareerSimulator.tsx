import { useParams } from "react-router-dom";

import { useCareerSim } from "../api/hooks";
import { DriverList } from "../components/DriverList";
import { ValueChart } from "../components/ValueChart";
import { Card, EmptyState, Loading, SectionTitle } from "../components/ui";
import { money } from "../lib/format";

export function CareerSimulator() {
  const playerId = Number(useParams().id);
  const { data, isLoading, isError } = useCareerSim(playerId);

  if (isLoading) return <Loading label="Simulating trajectory" />;
  if (isError || !data)
    return <EmptyState title="No trajectory to simulate" hint="This player has no current market value, so future value can’t be projected." />;

  const chart = data.trajectory
    .filter((p) => p.value_eur != null)
    .map((p) => ({ label: p.label, value: p.value_eur as number }));

  return (
    <div className="space-y-6">
      <Card>
        <SectionTitle>Projected value trajectory</SectionTitle>
        <ValueChart data={chart} />
        <div className="mt-5 flex gap-4 border-t border-line pt-4">
          {data.trajectory.map((p) => (
            <div key={p.label} className="flex-1 text-center">
              <div className="eyebrow mb-1">
                {p.label}
                {p.age ? ` · age ${p.age}` : ""}
              </div>
              <div className="tnum text-h3 font-semibold text-accent">{money(p.value_eur)}</div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-caption text-ink-muted">{data.note}</p>
      </Card>

      {data.trajectory
        .filter((p) => p.drivers.length > 0)
        .map((p) => (
          <Card key={p.label}>
            <SectionTitle>What drives the {p.label} projection</SectionTitle>
            <DriverList drivers={p.drivers} />
          </Card>
        ))}
    </div>
  );
}
