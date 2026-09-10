from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from onecmcp import __version__
from onecmcp.config import Settings
from onecmcp.console_docs import docs_root, markdown_to_html, resolve_doc
from onecmcp.console_meta import DOCS_PAGES, SETTINGS_FIELDS
from onecmcp.limits import RateLimiter
from onecmcp.mcp_server import create_mcp
from onecmcp.store import (
    apply_store,
    hash_password,
    public_bases,
    public_values,
    read_store,
    seed_bases_from_settings,
    tenant_token_map,
    verify_password,
    write_store,
)
from onecmcp.tenants import AdapterPool


def static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


def _problem(status: int, code: str, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"https://1cmcp.dev/errors/{code}",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
        },
    )


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


def _authorized(request: Request, settings: Settings) -> bool:
    token = _bearer(request)
    if not token:
        return False
    expected = settings.admin_bootstrap_token
    if expected and secrets.compare_digest(token, expected):
        return True
    sessions: dict[str, str] = request.app.state.console_sessions
    return token in sessions


def _guard(request: Request, settings: Settings) -> JSONResponse | None:
    if _authorized(request, settings):
        return None
    return _problem(401, "unauthorized", "Unauthorized", "Нужен токен первого входа или сессия оператора")


def _openapi_file() -> Path:
    here = Path(__file__).resolve()
    candidates = [parent / "specs" / "openapi.yaml" for parent in here.parents]
    candidates.extend([Path("/app/specs/openapi.yaml"), Path.cwd() / "specs" / "openapi.yaml"])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return Path("/app/specs/openapi.yaml")


def _rest_catalog() -> list[dict[str, str]]:
    path = _openapi_file()
    if not path.is_file():
        return []
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items: list[dict[str, str]] = []
    for url, ops in (spec.get("paths") or {}).items():
        if not isinstance(ops, dict):
            continue
        for method, body in ops.items():
            if method.startswith("x-") or not isinstance(body, dict):
                continue
            items.append(
                {
                    "method": method.upper(),
                    "path": url,
                    "summary": str(body.get("summary") or body.get("operationId") or ""),
                    "description": str(body.get("description") or "").strip(),
                    "scope": "read" if method.lower() == "get" else "",
                }
            )
    return items


def _mcp_catalog(settings: Settings) -> list[dict[str, str]]:
    server = create_mcp(settings)
    tools = []
    for tool in server._tool_manager.list_tools():
        tools.append(
            {
                "name": tool.name,
                "description": (getattr(tool, "description", None) or "").strip(),
            }
        )
    return tools


