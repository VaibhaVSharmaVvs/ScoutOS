# Data

- `raw/` — untouched downloads per source (`fbref/`, `statsbomb/`, `understat/`,
  `transfermarkt/`). **Gitignored** — contains PII (player names, DOB,
  nationality). Never commit or share externally per SOC2/ISO 27001.
- `staging/` — intermediate transform outputs (gitignored).
- `processed/` — final feature tables before DB load (gitignored).
