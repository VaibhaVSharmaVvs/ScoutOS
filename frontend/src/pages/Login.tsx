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
    <div className="mx-auto flex min-h-[70vh] max-w-sm items-center">
      <Card className="w-full">
        <h1 className="mb-1 text-h3 font-semibold">Sign in</h1>
        <p className="mb-5 text-sm text-ink-3">
          Passwordless — use a passkey (Windows Hello, Touch ID, or your phone). No email, no
          password.
        </p>

        {!supported && (
          <div className="mb-4 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
            This browser doesn’t support passkeys. Try a recent Chrome, Edge, or Safari.
          </div>
        )}

        <button
          onClick={() => run("signin")}
          disabled={!supported || busy !== null}
          className="w-full rounded-md bg-accent py-2.5 font-medium text-accent-ink transition-transform duration-150 ease-out hover:brightness-105 active:scale-[0.98] disabled:opacity-50"
        >
          {busy === "signin" ? "Waiting for passkey…" : "Sign in with a passkey"}
        </button>

        <div className="my-5 flex items-center gap-3 text-caption text-ink-muted">
          <span className="h-px flex-1 bg-[var(--line)]" /> first time here?{" "}
          <span className="h-px flex-1 bg-[var(--line)]" />
        </div>

        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name this device (optional)"
          className="mb-3 w-full rounded-md border border-line bg-input px-3 py-2.5 text-sm text-ink placeholder-ink-muted outline-none transition-colors focus:border-accent/60"
        />
        <button
          onClick={() => run("register")}
          disabled={!supported || busy !== null}
          className="w-full rounded-md border border-strong py-2.5 font-medium transition-colors hover:bg-white/[0.05] active:scale-[0.98] disabled:opacity-50"
        >
          {busy === "register" ? "Creating passkey…" : "Create a passkey"}
        </button>

        {error && <div className="mt-4 text-sm text-danger">{error}</div>}
      </Card>
    </div>
  );
}
