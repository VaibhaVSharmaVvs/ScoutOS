"""Orchestrates the explanation pipeline: build grounded facts -> render prompt
-> (Redis cache, version-keyed) -> LLM -> narrative.

The cache key embeds the model versions and the LLM model, so an explanation is
reused until a model is retrained or the LLM is swapped — then it regenerates.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
from sqlalchemy.orm import Session

from app.cache import get_bytes, set_bytes
from app.config import get_settings
from app.llm import context as ctx
from app.llm import prompts
from app.llm.client import generate


def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _to_native(obj):
    """Strip numpy/pandas scalar types so the facts dict is JSON-serializable
    (FastAPI's response serializer rejects numpy.int64/float64)."""
    return json.loads(json.dumps(obj, default=_json_default))


def _version_tag(facts: dict) -> str:
    versions = facts.get("model_versions", {})
    payload = json.dumps(versions, sort_keys=True) + "|" + get_settings().llm_model
    return hashlib.sha1(payload.encode()).hexdigest()[:10]


def _run(kind: str, ident: str, facts: dict) -> dict:
    key = f"llm:{kind}:{ident}:{_version_tag(facts)}"
    hit = get_bytes(key)
    if hit is not None:
        out = json.loads(hit)
        out["cached"] = True
        return out

    user = prompts.RENDERERS[kind](facts)
    narrative, provider = generate(prompts.SYSTEM, user)
    out = {"kind": kind, "narrative": narrative, "provider": provider,
           "grounding": _to_native(facts), "cached": False}
    set_bytes(key, json.dumps(out, default=str).encode(), ttl=get_settings().llm_cache_ttl)
    return out


def explain_report(db: Session, player_id: int) -> dict | None:
    facts = ctx.player_report_facts(db, player_id)
    return None if facts is None else _run("report", str(player_id), facts)


def explain_club_fit(player_id: int, club_id: int) -> dict | None:
    facts = ctx.club_fit_facts(player_id, club_id)
    return None if facts is None else _run("club_fit", f"{player_id}-{club_id}", facts)


def explain_comparison(db: Session, player_id: int, other_id: int) -> dict | None:
    facts = ctx.comparison_facts(db, player_id, other_id)
    return None if facts is None else _run("comparison", f"{player_id}-{other_id}", facts)
