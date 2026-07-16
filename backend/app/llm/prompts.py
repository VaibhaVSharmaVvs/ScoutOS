"""Prompt templates. The system prompt encodes the hard guardrails; per-kind
renderers turn a grounded facts dict into '- fact' bullet lines (the only things
the model may talk about).
"""

from __future__ import annotations

SYSTEM = (
    "You are an expert football (soccer) scout writing concise, professional "
    "assessments for a recruitment team.\n"
    "STRICT RULES:\n"
    "1. Every number and claim you make MUST come from the FACTS provided. Never "
    "invent statistics, values, clubs, or comparisons.\n"
    "2. The predictions and scores in the FACTS were computed by our models — you "
    "EXPLAIN them, you never predict or recompute. Do not second-guess the numbers.\n"
    "3. If a fact is not provided, do not mention it. No hedging filler.\n"
    "4. Write in plain scout language: what the numbers mean for recruitment. "
    "Reference the model's driving factors when explaining a value/potential.\n"
    "5. Keep it tight — a few short paragraphs, no bullet lists in the output."
)


def _money(v) -> str:
    return f"€{v/1e6:.1f}M" if isinstance(v, (int, float)) else "unknown"


def _drivers(ds) -> str:
    return "; ".join(f"{d['label']} ({d['effect']})" for d in ds)


def render_report(f: dict) -> str:
    b = f["bio"]
    lines = [
        f"- Player: {b['name']}, age {b['age']}, {b.get('nationality') or 'unknown nationality'}, "
        f"{b.get('foot') or 'unknown'}-footed, listed as {b.get('listed_position') or 'n/a'}.",
        f"- Season analysed: {f['season']}. "
        f"Current market value: {_money(b['current_market_value_eur'])}.",
        f"- Model-predicted market value: {_money(f['value_model']['predicted_value_eur'])}. "
        f"Top drivers: {_drivers(f['value_model']['top_drivers'])}.",
    ]
    if "potential_model" in f:
        p = f["potential_model"]
        lines.append(f"- Potential (+{p['horizon_years']}yr) projected value: "
                     f"{_money(p['projected_value_eur'])}. Drivers: {_drivers(p['top_drivers'])}.")
    pos = f["position_model"]
    lines.append(f"- Model role: primary {pos['primary']}, secondary {pos['secondary']}; "
                 f"playable: {', '.join(pos['playable'])}.")
    if f.get("similar_players"):
        sims = ", ".join(f"{s['name']} ({s['similarity']:.2f})" for s in f["similar_players"])
        lines.append(f"- Stylistically similar players: {sims}.")
    body = "\n".join(lines)
    return (f"Write a scouting report for this player, explaining what the model "
            f"outputs mean for recruitment.\n\nFACTS:\n{body}")


def render_club_fit(f: dict) -> str:
    s = f["sub_scores"]
    body = "\n".join([
        f"- Assessing fit of {f['player']} at {f['club']}.",
        f"- Overall fit score: {f['overall_fit']}/100.",
        f"- Tactical fit: {s['tactical']}/100 (playing-style match).",
        f"- Squad-need fit: {s['squad']}/100 (positional depth need).",
        f"- Financial fit: {s['financial']}/100 (value vs the club's spending level).",
        f"- Age fit: {s['age']}/100 (vs the club's age profile).",
    ])
    return (f"Explain how well this player fits this club, using the sub-scores. "
            f"Call out the strongest and weakest dimensions.\n\nFACTS:\n{body}")


def render_comparison(f: dict) -> str:
    a, b = f["player_a"], f["player_b"]
    lines = [
        f"- Comparing {a['name']} (age {a['age']}, {a.get('listed_position') or 'n/a'}) "
        f"with {b['name']} (age {b['age']}, {b.get('listed_position') or 'n/a'}).",
        f"- {a['name']} value: {_money(a['current_market_value_eur'])}; "
        f"{b['name']} value: {_money(b['current_market_value_eur'])}.",
    ]
    if f.get("similarity") is not None:
        lines.append(f"- Model style-similarity score: {f['similarity']:.2f} "
                     f"(1.0 = identical style).")
    if f.get("shared_style_traits"):
        lines.append(f"- Shared standout style traits: {', '.join(f['shared_style_traits'])}.")
    body = "\n".join(lines)
    return (f"Compare these two players' playing styles using the similarity output "
            f"and shared traits.\n\nFACTS:\n{body}")


RENDERERS = {"report": render_report, "club_fit": render_club_fit, "comparison": render_comparison}
