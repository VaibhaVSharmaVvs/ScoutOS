import { Link } from "react-router-dom";

import { SearchBar } from "../components/SearchBar";
import { EmptyState } from "../components/ui";

export function NotFound({ what = "This page slipped the net" }: { what?: string }) {
  return (
    <div className="fade-in flex min-h-[60vh] flex-col items-center justify-center">
      <EmptyState title={what} hint="The link may be stale or the player has moved on. Search, or head back home.">
        <div className="flex w-80 max-w-full flex-col items-center gap-3">
          <SearchBar autoFocus />
          <Link
            to="/"
            className="rounded-md border border-strong px-3 py-1.5 text-sm text-ink transition-colors hover:bg-white/[0.05]"
          >
            Back to home
          </Link>
        </div>
      </EmptyState>
    </div>
  );
}
