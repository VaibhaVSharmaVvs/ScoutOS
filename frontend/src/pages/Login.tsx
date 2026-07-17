import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../api/auth";
import { browserSupportsPasskeys } from "../api/passkey";
import { Card } from "../components/ui";

export function Login() {
  const { signIn, register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<null | "signin" | "register">(null);
  const supported = browserSupportsPasskeys();

  async function run(kind: "signin" | "register") {
    setError(null);
    setBusy(kind);
    try {
      if (kind === "signin") await signIn();
      else await register(name || undefined);
      navigate("/");
    } catch (err) {
      // user-cancelled gestures throw NotAllowedError — show a friendly message
      const msg = err instanceof Error ? err.message : String(err);
      setError(/NotAllowed|abort/i.test(msg) ? "Passkey prompt was dismissed." : msg);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="max-w-sm mx-auto py-10">
      <Card>
        <h1 className="text-xl font-bold mb-1">Sign in</h1>
        <p className="text-sm text-white/50 mb-5">
          Passwordless — use a passkey (Windows Hello, Touch ID, or your phone). No email,
          no password.
        </p>

        {!supported && (
          <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
            This browser doesn’t support passkeys. Try a recent Chrome, Edge, or Safari.
          </div>
        )}

        <button
          onClick={() => run("signin")}
          disabled={!supported || busy !== null}
          className="w-full rounded-lg bg-pitch-500 py-2.5 font-medium hover:bg-pitch-600 disabled:opacity-50"
        >
          {busy === "signin" ? "Waiting for passkey…" : "Sign in with a passkey"}
        </button>

        <div className="my-5 flex items-center gap-3 text-xs text-white/30">
          <span className="h-px flex-1 bg-white/10" /> first time here? <span className="h-px flex-1 bg-white/10" />
        </div>

        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name this device (optional)"
          className="w-full mb-3 rounded-lg border border-white/15 bg-surface-800 px-3 py-2.5 outline-none focus:border-pitch-400"
        />
        <button
          onClick={() => run("register")}
          disabled={!supported || busy !== null}
          className="w-full rounded-lg border border-white/15 py-2.5 font-medium hover:bg-white/5 disabled:opacity-50"
        >
          {busy === "register" ? "Creating passkey…" : "Create a passkey"}
        </button>

        {error && <div className="mt-4 text-sm text-red-400">{error}</div>}
      </Card>
    </div>
  );
}