def mount_console(app: FastAPI, settings: Settings) -> None:
    assets = static_dir()
    app.state.console_sessions = {}
    app.state.settings = apply_store(settings)

    @app.get("/")
    async def console_home() -> FileResponse:
        return FileResponse(assets / "index.html", media_type="text/html; charset=utf-8")

    @app.get("/console")
    async def console_alias() -> FileResponse:
        return FileResponse(assets / "index.html", media_type="text/html; charset=utf-8")

    @app.get("/console/api/catalog")
    async def catalog() -> dict[str, Any]:
        current: Settings = app.state.settings
        return {
            "version": __version__,
            "rest": _rest_catalog(),
            "mcp": _mcp_catalog(current),
        }

    @app.get("/console/api/docs")
    async def docs_index() -> dict[str, Any]:
        root = docs_root()
        pages = []
        for page in DOCS_PAGES:
            path = root / page["file"]
            if path.is_file():
                pages.append(page)
        return {"pages": pages}

    @app.get("/console/api/docs/{doc_path:path}")
    async def docs_page(doc_path: str) -> JSONResponse:
        relative = doc_path if doc_path.endswith(".md") else f"{doc_path}.md"
        path = resolve_doc(relative)
        if path is None:
            return _problem(404, "not_found", "Not found", "Нет такой инструкции")
        markdown = path.read_text(encoding="utf-8")
        meta = next((page for page in DOCS_PAGES if page["file"] == relative), None)
        return JSONResponse(
            {
                "id": (meta or {}).get("id") or relative.removesuffix(".md"),
                "title": (meta or {}).get("title") or relative,
                "markdown": markdown,
                "html": markdown_to_html(markdown),
            }
        )

    @app.post("/console/api/login")
    async def login(request: Request) -> JSONResponse:
        current: Settings = app.state.settings
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        token = str(payload.get("token") or payload.get("access_token") or "")
        login_name = str(payload.get("login") or "").strip()
        password = str(payload.get("password") or "")
        if token and current.admin_bootstrap_token and secrets.compare_digest(
            token, current.admin_bootstrap_token
        ):
            session = secrets.token_urlsafe(32)
            app.state.console_sessions[session] = "bootstrap"
            return JSONResponse({"access_token": session, "role": "bootstrap"})
        store = read_store(current.gateway_data_dir)
        for operator in store.get("operators") or []:
            if operator.get("login") == login_name and verify_password(
                password, str(operator.get("password_hash") or "")
            ):
                session = secrets.token_urlsafe(32)
                app.state.console_sessions[session] = login_name
                return JSONResponse({"access_token": session, "role": "operator", "login": login_name})
        return _problem(401, "unauthorized", "Unauthorized", "Неверный логин, пароль или токен")

    @app.get("/console/api/settings")
    async def get_settings(request: Request) -> JSONResponse:
        denied = _guard(request, app.state.settings)
        if denied:
            return denied
        current: Settings = app.state.settings
        return JSONResponse({"fields": SETTINGS_FIELDS, "values": public_values(current)})

    @app.put("/console/api/settings")
    async def put_settings(request: Request) -> JSONResponse:
        denied = _guard(request, app.state.settings)
        if denied:
            return denied
        current: Settings = app.state.settings
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return _problem(400, "bad_request", "Bad request", "Нужен JSON-объект")
        if not isinstance(payload, dict):
            return _problem(400, "bad_request", "Bad request", "Нужен JSON-объект")
        store = read_store(current.gateway_data_dir)
        settings_payload = dict(store.get("settings") or {})
        allowed = {item["name"] for item in SETTINGS_FIELDS if item["source"] == "ui"}
        ints = {"rate_limit_per_minute"}
        floats = {"onec_timeout_seconds", "meta_cache_ttl_seconds"}
        for key, value in payload.items():
            if key not in allowed:
                continue
            if key == "onec_token" and value in {"", None, "сохранён"}:
                continue
            try:
                if key in ints:
                    value = int(value)
                elif key in floats:
                    value = float(value)
            except (TypeError, ValueError):
                return _problem(400, "bad_request", "Bad request", f"Поле {key} должно быть числом")
            settings_payload[key] = value
        store["settings"] = settings_payload
        write_store(current.gateway_data_dir, store)
        await reload_runtime(app, current)
        return JSONResponse({"fields": SETTINGS_FIELDS, "values": public_values(app.state.settings)})

    @app.get("/console/api/bases")
    async def get_bases(request: Request) -> JSONResponse:
        denied = _guard(request, app.state.settings)
        if denied:
            return denied
        current: Settings = app.state.settings
        bases = seed_bases_from_settings(current)
        return JSONResponse({"items": public_bases(bases), "default_id": current.tenant})

    @app.put("/console/api/bases")
    async def put_bases(request: Request) -> JSONResponse:
        denied = _guard(request, app.state.settings)
        if denied:
            return denied
        current: Settings = app.state.settings
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return _problem(400, "bad_request", "Bad request", "Нужен JSON-объект")
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items:
            return _problem(400, "bad_request", "Bad request", "Нужен непустой items")
        store = read_store(current.gateway_data_dir)
        previous = {str(item.get("id")): item for item in store.get("bases") or []}
        cleaned: list[dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, dict) or not raw.get("id") or not raw.get("url"):
                return _problem(400, "bad_request", "Bad request", "У базы нужны id и url")
            ident = str(raw["id"]).strip()
            token = raw.get("token")
            if not token:
                token = (previous.get(ident) or {}).get("token") or ""
            cleaned.append(
                {
                    "id": ident,
                    "url": str(raw["url"]).rstrip("/"),
                    "token": str(token or ""),
                    "timeout_seconds": float(raw.get("timeout_seconds") or current.onec_timeout_seconds),
                    "preset": str(raw.get("preset") or current.onec_preset),
                }
            )
        default_id = str(payload.get("default_id") or cleaned[0]["id"])
        store["bases"] = cleaned
        settings_payload = dict(store.get("settings") or {})
        settings_payload["tenant"] = default_id
        store["settings"] = settings_payload
        write_store(current.gateway_data_dir, store)
        await reload_runtime(app, current)
        current = app.state.settings
        return JSONResponse({"items": public_bases(cleaned), "default_id": current.tenant})

    @app.get("/console/api/operators")
    async def get_operators(request: Request) -> JSONResponse:
        denied = _guard(request, app.state.settings)
        if denied:
            return denied
        current: Settings = app.state.settings
        store = read_store(current.gateway_data_dir)
        logins = [{"login": item.get("login")} for item in store.get("operators") or []]
        return JSONResponse({"items": logins})

    @app.post("/console/api/operators")
    async def post_operator(request: Request) -> JSONResponse:
        denied = _guard(request, app.state.settings)
        if denied:
            return denied
        current: Settings = app.state.settings
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return _problem(400, "bad_request", "Bad request", "Нужен JSON-объект")
        login_name = str((payload or {}).get("login") or "").strip()
        password = str((payload or {}).get("password") or "")
        if len(login_name) < 2 or len(password) < 8:
            return _problem(400, "bad_request", "Bad request", "Логин от 2 символов, пароль от 8")
        store = read_store(current.gateway_data_dir)
        operators = list(store.get("operators") or [])
        if any(item.get("login") == login_name for item in operators):
            return _problem(409, "conflict", "Conflict", "Оператор уже есть")
        operators.append({"login": login_name, "password_hash": hash_password(password)})
        store["operators"] = operators
        write_store(current.gateway_data_dir, store)
        return JSONResponse({"login": login_name}, status_code=201)

    if (assets / "app.js").is_file():
        app.mount("/console/static", StaticFiles(directory=assets), name="console-static")


async def reload_runtime(app: FastAPI, previous: Settings) -> None:
    refreshed = apply_store(previous)
    app.state.settings = refreshed
    limiter: RateLimiter | None = getattr(app.state, "limiter", None)
    if limiter is not None:
        limiter.per_minute = refreshed.rate_limit_per_minute
    old_pool: AdapterPool | None = getattr(app.state, "adapters", None)
    tokens = tenant_token_map(
        read_store(refreshed.gateway_data_dir).get("bases") or [],
        refreshed.onec_token,
    )
    transport = getattr(old_pool, "_transport", None) if old_pool is not None else None
    pool = AdapterPool(refreshed, transport=transport, tokens=tokens)
    app.state.adapters = pool
    app.state.onec = pool.client(refreshed.tenant)
    if old_pool is not None:
        await old_pool.aclose()
