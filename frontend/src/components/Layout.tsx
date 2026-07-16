import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../api/auth";
import { SearchBar } from "./SearchBar";

export function Layout() {
  const { isAuthenticated, logout } = useAuth();
  return (
    <div className="min-h-screen bg-pitch-900 text-white">
      <header className="border-b border-white/10 bg-surface-900/70 backdrop-blur sticky top-0 z-30">
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center gap-4">
          <Link to="/" className="text-xl font-bold tracking-tight whitespace-nowrap">
            Scout OS <span className="text-pitch-400">⚽</span>
          </Link>
          <nav className="hidden md:flex gap-1 text-sm">
            <NavItem to="/">Home</NavItem>
            <NavItem to="/squad">Squad Analyzer</NavItem>
          </nav>
          <div className="flex-1 flex justify-center">
            <SearchBar />
          </div>
          {isAuthenticated ? (
            <button onClick={logout} className="text-sm text-white/60 hover:text-white">
              Log out
            </button>
          ) : (
            <NavLink to="/login" className="text-sm text-white/60 hover:text-white">
              Log in
            </NavLink>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded px-3 py-1.5 ${isActive ? "bg-white/10 text-white" : "text-white/60 hover:text-white"}`
      }
    >
      {children}
    </NavLink>
  );
}
