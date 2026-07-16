"""LLM client with two providers, chosen automatically:

- anthropic : used when ANTHROPIC_API_KEY is set (real Claude call, low temp).
- stub      : deterministic, no-network fallback that renders the grounded
              context into a readable narrative. Lets the whole pipeline (context
              building, caching, endpoints) run and be tested without a key, and
              keeps the frontend unblocked. Clearly flags itself as non-LLM.

Both return (narrative_text, provider_name).
"""

from __future__ import annotations

import logging

from app.config import get_settings

log = logging.getLogger("scoutos.llm")


def provider_name() -> str:
    return "anthropic" if get_settings().anthropic_api_key else "stub"


def generate(system: str, user: str) -> tuple[str, str]:
    s = get_settings()
    if s.anthropic_api_key:
        try:
            return _anthropic(system, user, s), "anthropic"
        except Exception as exc:  # noqa: BLE001 - fall back rather than 500
            log.warning("anthropic call failed, using stub: %s", exc)
            return _stub(user), "stub-fallback"
    return _stub(user), "stub"


def _anthropic(system: str, user: str, s) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    msg = client.messages.create(
        model=s.llm_model,
        max_tokens=s.llm_max_tokens,
        temperature=s.llm_temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in msg.content if block.type == "text").strip()


def _stub(user: str) -> str:
    """Deterministic narrative from the grounded facts embedded in the prompt.

    Not an LLM — it just surfaces the context so the pipeline is exercisable
    offline. Prefixed so nobody mistakes it for a real explanation.
    """
    lines = [ln.strip() for ln in user.splitlines() if ln.strip().startswith("- ")]
    facts = " ".join(ln[2:] for ln in lines[:8])
    return f"[stub explanation — no ANTHROPIC_API_KEY configured] {facts}".strip()
