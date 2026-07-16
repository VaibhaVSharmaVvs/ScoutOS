import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../api/auth";
import { Card } from "../components/ui";

export function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto py-10">
      <Card>
        <h1 className="text-xl font-bold mb-1">{mode === "login" ? "Log in" : "Create account"}</h1>
        <p className="text-sm text-white/50 mb-5">Access the Scout OS platform.</p>
        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="w-full rounded-lg border border-white/15 bg-surface-800 px-3 py-2.5 outline-none focus:border-pitch-400"
          />
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full rounded-lg border border-white/15 bg-surface-800 px-3 py-2.5 outline-none focus:border-pitch-400"
          />
          {error && <div className="text-sm text-red-400">{error}</div>}
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-pitch-500 py-2.5 font-medium hover:bg-pitch-600 disabled:opacity-50"
          >
            {busy ? "…" : mode === "login" ? "Log in" : "Register"}
          </button>
        </form>
        <button
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="mt-4 text-sm text-white/50 hover:text-white"
        >
          {mode === "login" ? "Need an account? Register" : "Have an account? Log in"}
        </button>
      </Card>
    </div>
  );
}
