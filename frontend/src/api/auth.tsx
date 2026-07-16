// Minimal JWT auth context backed by localStorage + the backend /auth routes.

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { api, getToken, setToken } from "./client";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTok] = useState<string | null>(getToken());

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.postForm<{ access_token: string }>("/auth/login", {
      username: email,
      password,
    });
    setToken(res.access_token);
    setTok(res.access_token);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await api.postJson("/auth/register", { email, password });
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    setToken(null);
    setTok(null);
  }, []);

  const value = useMemo(
    () => ({ token, isAuthenticated: !!token, login, register, logout }),
    [token, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
