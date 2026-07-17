"""Lazy, cached loaders for the trained Phase 4 models.

Each loader is memoized so a model's artifacts load once per process. The ml.*
modules (value/potential/position/similarity/club_fit/explain) own the actual
inference logic; this module just holds the singletons and surfaces a readiness
check for the health endpoint.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from ml._paths import CLUB_FIT_CONFIG, MODELS_DIR

log = logging.getLogger("scoutos.ml")
ART = MODELS_DIR


@lru_cache(maxsize=1)
def position_models():
    """(role_model, role_meta, side_model, side_meta) from ml.models.position."""
    from ml.models.position import load_model

    role = load_model("role")
    side = load_model("side")
    return {"role": role, "side": side}


@lru_cache(maxsize=1)
def club_fit_engine():
    from ml.models.club_fit import ClubFitEngine

    return ClubFitEngine()


def warmup() -> None:
    """Load models + FAISS indexes into memory at startup (best-effort).

    A missing/failed model logs a warning rather than crashing boot — the
    matching endpoint will surface the error when actually called.
    """
    steps = {
        "position": position_models,
        "club_fit": club_fit_engine,
        "similarity_current": lambda: _warm_similarity("current"),
        "similarity_career": lambda: _warm_similarity("career"),
    }
    for name, fn in steps.items():
        try:
            fn()
            log.info("warmup: %s ready", name)
        except Exception as exc:  # noqa: BLE001
            log.warning("warmup: %s unavailable (%s)", name, exc)


def _warm_similarity(mode: str):
    from ml.models.similarity import _load_mode

    return _load_mode(mode)


def available() -> dict[str, bool]:
    """Which model artifacts are present on disk (for /health/models)."""
    return {
        "value": (ART / "value_v1" / "model.txt").exists(),
        "potential": (ART / "potential_v1" / "model_h3.txt").exists(),
        "position_role": (ART / "position_v1" / "model.cbm").exists(),
        "position_side": (ART / "position_side_v1" / "model.cbm").exists(),
        "similarity": (ART / "similarity_v1" / "season_index.faiss").exists(),
        "club_fit": CLUB_FIT_CONFIG.exists(),
    }
