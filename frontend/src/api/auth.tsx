// Auth context: passwordless via WebAuthn passkeys. The JWT (in localStorage) is
// still the API credential; passkeys just replace how it's obtained.

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { getToken, setToken } from "./client";
import { loginPasskey, registerPasskey } from "./passkey";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  signIn: () => Promise<void>;
  register: (displayName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(getToken());

  const signIn = useCallback(async () => {
    await loginPasskey();
    setTok(getToken());
  }, []);

  const register = useCallback(async (displayName?: string) => {
    await registerPasskey(displayName);
    setTok(getToken());
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setTok(null);
  }, []);

  const value = useMemo(
    () => ({ token, isAuthenticated: !!token, signIn, register, logout }),
    [token, signIn, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
