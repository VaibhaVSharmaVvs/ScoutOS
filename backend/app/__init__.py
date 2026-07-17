"""Scout OS backend package.

The backend has a "run from the repo root" contract: the serving layer lazily
imports the repo-root packages `ml`/`etl`, and the ml modules read repo-root-
relative paths (`ml/artifacts/...`, `config/club_fit_weights.json`), while
settings read `.env` at the repo root. Launched from anywhere else, imports fail
("No module named 'ml'"), artifacts aren't found, and — most insidiously — the
DB URL silently falls back to the default (:5432) instead of the repo `.env`
(:5433).

To make the process behave identically no matter the launch cwd, we bootstrap
the repo root onto sys.path and chdir to it here — this runs for ANY entry into
the `app` package (uvicorn's `app.main:app`, pytest, or a direct `app.ml.*`
import). Docker (Phase 8) sets WORKDIR to the repo root, matching this.
"""

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if (_REPO_ROOT / "ml").is_dir() and Path.cwd() != _REPO_ROOT:
    os.chdir(_REPO_ROOT)
