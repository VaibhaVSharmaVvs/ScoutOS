// One money formatter, used everywhere. Drops trailing ".0" (€200M not €200.0M);
// keeps a decimal only when it disambiguates (€1.01B, €7.5M under 10M).
export function money(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1e9) return `€${trim(v / 1e9, 2)}B`;
  if (v >= 1e7) return `€${Math.round(v / 1e6)}M`; // ≥10M: whole millions
  if (v >= 1e6) return `€${trim(v / 1e6, 1)}M`; // 1–10M: one decimal if needed
  if (v >= 1e3) return `€${Math.round(v / 1e3)}k`;
  return `€${Math.round(v)}`;
}

/** Round to `d` decimals, then strip any trailing zeros ("200.0" -> "200"). */
function trim(n: number, d: number): string {
  return parseFloat(n.toFixed(d)).toString();
}

export function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

export function num(v: number | null | undefined, digits = 1): string {
  return v == null ? "—" : v.toFixed(digits);
}

export function age(birthYear: number | null | undefined): number | null {
  if (!birthYear) return null;
  return 2025 - birthYear; // dataset season is 2024-25
}

/** A driver's magnitude in scout words, from its |weight| (MED-02). */
export function driverStrength(weight: number): "strong" | "notable" | "slight" {
  if (weight >= 0.5) return "strong";
  if (weight >= 0.15) return "notable";
  return "slight";
}
