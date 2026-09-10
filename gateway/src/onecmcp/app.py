from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from onecmcp import __version__
from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.diag import build_gateway_diag
from onecmcp.presets import list_scenario_catalog, scenario_guide

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


def create_app(
    settings: Settings | None = None,
    *,
    adapter_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = OneCClient(settings, transport=adapter_transport)
        app.state.onec = client
        app.state.settings = settings
        try:
            yield
        finally:
            await client.aclose()

    app = FastAPI(
        title="1cmcp gateway",
        version=__version__,
        lifespan=lifespan,
        description="Слой B: REST-проекция контракта v1. MCP — отдельный процесс stdio.",
    )

    @app.get("/health")
    async def gateway_health() -> dict[str, str]:
        return {"status": "ok", "service": "1cmcp-gateway", "version": __version__}

    @app.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        client: OneCClient = request.app.state.onec
        try:
            payload = await client.health()
        except Exception as exc:  # noqa: BLE001
            return JSONResponse(
                status_code=503,
                media_type="application/problem+json",
                content={
                    "type": "https://1cmcp.dev/errors/adapter_unavailable",
                    "title": "Adapter unavailable",
                    "status": 503,
                    "code": "adapter_unavailable",
                    "detail": str(exc),
                },
            )
        return JSONResponse({"status": "ok", "adapter": payload})

    @app.get("/diag")
    async def gateway_diag(request: Request) -> JSONResponse:
        client: OneCClient = request.app.state.onec
        settings: Settings = request.app.state.settings
        try:
            adapter = await client.diag()
            payload = build_gateway_diag(settings, adapter=adapter)
        except Exception as exc:  # noqa: BLE001
            payload = build_gateway_diag(settings, adapter_error=str(exc))
        return JSONResponse(payload)

    @app.get("/guide")
    async def gateway_guide(request: Request, q: str | None = None) -> dict:
        settings: Settings = request.app.state.settings
        if q is None or not str(q).strip():
            return list_scenario_catalog(settings.onec_preset)
        return scenario_guide(q, settings.onec_preset)

    @app.get("/openapi.yaml")
    async def openapi_yaml() -> FileResponse:
        path = _openapi_path()
        return FileResponse(path, media_type="application/yaml")

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def proxy_v1(path: str, request: Request) -> Response:
        client: OneCClient = request.app.state.onec
        body = await request.body()
        forwarded = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in HOP_BY_HOP
        }
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

    return app
