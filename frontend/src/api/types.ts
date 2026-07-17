// TS mirrors of the backend Pydantic schemas (backend/app/schemas.py).

export interface PlayerHit {
  id: number;
  full_name: string;
  primary_position: string | null;
  nationality: string | null;
  birth_year: number | null;
  foot: string | null;
}

export interface SeasonStat {
  season: string;
  club: string | null;
  league: string | null;
  minutes: number | null;
  matches: number | null;
  goals: number | null;
  assists: number | null;
  xg: number | null;
  xa: number | null;
}

export interface PlayerProfile {
  id: number;
  full_name: string;
  primary_position: string | null;
  nationality: string | null;
  date_of_birth: string | null;
  foot: string | null;
  height_cm: number | null;
  market_value_eur: number | null;
  highest_market_value_eur: number | null;
  contract_expiration: string | null;
  international_caps: number | null;
  seasons: SeasonStat[];
}

export interface Driver {
  feature: string;
  label: string;
  value: number | null;
  effect: string | null;
  weight: number;
}

export interface ValuePrediction {
  player_id: number;
  season: string;
  predicted_value_eur: number;
  actual_value_eur: number | null;
  drivers: Driver[];
}

export interface PotentialPrediction {
  player_id: number;
  season: string;
  horizon_years: number;
  current_value_eur: number | null;
  predicted_value_eur: number;
  drivers: Driver[];
}

export interface PositionPrediction {
  player_id: number;
  season: string;
  primary: string;
  secondary: string | null;
  playable: string[];
  probs: Record<string, number>;
  side_aware: { primary: string; secondary: string; foot: string; probs: Record<string, number> } | null;
}

export interface SimilarPlayer {
  player_id: number;
  player: string;
  position_group: string | null;
  similarity: number;
  season: number | null;
  shared_traits: { feature: string; label: string }[] | null;
}

export interface SimilarResponse {
  player_id: number;
  mode: string;
  results: SimilarPlayer[];
}

export interface ClubFit {
  club: string;
  club_id: number | null;
  tactical_fit: number;
  squad_fit: number;
  financial_fit: number;
  age_fit: number;
  overall_fit: number;
}

export interface ClubFitResponse {
  player_id: number;
  player: string;
  results: ClubFit[];
}

export interface RadarMetric {
  metric: string;
  label: string;
  percentile: number;
  per90: number | null;
}

export interface RadarResponse {
  player_id: number;
  season: string;
  position_group: string | null;
  focus: string;
  metrics: RadarMetric[];
  strengths: string[];
  weaknesses: string[];
  note: string | null;
}

export interface MarketValuePoint {
  as_of: string;
  value_eur: number;
}

export interface ClubHit {
  id: number;
  name: string;
  country: string | null;
}

export interface PositionDepth {
  position_group: string;
  squad_size: number;
  regulars: number;
  avg_age: number | null;
  total_value_eur: number | null;
}

export interface SquadAnalysis {
  club_id: number;
  club: string;
  season: string;
  squad_size: number;
  avg_age: number | null;
  total_value_eur: number | null;
  depth: PositionDepth[];
  gaps: string[];
}

export interface CareerPoint {
  label: string;
  horizon_years: number;
  age: number | null;
  value_eur: number | null;
  drivers: Driver[];
}

export interface CareerSimulation {
  player_id: number;
  player: string;
  season: string;
  trajectory: CareerPoint[];
  note: string;
}

export interface Explanation {
  kind: string;
  narrative: string;
  provider: string;
  cached: boolean;
  grounding: Record<string, unknown>;
}
