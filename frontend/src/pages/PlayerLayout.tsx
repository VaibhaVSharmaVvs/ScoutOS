import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";

import { usePlayer } from "../api/hooks";
import { ApiError } from "../api/client";
import { Badge, Loading } from "../components/ui";
import { NotFound } from "./NotFound";
import { money } from "../lib/format";

export function PlayerLayout() {
  const { id } = useParams();
  const playerId = Number(id);
  const navigate = useNavigate();
  const { data: p, isLoading, error } = usePlayer(playerId);

  if (isLoading) return <Loading label="Loading player" />;
  // 404 -> real not-found state (nav survives); other errors bubble as not-found too
  if (error) {
    const notFound = error instanceof ApiError && error.status === 404;
    return <NotFound what={notFound ? "We couldn’t find that player" : "Something went wrong"} />;
  }
  if (!p) return null;

  const tabs = [
    { to: `/player/${playerId}`, label: "Overview", end: true },
    { to: `/player/${playerId}/similar`, label: "Similar" },
    { to: `/player/${playerId}/clubs`, label: "Club Fit" },
    { to: `/player/${playerId}/career`, label: "Career" },
  ];

  return (
    <div>
      <button
        onClick={() => navigate(-1)}
        className="mb-4 text-caption text-ink-3 transition-colors hover:text-ink"
      >
        ← Back
      </button>
      {/* hero: the player and their value lead; everything else is demoted.
          Sits on the canvas, separated by a chalk line — not boxed. */}
      <div className="flex flex-wrap items-end justify-between gap-6 pb-6">
        <div>
          <div className="eyebrow mb-2">
            {[p.primary_position ?? "Player", p.nationality, p.current_club]
              .filter(Boolean)
              .join(" · ")}
          </div>
          <h1 className="text-h1 font-semibold">{p.full_name}</h1>
          <div className="mt-2.5 flex flex-wrap items-center gap-2 text-sm text-ink-3">
            {p.foot && <Badge>{p.foot}-footed</Badge>}
            {p.age != null && <span>age {p.age}</span>}
            {p.height_cm && <span>· {p.height_cm} cm</span>}
            {p.international_caps != null && <span>· {p.international_caps} caps</span>}
          </div>
        </div>
        {/* the one hero number, explicitly sourced (CRIT-03) */}
        <div className="text-right">
          <div className="eyebrow mb-1.5">Transfermarkt value</div>
          <div className="tnum text-display font-semibold text-accent">
            {money(p.market_value_eur)}
          </div>
          {p.highest_market_value_eur != null && (
            <div className="tnum mt-1 text-caption text-ink-3">
              career peak {money(p.highest_market_value_eur)}
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-1 border-b border-line">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              `-mb-px border-b-2 px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? "border-accent text-ink"
                  : "border-transparent text-ink-3 hover:text-ink"
              }`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </div>

      <div className="pt-6">
        <Outlet context={{ player: p }} />
      </div>
    </div>
  );
}
