import { Link } from "react-router-dom";

import { usePlayerSearch } from "../api/hooks";
import { SearchBar } from "../components/SearchBar";
import { Card, Monogram } from "../components/ui";
import { age, money } from "../lib/format";

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
    <div className="flex flex-col items-center gap-12 py-10">
      <div className="max-w-2xl text-center">
        <h1 className="font-semibold" style={{ fontSize: "clamp(34px, 6vw, 52px)", lineHeight: 1.02, letterSpacing: "-0.03em" }}>
          Scout smarter.
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-ink-2">
          AI-powered scouting across Europe’s top five leagues — market value, potential, playing
          style, position, and club fit, each explained by the model’s own drivers.
        </p>
      </div>
      <div className="flex w-full justify-center">
        <SearchBar autoFocus />
      </div>

      <div className="w-full">
        <h2 className="eyebrow mb-3">Featured players</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURED.map((name, i) => (
            <FeaturedCard key={name} name={name} index={i} />
          ))}
        </div>
      </div>

      <div className="w-full border-t border-line pt-8">
        <h2 className="eyebrow mb-4">What you get on every player</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          {CAPABILITIES.map((c) => (
            <div key={c.title}>
              <div className="font-medium text-ink">{c.title}</div>
              <p className="mt-1 text-sm text-ink-3">{c.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const CAPABILITIES = [
  { title: "Value & potential", body: "A model estimate with the drivers behind it, and a three-year projection." },
  { title: "Style & position", body: "A position-appropriate percentile profile and the roles the player fits." },
  { title: "Similar players & club fit", body: "Stylistic matches and the clubs where a move makes sense." },
];

function FeaturedCard({ name, index }: { name: string; index: number }) {
  const { data } = usePlayerSearch(name);
  const hit = data?.find((p) => p.full_name === name) ?? data?.[0];
  const a = age(hit?.birth_year);
  const inner = (
    <Card className="card-hover group flex h-full items-center gap-3">
      <Monogram name={name} />
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{name}</div>
        <div className="mt-0.5 truncate text-caption text-ink-3">
          {hit ? `${hit.primary_position ?? "—"} · ${hit.nationality ?? "—"}` : "…"}
        </div>
      </div>
      <div className="text-right">
        <div className="tnum text-sm font-semibold text-ink">{money(hit?.market_value_eur)}</div>
        {a && <div className="tnum text-caption text-ink-3">age {a}</div>}
      </div>
      <span className="text-ink-muted transition-transform group-hover:translate-x-0.5 group-hover:text-ink-2">→</span>
    </Card>
  );
  return (
    <div className="rise" style={{ animationDelay: `${index * 50}ms` }}>
      {hit ? <Link to={`/player/${hit.id}`}>{inner}</Link> : inner}
    </div>
  );
}
