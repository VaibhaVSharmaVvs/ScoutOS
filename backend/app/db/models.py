"""Normalized schema for Scout OS.

Design notes:
- `players` is the canonical entity. Each source's identifier maps to it via
  `entity_xref` (the cross-source resolution built in Phase 2b). Transfermarkt
  is the spine (has full DOB + player_id + market values); FBref (name + birth
  year) and Understat (own player_id) are matched onto it.
- Wide, source-specific stat columns are NOT enumerated as SQL columns; the
  core queryable metrics are promoted and the full detailed stat set is kept in
  a JSONB `stats` blob per (player, season, club, source). Phase 3 materializes
  ML features from these.
- Reference tables (league/season/club) are deduplicated dimensions.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# --- Source enumeration (kept as a plain string + check constraint) ----------
SOURCES = ("fbref", "fbref_kaggle", "understat", "transfermarkt", "clubelo", "statsbomb")


# --- Auth ---------------------------------------------------------------------
class User(Base, TimestampMixin):
    """API user. Single-role for now (Phase 5); expand to roles later."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


# --- Dimensions ---------------------------------------------------------------
class League(Base, TimestampMixin):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # 'ENG-Premier League'
    name: Mapped[str] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(64))
    tier: Mapped[int | None] = mapped_column(Integer, default=1)
    # source competition codes for joining (e.g. Transfermarkt 'GB1')
    transfermarkt_code: Mapped[str | None] = mapped_column(String(16), index=True)

    seasons_stats: Mapped[list[PlayerSeasonStats]] = relationship(back_populates="league")


class Season(Base, TimestampMixin):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # '2024-25'
    code: Mapped[str] = mapped_column(String(8), index=True)  # soccerdata '2425'
    start_year: Mapped[int] = mapped_column(Integer, index=True)


class Club(Base, TimestampMixin):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    normalized_name: Mapped[str] = mapped_column(String(128), index=True)
    country: Mapped[str | None] = mapped_column(String(64))
    # per-source identifiers (nullable; filled as matched)
    transfermarkt_id: Mapped[int | None] = mapped_column(Integer, index=True)
    understat_id: Mapped[int | None] = mapped_column(Integer, index=True)
    fbref_name: Mapped[str | None] = mapped_column(String(128))
    clubelo_name: Mapped[str | None] = mapped_column(String(128), index=True)

    __table_args__ = (UniqueConstraint("normalized_name", "country", name="uq_club_name_country"),)


# --- Canonical player + cross-source resolution -------------------------------
class Player(Base, TimestampMixin):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    normalized_name: Mapped[str] = mapped_column(String(160), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    birth_year: Mapped[int | None] = mapped_column(Integer, index=True)
    nationality: Mapped[str | None] = mapped_column(String(64))
    primary_position: Mapped[str | None] = mapped_column(String(32))
    foot: Mapped[str | None] = mapped_column(String(16))
    height_cm: Mapped[int | None] = mapped_column(Integer)
    # youth-value / potential signals (from Transfermarkt; Phase 4 value_v2)
    international_caps: Mapped[int | None] = mapped_column(Integer)
    international_goals: Mapped[int | None] = mapped_column(Integer)
    contract_expiration: Mapped[date | None] = mapped_column(Date)
    highest_market_value_eur: Mapped[int | None] = mapped_column(Numeric(14, 0))

    xrefs: Mapped[list[EntityXref]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    season_stats: Mapped[list[PlayerSeasonStats]] = relationship(back_populates="player")
    market_values: Mapped[list[MarketValue]] = relationship(back_populates="player")


class EntityXref(Base, TimestampMixin):
    """Maps a canonical player to one source's identifier.

    source_id: stable id where the source has one (Understat/Transfermarkt).
    source_key: composite natural key where it doesn't (FBref: name|birth|...).
    """

    __tablename__ = "entity_xref"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    source_id: Mapped[str | None] = mapped_column(String(64), index=True)
    source_key: Mapped[str | None] = mapped_column(String(256), index=True)
    match_method: Mapped[str | None] = mapped_column(String(32))  # exact|fuzzy|manual
    confidence: Mapped[float | None] = mapped_column(Float)

    player: Mapped[Player] = relationship(back_populates="xrefs")

    __table_args__ = (
        UniqueConstraint("source", "source_id", "source_key", name="uq_xref_source_identity"),
        CheckConstraint(f"source IN {SOURCES}", name="ck_xref_source"),
    )


# --- Facts --------------------------------------------------------------------
class PlayerSeasonStats(Base, TimestampMixin):
    __tablename__ = "player_season_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id"), index=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)

    # Promoted core metrics (queryable); full detail in `stats`.
    minutes: Mapped[int | None] = mapped_column(Integer)
    matches: Mapped[int | None] = mapped_column(Integer)
    goals: Mapped[float | None] = mapped_column(Float)
    assists: Mapped[float | None] = mapped_column(Float)
    xg: Mapped[float | None] = mapped_column(Float)
    xa: Mapped[float | None] = mapped_column(Float)
    position: Mapped[str | None] = mapped_column(String(32))
    stats: Mapped[dict | None] = mapped_column(JSONB)

    player: Mapped[Player] = relationship(back_populates="season_stats")
    league: Mapped[League] = relationship(back_populates="seasons_stats")

    __table_args__ = (
        UniqueConstraint(
            "player_id", "season_id", "club_id", "source", name="uq_pss_player_season_club_source"
        ),
        CheckConstraint(f"source IN {SOURCES}", name="ck_pss_source"),
    )


