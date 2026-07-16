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
    <div className="flex flex-col items-center gap-10 py-8">
      <div className="text-center max-w-2xl">
        <h1 className="text-4xl font-bold tracking-tight mb-3">Scout smarter.</h1>
        <p className="text-white/60">
          AI-powered scouting across Europe’s top five leagues — market value, potential,
          playing style, position, and club fit, each explained by the model’s own drivers.
        </p>
      </div>
      <div className="w-full flex justify-center">
        <SearchBar autoFocus />
      </div>

      <div className="w-full">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-white/50 mb-3">
          Featured players
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
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
    <Card className="hover:border-pitch-400/50 transition-colors cursor-pointer h-full">
      <div className="font-semibold">{name}</div>
      <div className="text-xs text-white/40 mt-1">
        {hit ? `${hit.primary_position ?? "—"} · ${hit.nationality ?? "—"}` : "…"}
      </div>
    </Card>
  );
  return hit ? <Link to={`/player/${hit.id}`}>{inner}</Link> : inner;
}
