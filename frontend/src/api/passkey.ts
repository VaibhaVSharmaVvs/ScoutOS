// WebAuthn passkey ceremonies, browser side. @simplewebauthn/browser drives the
// navigator.credentials calls; we just shuttle options/results to the backend.

import { startAuthentication, startRegistration } from "@simplewebauthn/browser";

import { api, setToken } from "./client";

interface BeginResponse {
  ceremony_id: string;
  options: Record<string, unknown>;
}

export function browserSupportsPasskeys(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.PublicKeyCredential !== "undefined" &&
    !!navigator.credentials
  );
}

export async function registerPasskey(displayName?: string): Promise<string> {
  const begin = await api.postJson<BeginResponse>("/auth/passkey/register/begin", {
    display_name: displayName,
  });
  const credential = await startRegistration({ optionsJSON: begin.options as never });
  const { access_token } = await api.postJson<{ access_token: string }>(
    "/auth/passkey/register/complete",
    { ceremony_id: begin.ceremony_id, credential },
  );
  setToken(access_token);
  return access_token;
}

export async function loginPasskey(): Promise<string> {
  const begin = await api.postJson<BeginResponse>("/auth/passkey/login/begin", {});
  const credential = await startAuthentication({ optionsJSON: begin.options as never });
  const { access_token } = await api.postJson<{ access_token: string }>(
    "/auth/passkey/login/complete",
    { ceremony_id: begin.ceremony_id, credential },
  );
  setToken(access_token);
  return access_token;
}
