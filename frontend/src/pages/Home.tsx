import { Link } from "react-router-dom";

import { usePlayerSearch } from "../api/hooks";
import { SearchBar } from "../components/SearchBar";
import { Card } from "../components/ui";

const FEATURED = [
  "Erling Haaland",
  "Jude Bellingham",
  "Vinicius Junior",
  "Rodri",
  "Florian Wirtz",
  "Lautaro Martinez",
];

export function Home() {
  return (
    <div className="flex flex-col items-center gap-10 py-10">
      <div className="max-w-2xl text-center">
        <h1 className="mb-3 text-h1 font-semibold">Scout smarter.</h1>
        <p className="text-ink-2">
          AI-powered scouting across Europe’s top five leagues — market value, potential, playing
          style, position, and club fit, each explained by the model’s own drivers.
        </p>
      </div>
      <div className="flex w-full justify-center">
        <SearchBar autoFocus />
      </div>

      <div className="w-full">
        <h2 className="eyebrow mb-3">Featured players</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {FEATURED.map((name) => (
            <FeaturedCard key={name} name={name} />
          ))}
        </div>
      </div>
    </div>
  );
}

function FeaturedCard({ name }: { name: string }) {
  const { data } = usePlayerSearch(name);
  const hit = data?.find((p) => p.full_name === name) ?? data?.[0];
  const inner = (
    <Card className="h-full cursor-pointer transition-colors hover:border-strong">
      <div className="font-medium">{name}</div>
      <div className="mt-1 text-caption text-ink-3">
        {hit ? `${hit.primary_position ?? "—"} · ${hit.nationality ?? "—"}` : "…"}
      </div>
    </Card>
  );
  return hit ? <Link to={`/player/${hit.id}`}>{inner}</Link> : inner;
}
