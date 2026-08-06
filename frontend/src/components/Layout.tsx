import { motion } from "motion/react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../api/auth";
import { useReducedMotion } from "../lib/useReducedMotion";
import { SearchBar } from "./SearchBar";

export function Layout() {
  const { isAuthenticated, logout } = useAuth();
  const { pathname } = useLocation();
  const reduced = useReducedMotion();
  const isHome = pathname === "/";
  // top-level route key: switching sections (Home / Player / Squad) replays the
  // transition; navigating between a player's own tabs stays within PlayerLayout
  // (its own Motion), so key on the section root, not the full path.
  const routeKey = pathname.split("/").slice(0, 3).join("/");

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <a href="#content" className="skip-link">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-line bg-[rgb(11_15_16/0.85)] backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-5 px-5 py-3">
          <Wordmark />
          <nav className="hidden gap-0.5 text-sm md:flex">
            <NavItem to="/">Home</NavItem>
            <NavItem to="/squad">Squad Analyzer</NavItem>
          </nav>
          {/* one global search — hidden on Home, where the hero field is the search */}
          <div className="flex flex-1 justify-center">
            {!isHome && <SearchBar />}
          </div>
          {isAuthenticated ? (
            <button
              onClick={logout}
              className="text-sm text-ink-3 transition-colors hover:text-ink"
            >
              Log out
            </button>
          ) : (
            <NavLink to="/login" className="text-sm text-ink-3 transition-colors hover:text-ink">
              Sign in
            </NavLink>
          )}
        </div>
      </header>
      <motion.main
        id="content"
        key={routeKey}
        // Home owns its full-bleed hero, so it renders edge-to-edge; every other
        // route sits in the standard centred content column.
        className={isHome ? "" : "mx-auto max-w-6xl px-5 py-7"}
        initial={reduced ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.26, ease: [0.23, 1, 0.32, 1] }}
      >
        <Outlet />
      </motion.main>
    </div>
  );
}

function Wordmark() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2 whitespace-nowrap">
      {/* centre-circle mark — a pitch marking, not an emoji */}
      <span className="relative grid h-6 w-6 place-items-center rounded-full border border-strong">
        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
        <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-[var(--line-strong)]" />
      </span>
      <span className="text-h4 font-semibold tracking-tight">
        Scout<span className="text-accent">OS</span>
      </span>
    </Link>
  );
}

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-sm px-3 py-1.5 transition-colors ${
          isActive ? "bg-white/[0.06] text-ink" : "text-ink-3 hover:text-ink"
        }`
      }
    >
      {children}
    </NavLink>
  );
}
