"""Model-serving layer: loads Phase 4 artifacts and builds prediction inputs.

The heavy ML packages (lightgbm, catboost, torch, faiss, shap) are imported
lazily inside the registry so the API process only pays for a model the first
time an endpoint needs it. Everything here assumes the process runs from the
repo root (artifact paths like ``ml/artifacts/...`` are repo-relative).
"""