class MarketValue(Base, TimestampMixin):
    __tablename__ = "market_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id"))
    as_of: Mapped[date] = mapped_column(Date, index=True)
    value_eur: Mapped[int | None] = mapped_column(Numeric(14, 0))

    player: Mapped[Player] = relationship(back_populates="market_values")

    __table_args__ = (UniqueConstraint("player_id", "as_of", name="uq_mv_player_date"),)


class Transfer(Base, TimestampMixin):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    transfer_date: Mapped[date | None] = mapped_column(Date, index=True)
    season_label: Mapped[str | None] = mapped_column(String(16))
    from_club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id"))
    to_club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id"))
    fee_eur: Mapped[int | None] = mapped_column(Numeric(14, 0))
    market_value_eur: Mapped[int | None] = mapped_column(Numeric(14, 0))


class ClubStrength(Base, TimestampMixin):
    """ClubElo snapshots. club_id nullable until resolved to a Club."""

    __tablename__ = "club_strength"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id"), index=True)
    clubelo_name: Mapped[str] = mapped_column(String(128), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    elo: Mapped[float | None] = mapped_column(Float)
    rank: Mapped[int | None] = mapped_column(Integer)
    country: Mapped[str | None] = mapped_column(String(16))
    league_code: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        UniqueConstraint("clubelo_name", "snapshot_date", name="uq_elo_name_date"),
    )


class PlayerFeatures(Base, TimestampMixin):
    """ML-ready features per player-season (Phase 3).

    Merges the source rows (fbref_kaggle detailed + understat xG) into one
    normalized feature vector. Context columns are promoted for querying; the
    numeric feature vector (per-90 + rate + percentile features) lives in the
    JSONB `features` blob, keyed by feature name. `feature_set_version` lets us
    evolve the feature set without breaking trained models.
    """

    __tablename__ = "player_features"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id"))
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id"))
    feature_set_version: Mapped[str] = mapped_column(String(16), index=True)

    age: Mapped[float | None] = mapped_column(Float)
    minutes: Mapped[int | None] = mapped_column(Integer)
    matches: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(String(32))
    position_group: Mapped[str | None] = mapped_column(String(8), index=True)
    club_elo: Mapped[float | None] = mapped_column(Float)
    league_strength: Mapped[float | None] = mapped_column(Float)
    market_value_eur: Mapped[int | None] = mapped_column(Numeric(14, 0))  # value-model target

    features: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint("player_id", "season_id", "feature_set_version",
                         name="uq_pf_player_season_version"),
    )


class TeamTacticalProfile(Base, TimestampMixin):
    """Per club-season tactical profile, aggregated from player stats (Phase 3)."""

    __tablename__ = "team_tactical_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), index=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id"))
    profile: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        UniqueConstraint("club_id", "season_id", name="uq_ttp_club_season"),
    )
