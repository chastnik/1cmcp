from __future__ import annotations

import json

from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_tenant_map(raw: str, *, default_id: str, default_url: str) -> dict[str, str]:
    """Карта тенант → URL слоя A. CSV `id=url,id2=url2` или JSON-объект."""
    mapping = {default_id: default_url.rstrip("/")}
    text = (raw or "").strip()
    if not text:
        return mapping
    if text.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("ONEC_TENANTS: JSON должен быть объектом id→url")
        for key, value in data.items():
            mapping[str(key)] = str(value).rstrip("/")
        return mapping
    for part in text.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"ONEC_TENANTS: ожидается id=url, получено {chunk!r}")
        tenant_id, url = chunk.split("=", 1)
        mapping[tenant_id.strip()] = url.strip().rstrip("/")
    return mapping


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
    onec_tenants: str = ""
    meta_cache_ttl_seconds: float = 60.0
    onec_preset: str = "auto"
    rate_limit_per_minute: int = 120
    otel_exporter_otlp_endpoint: str = ""
    mcp_http_path: str = "/mcp"

    def tenant_map(self) -> dict[str, str]:
        return parse_tenant_map(
            self.onec_tenants,
            default_id=self.tenant,
            default_url=self.onec_base_url,
        )


def load_settings() -> Settings:
    return Settings()
