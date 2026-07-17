"""Repo-root-anchored paths for ml artifacts and config.

The ml modules read/write artifacts and config by path. Anchoring them to the
repo root (computed from this file's location) makes them resolve regardless of
the process's current working directory — no chdir, no PYTHONPATH assumptions.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]  # ml/_paths.py -> ml -> repo root
ARTIFACTS = REPO_ROOT / "ml" / "artifacts"
MODELS_DIR = ARTIFACTS / "models"
CLUB_FIT_CONFIG = REPO_ROOT / "config" / "club_fit_weights.json"
