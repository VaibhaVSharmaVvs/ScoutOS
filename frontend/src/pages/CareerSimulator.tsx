import { useParams } from "react-router-dom";

import { useCareerSim } from "../api/hooks";
import { DriverList } from "../components/DriverList";
import { ValueChart } from "../components/ValueChart";
import { Card, Empty, Loading, SectionTitle } from "../components/ui";
import { money } from "../lib/format";

export function CareerSimulator() {
  const playerId = Number(useParams().id);
  const { data, isLoading, isError } = useCareerSim(playerId);

  if (isLoading) return <Loading label="Simulating trajectory…" />;
  if (isError || !data) return <Empty>No current market value — trajectory can’t be simulated.</Empty>;

  const chart = data.trajectory
    .filter((p) => p.value_eur != null)
    .map((p) => ({ label: p.label, value: p.value_eur as number }));

  return (
    <div className="space-y-6">
      <Card>
        <SectionTitle>Projected value trajectory</SectionTitle>
        <ValueChart data={chart} />
        <div className="mt-4 flex gap-4">
          {data.trajectory.map((p) => (
            <div key={p.label} className="flex-1 text-center">
              <div className="text-xs text-white/40">{p.label}{p.age ? ` · age ${p.age}` : ""}</div>
              <div className="text-lg font-bold text-pitch-400">{money(p.value_eur)}</div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-white/40">{data.note}</p>
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
