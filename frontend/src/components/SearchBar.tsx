// Debounced search-as-you-type with a results dropdown.
// Two looks: the compact header search (default) and a large hero pill (hero).

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { usePlayerSearch } from "../api/hooks";
import { useDebounced } from "../lib/useDebounced";

export function SearchBar({
  autoFocus = false,
  variant = "default",
  id,
}: {
  autoFocus?: boolean;
  variant?: "default" | "hero";
  id?: string;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const debounced = useDebounced(q, 300);
  const { data, isFetching } = usePlayerSearch(debounced);
  const navigate = useNavigate();
  const hero = variant === "hero";

  function go(id: number) {
    setOpen(false);
    setQ("");
    navigate(`/player/${id}`);
  }

  function submitTop() {
    if (data && data.length > 0) go(data[0].id);
  }

  const dropdown = open && debounced.trim().length >= 2 && (
    <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-lg border border-line bg-surface-overlay shadow-2xl shadow-black/50">
      {isFetching && <div className="px-4 py-3 text-sm text-ink-muted">Searching…</div>}
      {!isFetching && data && data.length === 0 && (
        <div className="px-4 py-3 text-sm text-ink-muted">No players found.</div>
      )}
      {data?.map((p) => (
        <button
          key={p.id}
          onMouseDown={() => go(p.id)}
          className="flex w-full items-center justify-between px-4 py-2.5 text-left transition-colors hover:bg-white/[0.05]"
        >
          <span className="text-sm text-ink">{p.full_name}</span>
          <span className="text-caption text-ink-3">
            {p.primary_position ?? "—"}
            {p.nationality ? ` · ${p.nationality}` : ""}
          </span>
        </button>
      ))}
    </div>
  );

  if (hero) {
    return (
      <div className="relative w-full max-w-2xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitTop();
          }}
          className="group flex items-center gap-2 rounded-full border border-line bg-input py-2 pl-4 pr-2 backdrop-blur-sm transition-colors focus-within:border-accent/50 focus-within:shadow-[0_0_0_4px_var(--accent-soft)]"
        >
          <span className="pointer-events-none text-ink-3">
            <SearchIcon size={18} />
          </span>
          <input
            id={id}
            autoFocus={autoFocus}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            placeholder="Search players by name…"
            className="min-w-0 flex-1 border-0 bg-transparent py-1.5 text-base text-ink placeholder-ink-muted outline-none"
          />
          <button
            type="submit"
            aria-label="Search"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-accent/40 text-accent transition-colors hover:bg-accent hover:text-accent-ink"
          >
            <ArrowIcon />
          </button>
        </form>
        {dropdown}
      </div>
    );
  }

  return (
    <div className="relative w-full max-w-xl">
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3">
        <SearchIcon />
      </span>
      <input
        id={id}
        autoFocus={autoFocus}
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search players…"
        className="w-full rounded-md border border-line bg-input py-2 pl-9 pr-3 text-sm text-ink placeholder-ink-muted outline-none transition-colors focus:border-accent/60"
      />
      {dropdown}
    </div>
  );
}

function SearchIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" strokeLinecap="round" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
