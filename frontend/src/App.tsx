import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type Health = { status: string; service: string; version: string };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="min-h-screen bg-pitch-900 text-white flex flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-4xl font-bold tracking-tight">
        Scout OS <span className="text-pitch-500">⚽</span>
      </h1>
      <p className="text-white/70 max-w-md text-center">
        AI-powered football scouting platform. Phase 0 scaffold — backend and
        frontend are wired together.
      </p>

      <div className="rounded-lg border border-white/10 bg-white/5 px-6 py-4 min-w-[280px]">
        <div className="text-sm uppercase tracking-wide text-white/50 mb-2">
          Backend status
        </div>
        {health && (
          <div className="text-pitch-500 font-mono">
            ● {health.status} — {health.service} v{health.version}
          </div>
        )}
        {error && <div className="text-red-400 font-mono">● {error}</div>}
        {!health && !error && <div className="text-white/40">Connecting…</div>}
      </div>
    </div>
  );
}
