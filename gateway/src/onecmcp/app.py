from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from onecmcp import __version__
from onecmcp.config import Settings
from onecmcp.diag import build_gateway_diag
from onecmcp.limits import RateLimiter, request_limit_key
from onecmcp.mcp_server import create_mcp
from onecmcp.presets import list_scenario_catalog, scenario_guide
from onecmcp.tenants import AdapterPool, UnknownTenant
from onecmcp.tracing import configure_tracing, http_span

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

PROBE_PATHS = {"/health", "/ready"}


def _openapi_path() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "specs" / "openapi.yaml",
        here.parents[2] / "specs" / "openapi.yaml",
        Path("/app/specs/openapi.yaml"),
        Path.cwd() / "specs" / "openapi.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _problem(status: int, code: str, title: str, detail: str, *, retry_after: float | None = None) -> JSONResponse:
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(max(1, int(retry_after)))
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
        content={
            "type": f"https://1cmcp.dev/errors/{code}",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
        },
    )


def create_app(
    settings: Settings | None = None,
    *,
    adapter_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or Settings()
    configure_tracing(settings)
    limiter = RateLimiter(settings.rate_limit_per_minute)
    mcp = create_mcp(settings)
    mcp_http = mcp.streamable_http_app(streamable_http_path="/")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        pool = AdapterPool(settings, transport=adapter_transport)
        app.state.adapters = pool
        app.state.onec = pool.client(settings.tenant)
        app.state.settings = settings
        try:
            async with mcp_http.router.lifespan_context(mcp_http):
                yield
        finally:
            await pool.aclose()

    app = FastAPI(
        title="1cmcp gateway",
        version=__version__,
        lifespan=lifespan,
        description="Слой B: REST-проекция v1, MCP streamable HTTP на /mcp, лимиты и тенанты.",
    )

    @app.middleware("http")
    async def observe_and_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        tenant = request.headers.get("x-tenant") or settings.tenant
        path = request.url.path
        with http_span(request.method, path, tenant):
            if path.rstrip("/") not in PROBE_PATHS and path != "/":
                allowed, retry_after = limiter.allow(request_limit_key(request))
                if not allowed:
                    return _problem(
                        429,
                        "rate_limited",
                        "Too Many Requests",
                        "Превышен лимит запросов шлюза",
                        retry_after=retry_after,
                    )
            return await call_next(request)

    @app.get("/health")
    async def gateway_health() -> dict[str, str]:
        return {"status": "ok", "service": "1cmcp-gateway", "version": __version__}

    @app.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        pool: AdapterPool = request.app.state.adapters
        try:
            payload = await pool.client(settings.tenant).health()
        except Exception as exc:  # noqa: BLE001
            return _problem(503, "adapter_unavailable", "Adapter unavailable", str(exc))
        return JSONResponse({"status": "ok", "adapter": payload})

    @app.get("/diag")
    async def gateway_diag(request: Request) -> JSONResponse:
        pool: AdapterPool = request.app.state.adapters
        try:
            adapter = await pool.client(settings.tenant).diag()
            payload = build_gateway_diag(settings, adapter=adapter)
        except Exception as exc:  # noqa: BLE001
            payload = build_gateway_diag(settings, adapter_error=str(exc))
        return JSONResponse(payload)

    @app.get("/guide")
    async def gateway_guide(request: Request, q: str | None = None) -> dict:
        if q is None or not str(q).strip():
            return list_scenario_catalog(settings.onec_preset)
        return scenario_guide(q, settings.onec_preset)

    @app.get("/openapi.yaml")
    async def openapi_yaml() -> FileResponse:
        path = _openapi_path()
        return FileResponse(path, media_type="application/yaml")

    async def _proxy(path: str, request: Request, tenant: str | None) -> Response:
        pool: AdapterPool = request.app.state.adapters
        try:
            client = pool.client(tenant)
        except UnknownTenant as exc:
            return _problem(
                404,
                "unknown_tenant",
                "Unknown tenant",
                f"Неизвестный тенант {exc.args[0]!s}",
            )
        body = await request.body()
        forwarded = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in HOP_BY_HOP
        }
        forwarded["X-Tenant"] = pool.resolve(tenant)
        upstream = await client.request(
            request.method,
            f"/v1/{path}",
            params=dict(request.query_params),
            headers=forwarded,
            content=body or None,
        )
        response_headers = {
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in HOP_BY_HOP
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type"),
        )

    @app.api_route("/t/{tenant}/v1/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def proxy_tenant_v1(tenant: str, path: str, request: Request) -> Response:
        return await _proxy(path, request, tenant)

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def proxy_v1(path: str, request: Request) -> Response:
        return await _proxy(path, request, request.headers.get("x-tenant"))

    app.mount(settings.mcp_http_path or "/mcp", mcp_http)
    return app
