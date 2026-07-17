from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root; anchor to it so settings load regardless of cwd.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://scout:scout@localhost:5432/scoutos"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # WebAuthn / passkeys. rp_id = the site's registrable domain (no scheme/port);
    # origin must match the frontend exactly. Defaults suit local dev; override in
    # prod (e.g. rp_id="scoutos.app", origin="https://scoutos.app").
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Scout OS"
    webauthn_origin: str = "http://localhost:5173"

    # LLM explanation layer (Phase 6). Empty key -> deterministic stub narratives.
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 700
    llm_temperature: float = 0.2
    llm_cache_ttl: int = 86400  # explanations regenerate only when inputs change


@lru_cache
def get_settings() -> Settings:
    return Settings()
