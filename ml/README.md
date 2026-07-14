# Scout OS — Machine Learning (Phase 3 & 4)

Feature engineering and the five models. Nothing implemented yet.

Planned models:
- **Similarity** — PyTorch autoencoder + FAISS
- **Market value** — LightGBM regression + SHAP
- **Position** — CatBoost classifier
- **Potential growth** — LightGBM regression (+1y/+3y/+5y)
- **Club fit** — weighted scoring (no ML)

Trained artifacts are written to `ml/models/` (gitignored) with a registry
manifest recording version, metrics, and feature-set version.
