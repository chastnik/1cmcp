from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from typing import Any

from onecmcp.config import Settings, parse_tenant_map

STORE_NAME = "console.json"
PBKDF2_ROUNDS = 120_000
OPERATIONAL = (
    "onec_base_url",
    "onec_token",
    "onec_timeout_seconds",
    "tenant",
    "onec_tenants",
    "meta_cache_ttl_seconds",
    "onec_preset",
    "rate_limit_per_minute",
    "otel_exporter_otlp_endpoint",
    "mcp_http_path",
)


def store_path(data_dir: str) -> Path:
    return Path(data_dir).expanduser() / STORE_NAME


def empty_store() -> dict[str, Any]:
    return {"settings": {}, "bases": [], "operators": []}


def read_store(data_dir: str) -> dict[str, Any]:
    if not data_dir:
        return empty_store()
    path = store_path(data_dir)
    if not path.is_file():
        return empty_store()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return empty_store()
    loaded.setdefault("settings", {})
    loaded.setdefault("bases", [])
    loaded.setdefault("operators", [])
    return loaded


def write_store(data_dir: str, payload: dict[str, Any]) -> None:
    if not data_dir:
        raise ValueError("GATEWAY_DATA_DIR не задан")
    path = store_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def hash_password(password: str, *, salt: str | None = None) -> str:
    raw_salt = salt.encode("utf-8") if salt else secrets.token_bytes(16)
    if salt is None:
        salt_hex = raw_salt.hex()
        salt_bytes = raw_salt
    else:
        salt_hex = salt
        salt_bytes = bytes.fromhex(salt) if re.fullmatch(r"[0-9a-f]+", salt) else salt.encode("utf-8")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ROUNDS)
    return f"{salt_hex}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if "$" not in stored:
        return False
    salt, _digest = stored.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt=salt), stored)


def settings_from_bases(bases: list[dict[str, Any]], default_id: str) -> dict[str, Any]:
    if not bases:
        return {}
    chosen = next((item for item in bases if item.get("id") == default_id), bases[0])
    tenants = ",".join(
        f"{item['id']}={str(item.get('url') or '').rstrip('/')}"
        for item in bases
        if item.get("id") and item.get("url")
    )
    return {
        "tenant": str(chosen.get("id") or default_id),
        "onec_base_url": str(chosen.get("url") or "").rstrip("/"),
        "onec_token": str(chosen.get("token") or ""),
        "onec_tenants": tenants,
        "onec_timeout_seconds": float(chosen.get("timeout_seconds") or 30),
    }


def tenant_token_map(bases: list[dict[str, Any]], fallback: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in bases:
        key = str(item.get("id") or "").strip()
        if not key:
            continue
        mapping[key] = str(item.get("token") or fallback or "")
    return mapping


def apply_store(settings: Settings) -> Settings:
    data = read_store(settings.gateway_data_dir)
    payload = dict(data.get("settings") or {})
    update = {key: payload[key] for key in OPERATIONAL if key in payload}
    bases = list(data.get("bases") or [])
    if bases:
        update.update(settings_from_bases(bases, str(payload.get("tenant") or settings.tenant)))
    if not update:
        return settings
    return settings.model_copy(update=update)


def public_values(settings: Settings) -> dict[str, Any]:
    return {
        "onec_base_url": settings.onec_base_url,
        "onec_token_set": bool(settings.onec_token),
        "onec_timeout_seconds": settings.onec_timeout_seconds,
        "tenant": settings.tenant,
        "onec_tenants": settings.onec_tenants,
        "meta_cache_ttl_seconds": settings.meta_cache_ttl_seconds,
        "onec_preset": settings.onec_preset,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "otel_exporter_otlp_endpoint": settings.otel_exporter_otlp_endpoint,
        "mcp_http_path": settings.mcp_http_path,
        "gateway_host": settings.gateway_host,
        "gateway_port": settings.gateway_port,
        "gateway_data_dir": settings.gateway_data_dir,
        "admin_bootstrap_token_set": bool(settings.admin_bootstrap_token),
    }


def public_bases(bases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in bases:
        rows.append(
            {
                "id": item.get("id"),
                "url": item.get("url"),
                "timeout_seconds": item.get("timeout_seconds") or 30,
                "preset": item.get("preset") or "",
                "token_set": bool(item.get("token")),
            }
        )
    return rows


def seed_bases_from_settings(settings: Settings) -> list[dict[str, Any]]:
    data = read_store(settings.gateway_data_dir)
    stored = list(data.get("bases") or [])
    if stored:
        return stored
    mapping = parse_tenant_map(
        settings.onec_tenants,
        default_id=settings.tenant,
        default_url=settings.onec_base_url,
    )
    return [
        {
            "id": key,
            "url": url,
            "token": settings.onec_token if key == settings.tenant else "",
            "timeout_seconds": settings.onec_timeout_seconds,
            "preset": settings.onec_preset if key == settings.tenant else "",
        }
        for key, url in mapping.items()
    ]
