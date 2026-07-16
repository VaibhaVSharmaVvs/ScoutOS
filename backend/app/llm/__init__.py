"""LLM explanation layer (Phase 6).

HARD RULE (from the proposal): the LLM never predicts — it only narrates model
outputs. Everything it says must trace back to a model output or a DB fact that
we put in its context. This package assembles that grounded context, renders a
low-temperature prompt, and returns a scout-style narrative.
"""
