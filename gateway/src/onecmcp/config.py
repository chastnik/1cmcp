from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    onec_base_url: str = "http://127.0.0.1:18080"
    onec_token: str = ""
    onec_timeout_seconds: float = 30.0
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    tenant: str = "default"
    meta_cache_ttl_seconds: float = 60.0


def load_settings() -> Settings:
    return Settings()
