from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from onecmcp import __version__

DEMO_ID_ROMA = "8a996f93-36c8-4bcf-b707-f75b8b4bc5e3"
DEMO_ID_IVAN = "caf2ddab-572b-4ea9-b84f-ca4006dcb864"

DEMO_CATALOG: dict[str, Any] = {
    "kind": "catalog",
    "name": "DemoCounterparties",
    "synonym": "Демо-контрагенты",
    "description": "Фикстура стенда 1cmcp. Не объект типовой конфигурации.",
    "examples": ["ООО Ромашка", "ИП Иванов"],
    "fields": [
        {
            "name": "Description",
            "synonym": "Наименование",
            "type": "string",
            "required": True,
            "examples": ["ООО Ромашка"],
        },
        {
            "name": "INN",
            "synonym": "ИНН",
            "type": "string",
            "required": False,
            "description": "Идентификационный номер налогоплательщика",
            "examples": ["7701234567"],
        },
    ],
    "tabular_sections": [],
    "json_schema": {
        "type": "object",
        "properties": {
            "Description": {"type": "string"},
            "INN": {"type": "string"},
        },
        "required": ["Description"],
    },
}

DEMO_ITEMS: dict[str, dict[str, Any]] = {
    DEMO_ID_ROMA: {
        "id": DEMO_ID_ROMA,
        "ref": {
            "ref": "Catalog.DemoCounterparties",
            "id": DEMO_ID_ROMA,
            "presentation": "ООО Ромашка",
        },
        "Description": "ООО Ромашка",
        "INN": "7701234567",
    },
    DEMO_ID_IVAN: {
        "id": DEMO_ID_IVAN,
        "ref": {
            "ref": "Catalog.DemoCounterparties",
            "id": DEMO_ID_IVAN,
            "presentation": "ИП Иванов",
        },
        "Description": "ИП Иванов",
        "INN": "5001098765",
    },
}


def problem(status: int, code: str, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"https://1cmcp.dev/errors/{code}",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
        },
    )


def data_headers() -> dict[str, str]:
    return {"X-1cmcp-Content-Kind": "data"}


def create_mock_app() -> FastAPI:
    app = FastAPI(title="1cmcp mock adapter", version=__version__)

    @app.get("/v1/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "1cmcp",
            "version": __version__,
            "api": "v1",
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    @app.get("/v1/meta")
    async def list_meta(
        kind: str | None = None,
        limit: int = Query(default=50, ge=1, le=500),
        cursor: str | None = None,  # noqa: ARG001
    ) -> JSONResponse:
        items = [DEMO_CATALOG]
        if kind and kind != "catalog":
            items = []
        body = {"items": [_summary(item) for item in items[:limit]], "next_cursor": None, "has_more": False}
        return JSONResponse(body, headers=data_headers())

    @app.get("/v1/meta/search")
    async def search_meta(
        q: str = Query(min_length=1, max_length=200),
        limit: int = Query(default=20, ge=1, le=500),
    ) -> JSONResponse:
        needle = q.casefold()
        haystack = " ".join(
            [
                DEMO_CATALOG["name"],
                DEMO_CATALOG["synonym"],
                DEMO_CATALOG["description"],
                *DEMO_CATALOG["examples"],
                "контрагент",
                "counterparty",
            ]
        ).casefold()
        items = [_summary(DEMO_CATALOG)] if needle in haystack else []
        return JSONResponse(
            {"query": q, "items": items[:limit]},
            headers=data_headers(),
        )

    @app.get("/v1/meta/{kind}/{name}")
    async def describe_meta(kind: str, name: str) -> JSONResponse:
        if kind == DEMO_CATALOG["kind"] and name == DEMO_CATALOG["name"]:
            return JSONResponse(DEMO_CATALOG, headers=data_headers())
        return problem(404, "not_found", "Not found", f"Нет объекта {kind}/{name}")

    @app.get("/v1/data/{kind}/{name}")
    async def list_data(
        kind: str,
        name: str,
        limit: int = Query(default=50, ge=1, le=500),
        cursor: str | None = None,  # noqa: ARG001
    ) -> JSONResponse:
        if kind != "catalog" or name != DEMO_CATALOG["name"]:
            return problem(404, "not_found", "Not found", f"Нет выборки {kind}/{name}")
        items = list(DEMO_ITEMS.values())[:limit]
        return JSONResponse(
            {
                "content_kind": "data",
                "kind": kind,
                "name": name,
                "items": items,
                "next_cursor": None,
                "has_more": False,
            },
            headers=data_headers(),
        )

    @app.get("/v1/data/{kind}/{name}/{item_id}")
    async def get_data(kind: str, name: str, item_id: str) -> JSONResponse:
        if kind != "catalog" or name != DEMO_CATALOG["name"] or item_id not in DEMO_ITEMS:
            return problem(404, "not_found", "Not found", "Объект не найден")
        return JSONResponse(
            {
                "content_kind": "data",
                "kind": kind,
                "name": name,
                "item": DEMO_ITEMS[item_id],
            },
            headers=data_headers(),
        )

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def not_implemented(path: str, request: Request) -> JSONResponse:  # noqa: ARG001
        return problem(
            501,
            "not_implemented",
            "Not implemented",
            "Операция описана в контракте v1 и будет реализована в следующей фазе.",
        )

    return app


def _summary(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": obj["kind"],
        "name": obj["name"],
        "synonym": obj.get("synonym"),
        "description": obj.get("description"),
        "examples": obj.get("examples", []),
    }
