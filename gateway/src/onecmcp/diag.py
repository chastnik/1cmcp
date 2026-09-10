from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from onecmcp import __version__
from onecmcp.config import Settings

PRODUCT_LICENSE = "not_required"
COMPATIBILITY = {"platform": "8.3.20+", "modes": ["file", "client_server"]}


def adapter_host(base_url: str) -> str:
    return urlparse(base_url).hostname or ""


def build_adapter_diag(*, version: str, time: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "1cmcp",
        "version": version,
        "api": "v1",
        "time": time,
        "compatibility": dict(COMPATIBILITY),
        "publication": {
            "root_url": "mcp",
            "reuse_sessions": "AutoUse",
            "session_max_age": 20,
        },
        "product_license": PRODUCT_LICENSE,
        "checks": [
            {"id": "http_service", "ok": True, "detail": "RootURL mcp"},
            {"id": "session_reuse", "ok": True, "detail": "AutoUse, SessionMaxAge=20"},
            {"id": "role", "ok": True, "detail": "мкпДоступКоннектора"},
            {"id": "product_license", "ok": True, "detail": PRODUCT_LICENSE},
        ],
    }


def build_gateway_diag(
    settings: Settings,
    *,
    adapter: dict[str, Any] | None = None,
    adapter_error: str | None = None,
) -> dict[str, Any]:
    adapter_ok = adapter is not None and not adapter_error
    tenants = settings.tenant_map()
    return {
        "status": "ok" if adapter_ok else "degraded",
        "service": "1cmcp-gateway",
        "version": __version__,
        "api": "v1",
        "product_license": PRODUCT_LICENSE,
        "gateway": {
            "preset": settings.onec_preset,
            "meta_cache_ttl_seconds": settings.meta_cache_ttl_seconds,
            "tenant": settings.tenant,
            "adapter_host": adapter_host(settings.onec_base_url),
            "mcp_http_path": settings.mcp_http_path,
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "tenants": sorted(tenants),
        },
        "adapter": adapter,
        "checks": [
            {
                "id": "adapter_reachable",
                "ok": adapter_ok,
                "detail": "ok" if adapter_ok else (adapter_error or "adapter_unavailable"),
            },
            {"id": "product_license", "ok": True, "detail": PRODUCT_LICENSE},
            {
                "id": "mcp_http",
                "ok": True,
                "detail": settings.mcp_http_path,
            },
        ],
    }
