import { NavLink, Outlet, useParams } from "react-router-dom";

import { usePlayer } from "../api/hooks";
import { Badge, ErrorState, Loading } from "../components/ui";
import { money } from "../lib/format";

export function PlayerLayout() {
  const { id } = useParams();
  const playerId = Number(id);
  const { data: p, isLoading, error } = usePlayer(playerId);

  if (isLoading) return <Loading label="Loading player…" />;
  if (error) return <ErrorState error={error} />;
  if (!p) return null;

  const tabs = [
    { to: `/player/${playerId}`, label: "Overview", end: true },
    { to: `/player/${playerId}/similar`, label: "Similar" },
    { to: `/player/${playerId}/clubs`, label: "Club Fit" },
    { to: `/player/${playerId}/career`, label: "Career" },
  ];

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-white/10 bg-surface-800/60 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">{p.full_name}</h1>
            <div className="mt-2 flex flex-wrap gap-2 text-sm text-white/60">
              {p.primary_position && <Badge>{p.primary_position}</Badge>}
              {p.nationality && <span>{p.nationality}</span>}
              {p.foot && <span>· {p.foot}-footed</span>}
              {p.height_cm && <span>· {p.height_cm} cm</span>}
              {p.date_of_birth && <span>· b. {p.date_of_birth}</span>}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs uppercase tracking-wide text-white/40">Market value</div>
            <div className="text-2xl font-bold text-pitch-400">{money(p.market_value_eur)}</div>
            {p.highest_market_value_eur != null && (
              <div className="text-xs text-white/40">peak {money(p.highest_market_value_eur)}</div>
            )}
          </div>
        </div>
      </div>

      <div className="flex gap-1 border-b border-white/10">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              `px-4 py-2 text-sm border-b-2 -mb-px ${
                isActive
                  ? "border-pitch-400 text-white"
                  : "border-transparent text-white/50 hover:text-white"
              }`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </div>

      <Outlet context={{ player: p }} />
    </div>
  );
}
