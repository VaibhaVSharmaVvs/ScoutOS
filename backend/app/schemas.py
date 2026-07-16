"""API response schemas. Kept permissive (Optional fields) — data coverage
varies by player/source, and endpoints should degrade gracefully, not 500."""

from __future__ import annotations

from pydantic import BaseModel


class PlayerHit(BaseModel):
    id: int
    full_name: str
    primary_position: str | None = None
    nationality: str | None = None
    birth_year: int | None = None
    foot: str | None = None


class SeasonStat(BaseModel):
    season: str
    club: str | None = None
    league: str | None = None
    minutes: int | None = None
    matches: int | None = None
    goals: float | None = None
    assists: float | None = None
    xg: float | None = None
    xa: float | None = None


class PlayerProfile(BaseModel):
    id: int
    full_name: str
    primary_position: str | None = None
    nationality: str | None = None
    date_of_birth: str | None = None
    foot: str | None = None
    height_cm: int | None = None
    market_value_eur: float | None = None
    highest_market_value_eur: float | None = None
    contract_expiration: str | None = None
    international_caps: int | None = None
    seasons: list[SeasonStat] = []


class Driver(BaseModel):
    feature: str
    label: str
    value: float | None = None
    effect: str | None = None  # "increases" | "decreases"
    weight: float


class ValuePrediction(BaseModel):
    player_id: int
    season: str
    predicted_value_eur: int
    actual_value_eur: float | None = None
    drivers: list[Driver]


class PotentialPrediction(BaseModel):
    player_id: int
    season: str
    horizon_years: int
    current_value_eur: float | None = None
    predicted_value_eur: int
    drivers: list[Driver]


class PositionPrediction(BaseModel):
    player_id: int
    season: str
    primary: str
    secondary: str | None = None
    playable: list[str]
    probs: dict[str, float]
    side_aware: dict | None = None  # foot-based L/R refinement when foot known


class SimilarPlayer(BaseModel):
    player_id: int
    player: str
    position_group: str | None = None
    similarity: float
    season: int | None = None
    shared_traits: list[dict] | None = None


class SimilarResponse(BaseModel):
    player_id: int
    mode: str
    results: list[SimilarPlayer]


class ClubFit(BaseModel):
    club: str
    club_id: int | None = None
    tactical_fit: float
    squad_fit: float
    financial_fit: float
    age_fit: float
    overall_fit: float


class ClubFitResponse(BaseModel):
    player_id: int
    player: str
    results: list[ClubFit]


class ClubHit(BaseModel):
    id: int
    name: str
    country: str | None = None


class MarketValuePoint(BaseModel):
    as_of: str
    value_eur: float


class RadarMetric(BaseModel):
    metric: str
    label: str
    percentile: float          # 0-1, vs same position group
    per90: float | None = None


class RadarResponse(BaseModel):
    player_id: int
    season: str
    position_group: str | None = None
    metrics: list[RadarMetric]
    strengths: list[str]       # labels of top percentile metrics
    weaknesses: list[str]      # labels of bottom percentile metrics


class PositionDepth(BaseModel):
    position_group: str
    squad_size: int
    regulars: int          # players over the regular-minutes threshold
    avg_age: float | None = None
    total_value_eur: float | None = None


class SquadAnalysis(BaseModel):
    club_id: int
    club: str
    season: str
    squad_size: int
    avg_age: float | None = None
    total_value_eur: float | None = None
    depth: list[PositionDepth]
    gaps: list[str]        # position groups that look thin (few regulars)


class CareerPoint(BaseModel):
    label: str             # "current", "+1yr", "+3yr"
    horizon_years: int     # 0 for current
    age: float | None = None
    value_eur: float | None = None
    drivers: list[Driver] = []


class CareerSimulation(BaseModel):
    player_id: int
    player: str
    season: str
    trajectory: list[CareerPoint]
    note: str


class ExplanationResponse(BaseModel):
    kind: str                  # "report" | "club_fit" | "comparison"
    narrative: str             # scout-style text (LLM or stub)
    provider: str              # "anthropic" | "stub" | "stub-fallback"
    cached: bool
    grounding: dict            # the exact model outputs / facts the narrative is built on


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
