export function money(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1e9) return `€${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `€${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `€${(v / 1e3).toFixed(0)}k`;
  return `€${v.toFixed(0)}`;
}

export function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

export function num(v: number | null | undefined, digits = 1): string {
  return v == null ? "—" : v.toFixed(digits);
}
