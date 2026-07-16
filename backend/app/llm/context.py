"""Grounded-context builders for the LLM layer.

Each function returns a plain dict of FACTS — every value is a model output or a
DB row, never an invented number. The prompt renderer turns these into bullet
lines; the LLM only narrates them. Model versions are stamped so cached
explanations invalidate when a model is retrained.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ml.features import latest_feature_row, position_frame
from app.ml.registry import club_fit_engine, position_models

# bump the relevant tag when a model is retrained -> caches regenerate
MODEL_VERSIONS = {
    "features": "v1", "value": "value_v1", "potential": "potential_v1",
    "position": "position_v1", "similarity": "similarity_v1", "club_fit": "cf_v1",
}


def _eur(x) -> float | None:
    return None if x is None else round(float(x))


def _bio(db: Session, player_id: int) -> dict | None:
    row = db.execute(text(
        "select id, full_name, primary_position, nationality, foot, height_cm, "
        "date_part('year', age(current_date, date_of_birth)) as age "
        "from players where id=:pid"), {"pid": player_id}).mappings().first()
    if row is None:
        return None
    cur = db.execute(text(
        "select value_eur from market_values where player_id=:pid "
        "order by as_of desc limit 1"), {"pid": player_id}).scalar()
    return {"player_id": row["id"], "name": row["full_name"],
            "listed_position": row["primary_position"], "nationality": row["nationality"],
            "foot": row["foot"], "height_cm": row["height_cm"],
            "age": int(row["age"]) if row["age"] is not None else None,
            "current_market_value_eur": _eur(cur)}


def player_report_facts(db: Session, player_id: int) -> dict | None:
    """Full scouting context: bio + value + potential + position + top similar."""
    from ml.models.explain import explain_potential, explain_value
    from ml.models.similarity import find_similar

    bio = _bio(db, player_id)
    row = latest_feature_row(player_id)
    if bio is None or row is None:
        return None

    facts: dict = {"bio": bio, "season": row["season"],
                   "model_versions": MODEL_VERSIONS}

    val = explain_value(row)
    facts["value_model"] = {"predicted_value_eur": val["predicted_value_eur"],
                            "top_drivers": val["drivers"][:5]}
    if row.get("cur_value_log") is not None:
        pot = explain_potential(row, horizon=3)
        facts["potential_model"] = {"horizon_years": 3,
                                    "projected_value_eur": pot["predicted_value_eur"],
                                    "top_drivers": pot["drivers"][:4]}

    role_model, role_meta = position_models()["role"]
    from ml.models.position import predict_positions
    pos = predict_positions(role_model, role_meta, position_frame(row, role_meta))[0]
    facts["position_model"] = {"primary": pos["primary"], "secondary": pos["secondary"],
                               "playable": pos["playable"],
                               "top_probabilities": dict(list(pos["probs"].items())[:3])}

    sims = find_similar(player_id, k=5, mode="current")
    facts["similar_players"] = [{"name": s["player"], "similarity": s["similarity"]}
                                for s in sims]
    return facts


def club_fit_facts(player_id: int, club_id: int) -> dict | None:
    engine = club_fit_engine()
    res = engine.score(player_id, club_id)
    if res is None:
        return None
    return {"player": res["player"], "club": res["club"],
            "model_versions": {"club_fit": MODEL_VERSIONS["club_fit"]},
            "sub_scores": {"tactical": res["tactical_fit"], "squad": res["squad_fit"],
                           "financial": res["financial_fit"], "age": res["age_fit"]},
            "overall_fit": res["overall_fit"]}


def comparison_facts(db: Session, player_id: int, other_id: int) -> dict | None:
    from ml.models.explain import _shared_traits, _style_vectors

    a_bio, b_bio = _bio(db, player_id), _bio(db, other_id)
    if a_bio is None or b_bio is None:
        return None
    names, vecs = _style_vectors("v1")
    va, vb = vecs.get(player_id), vecs.get(other_id)
    traits = _shared_traits(va, vb, names) if (va is not None and vb is not None) else []
    # similarity score if the other player is in this player's neighbour list
    from ml.models.similarity import find_similar
    sim = next((s["similarity"] for s in find_similar(player_id, k=250, mode="current")
                if s["player_id"] == other_id), None)
    return {"player_a": a_bio, "player_b": b_bio,
            "model_versions": {"similarity": MODEL_VERSIONS["similarity"]},
            "similarity": sim, "shared_style_traits": [t["label"] for t in traits]}
