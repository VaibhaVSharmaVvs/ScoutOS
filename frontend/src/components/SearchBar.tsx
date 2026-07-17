// Debounced search-as-you-type with a results dropdown.

import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { usePlayerSearch } from "../api/hooks";
import { useDebounced } from "../lib/useDebounced";

export function SearchBar({ autoFocus = false }: { autoFocus?: boolean }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const debounced = useDebounced(q, 300);
  const { data, isFetching } = usePlayerSearch(debounced);
  const navigate = useNavigate();

  function go(id: number) {
    setOpen(false);
    setQ("");
    navigate(`/player/${id}`);
  }

  return (
    <div className="relative w-full max-w-xl">
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3">
        <SearchIcon />
      </span>
      <input
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
      {open && debounced.trim().length >= 2 && (
        <div className="absolute z-20 mt-1.5 w-full overflow-hidden rounded-md border border-line bg-surface-overlay shadow-2xl shadow-black/40">
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
      )}
    </div>
  );
}

function SearchIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" strokeLinecap="round" />
    </svg>
  );
}
