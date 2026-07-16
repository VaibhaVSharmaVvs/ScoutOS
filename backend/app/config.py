from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str = "postgresql+psycopg://scout:scout@localhost:5432/scoutos"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # LLM explanation layer (Phase 6). Empty key -> deterministic stub narratives.
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 700
    llm_temperature: float = 0.2
    llm_cache_ttl: int = 86400  # explanations regenerate only when inputs change


@lru_cache
def get_settings() -> Settings:
    return Settings()
