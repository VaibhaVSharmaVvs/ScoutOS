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
        className="w-full rounded-lg border border-white/15 bg-surface-800 px-4 py-3 text-white placeholder-white/40 outline-none focus:border-pitch-400"
      />
      {open && debounced.trim().length >= 2 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-white/10 bg-surface-800 shadow-xl overflow-hidden">
          {isFetching && <div className="px-4 py-3 text-white/40 text-sm">Searching…</div>}
          {!isFetching && data && data.length === 0 && (
            <div className="px-4 py-3 text-white/40 text-sm">No players found.</div>
          )}
          {data?.map((p) => (
            <button
              key={p.id}
              onMouseDown={() => go(p.id)}
              className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-white/5"
            >
              <span className="text-white">{p.full_name}</span>
              <span className="text-xs text-white/40">
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
