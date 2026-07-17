"""Scout OS backend package.

The serving layer lazily imports the repo-root packages `ml`/`etl`. Bootstrap the
repo root onto sys.path here so those imports resolve regardless of the launch
cwd or PYTHONPATH (previously a wrong cwd surfaced as a runtime "No module named
'ml'"). This runs for ANY entry into the `app` package — uvicorn's `app.main:app`,
pytest, or a direct `app.ml.*` import.

Artifact/config/.env paths are anchored to the repo root explicitly (ml/_paths.py
and config._ENV_FILE), so — unlike an os.chdir — this doesn't disturb tools that
rely on the real cwd (e.g. alembic resolving backend/alembic.ini).
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
