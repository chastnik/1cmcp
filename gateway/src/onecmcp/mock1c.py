from __future__ import annotations

import copy
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from onecmcp import __version__
from onecmcp.diag import build_adapter_diag
from onecmcp.query_validator import QueryRejected, resolve_limit, validate_query_text
from onecmcp.writes import WriteEngine, fill_check, posting_check

DEV_TOKEN = "dev-token"
WRITE_ONLY_TOKEN = "write-only-token"
DENIED_SHIPMENTS_TOKEN = "deny-shipments-token"
WRITE_DEV_TOKEN = "dev-write-token"

DEMO_ID_ROMA = "8a996f93-36c8-4bcf-b707-f75b8b4bc5e3"
DEMO_ID_IVAN = "caf2ddab-572b-4ea9-b84f-ca4006dcb864"

SHIP_AUG_1 = "3c1a0e7a-6b21-4f3d-9c8a-1d2e3f4a5b60"
SHIP_AUG_2 = "7d4b2f91-8e55-4a12-b6c0-9a8b7c6d5e43"
SHIP_JULY = "e2f1d0c9-b8a7-4655-9432-1100aa99bb88"
SHIP_IVAN = "0f9e8d7c-6b5a-4c3b-9210-fedcba987654"

_CLIENTS: dict[str, dict[str, Any]] = {
    DEV_TOKEN: {"id": "dev", "scopes": ["read"], "acl": None},
    WRITE_ONLY_TOKEN: {"id": "writer", "scopes": ["write"], "acl": None},
    WRITE_DEV_TOKEN: {
        "id": "dev-writer",
        "scopes": ["read", "write"],
        "acl": {
            ("catalog", "DemoCounterparties"): True,
            ("document", "DemoShipments"): True,
        },
    },
    DENIED_SHIPMENTS_TOKEN: {
        "id": "limited",
        "scopes": ["read"],
        "acl": {
            ("catalog", "DemoCounterparties"): True,
            ("document", "DemoShipments"): False,
        },
    },
}

_CALL_LOG: list[dict[str, Any]] = []


def bearer_headers(token: str = DEV_TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def call_log() -> list[dict[str, Any]]:
    return list(_CALL_LOG)


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


def _session_id(request: Request) -> str | None:
    return request.headers.get("x-session-id") or request.headers.get("X-Session-Id")


def _idempotency_key(request: Request) -> str | None:
    return request.headers.get("idempotency-key") or request.headers.get("Idempotency-Key")


def _ref(kind_meta: str, item_id: str, presentation: str) -> dict[str, str]:
    return {"ref": kind_meta, "id": item_id, "presentation": presentation}


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

DEMO_DOCUMENT: dict[str, Any] = {
    "kind": "document",
    "name": "DemoShipments",
    "synonym": "Демо-отгрузки",
    "description": "Фикстура реализаций/отгрузок стенда 1cmcp. Не объект типовой конфигурации.",
    "examples": ["отгрузка ООО Ромашка за август"],
    "fields": [
        {"name": "Number", "synonym": "Номер", "type": "string", "required": True},
        {"name": "Date", "synonym": "Дата", "type": "date", "required": True},
        {"name": "Posted", "synonym": "Проведен", "type": "boolean", "required": False},
        {
            "name": "Counterparty",
            "synonym": "Контрагент",
            "type": "ref",
            "required": True,
            "description": "Покупатель отгрузки",
            "examples": ["ООО Ромашка"],
        },
        {
            "name": "Amount",
            "synonym": "Сумма",
            "type": "number",
            "required": True,
            "description": "Сумма документа",
        },
    ],
    "tabular_sections": [],
    "json_schema": {
        "type": "object",
        "properties": {
            "Number": {"type": "string"},
            "Date": {"type": "string", "format": "date"},
            "Posted": {"type": "boolean"},
            "Counterparty": {"type": "object"},
            "Amount": {"type": "number"},
        },
        "required": ["Number", "Date", "Counterparty", "Amount"],
    },
}

DEMO_REPORT: dict[str, Any] = {
    "kind": "report",
    "name": "DemoSales",
    "synonym": "Демо-продажи",
    "description": "Фикстура отчёта СКД: продажи по контрагенту за период.",
    "examples": ["отчёт по продажам за август"],
    "fields": [
        {"name": "BeginDate", "synonym": "Начало периода", "type": "date", "required": True},
        {"name": "EndDate", "synonym": "Конец периода", "type": "date", "required": True},
        {
            "name": "Counterparty",
            "synonym": "Контрагент",
            "type": "ref",
            "required": False,
            "description": "Необязательный отбор по покупателю",
        },
    ],
    "tabular_sections": [],
    "json_schema": {
        "type": "object",
        "properties": {
            "BeginDate": {"type": "string", "format": "date"},
            "EndDate": {"type": "string", "format": "date"},
            "Counterparty": {"type": "object"},
        },
        "required": ["BeginDate", "EndDate"],
    },
}

HIDDEN_CONNECTOR_OBJECT: dict[str, Any] = {
    "kind": "catalog",
    "name": "мкпКлиентыИнтеграции",
    "synonym": "Клиенты интеграции",
    "description": "Служебный объект расширения, агенту не отдаётся.",
    "examples": [],
    "fields": [],
    "tabular_sections": [],
}

DEMO_ITEMS: dict[str, dict[str, Any]] = {
    DEMO_ID_ROMA: {
        "id": DEMO_ID_ROMA,
        "ref": _ref("Catalog.DemoCounterparties", DEMO_ID_ROMA, "ООО Ромашка"),
        "Description": "ООО Ромашка",
        "INN": "7701234567",
    },
    DEMO_ID_IVAN: {
        "id": DEMO_ID_IVAN,
        "ref": _ref("Catalog.DemoCounterparties", DEMO_ID_IVAN, "ИП Иванов"),
        "Description": "ИП Иванов",
        "INN": "5001098765",
    },
}

DEMO_SHIPMENTS: dict[str, dict[str, Any]] = {
    SHIP_AUG_1: {
        "id": SHIP_AUG_1,
        "ref": _ref("Document.DemoShipments", SHIP_AUG_1, "000000001 от 05.08.2026"),
        "Number": "000000001",
        "Date": "2026-08-05",
        "Posted": True,
        "Counterparty": _ref("Catalog.DemoCounterparties", DEMO_ID_ROMA, "ООО Ромашка"),
        "Amount": 100000.0,
    },
    SHIP_AUG_2: {
        "id": SHIP_AUG_2,
        "ref": _ref("Document.DemoShipments", SHIP_AUG_2, "000000002 от 18.08.2026"),
        "Number": "000000002",
        "Date": "2026-08-18",
        "Posted": True,
        "Counterparty": _ref("Catalog.DemoCounterparties", DEMO_ID_ROMA, "ООО Ромашка"),
        "Amount": 50000.0,
    },
    SHIP_JULY: {
        "id": SHIP_JULY,
        "ref": _ref("Document.DemoShipments", SHIP_JULY, "000000003 от 10.07.2026"),
        "Number": "000000003",
        "Date": "2026-07-10",
        "Posted": True,
        "Counterparty": _ref("Catalog.DemoCounterparties", DEMO_ID_ROMA, "ООО Ромашка"),
        "Amount": 9999.0,
    },
    SHIP_IVAN: {
        "id": SHIP_IVAN,
        "ref": _ref("Document.DemoShipments", SHIP_IVAN, "000000004 от 12.08.2026"),
        "Number": "000000004",
        "Date": "2026-08-12",
        "Posted": True,
        "Counterparty": _ref("Catalog.DemoCounterparties", DEMO_ID_IVAN, "ИП Иванов"),
        "Amount": 30000.0,
    },
}

SEMANTIC_DICTIONARY: list[dict[str, str]] = [
    {
        "kind": "catalog",
        "name": "DemoCounterparties",
        "field": "",
        "synonyms": "контрагент, покупатель, counterparty",
        "description": "Демо-справочник контрагентов стенда",
        "examples": "ООО Ромашка",
    },
    {
        "kind": "document",
        "name": "DemoShipments",
        "field": "",
        "synonyms": "отгрузка, реализация, shipment, отгрузки",
        "description": "Демо-документы отгрузки (реализации) товаров",
        "examples": "сколько отгрузок за август по контрагенту",
    },
    {
        "kind": "document",
        "name": "DemoShipments",
        "field": "Counterparty",
        "synonyms": "контрагент, покупатель",
        "description": "Покупатель в отгрузке",
        "examples": "ООО Ромашка",
    },
    {
        "kind": "document",
        "name": "DemoShipments",
        "field": "Amount",
        "synonyms": "сумма, amount",
        "description": "Сумма отгрузки",
        "examples": "150000",
    },
    {
        "kind": "document",
        "name": "DemoShipments",
        "field": "Date",
        "synonyms": "дата, период, август",
        "description": "Дата документа отгрузки",
        "examples": "2026-08-01",
    },
    {
        "kind": "report",
        "name": "DemoSales",
        "field": "",
        "synonyms": "продажи, отчёт, отчет, скд, sales report",
        "description": "Демо-отчёт СКД по продажам",
        "examples": "отчёт по продажам за август",
    },
]

_COLLECTIONS: dict[tuple[str, str], dict[str, dict[str, Any]]] = {
    ("catalog", "DemoCounterparties"): DEMO_ITEMS,
    ("document", "DemoShipments"): DEMO_SHIPMENTS,
}

_ITEMS_SEED = copy.deepcopy(DEMO_ITEMS)
_SHIPMENTS_SEED = copy.deepcopy(DEMO_SHIPMENTS)

_META: dict[tuple[str, str], dict[str, Any]] = {
    ("catalog", "DemoCounterparties"): DEMO_CATALOG,
    ("document", "DemoShipments"): DEMO_DOCUMENT,
    ("report", "DemoSales"): DEMO_REPORT,
    ("catalog", "мкпКлиентыИнтеграции"): HIDDEN_CONNECTOR_OBJECT,
}

NAMED_QUERIES = {
    "DemoShipmentsByPeriod": {
        "description": "Отгрузки за период с отбором по контрагенту",
        "columns": ["Number", "Date", "Counterparty", "Amount"],
    },
    "DemoHeavy": {
        "description": "Тяжёлая выборка для проверки /v1/job",
        "columns": ["Number", "Date", "Counterparty", "Amount"],
        "heavy": True,
    },
}

_JOBS: dict[str, dict[str, Any]] = {}


def _summary(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": obj["kind"],
        "name": obj["name"],
        "synonym": obj.get("synonym"),
        "description": obj.get("description"),
        "examples": obj.get("examples", []),
    }


def _public_meta() -> list[dict[str, Any]]:
    return [
        DEMO_CATALOG,
        DEMO_DOCUMENT,
        DEMO_REPORT,
    ]


def _is_hidden(name: str) -> bool:
    return name.startswith("мкп")


def _authenticate(request: Request, *, scope: str = "read") -> dict[str, Any] | JSONResponse:
    header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if not header.startswith("Bearer "):
        return problem(401, "unauthorized", "Unauthorized", "Требуется действительный Bearer-токен")
    token = header[7:].strip()
    client = _CLIENTS.get(token)
    if client is None:
        return problem(401, "unauthorized", "Unauthorized", "Требуется действительный Bearer-токен")
    scopes = client["scopes"]
    if "*" not in scopes and scope not in scopes:
        return problem(403, "forbidden", "Forbidden", "Недостаточно прав")
    return client


def _allowed(client: dict[str, Any], kind: str, name: str, operation: str = "read") -> bool:
    if _is_hidden(name):
        return False
    acl = client.get("acl")
    if acl is None:
        return operation == "read"
    return bool(acl.get((kind, name), False))


def _match_filter(item: dict[str, Any], spec: Any, field: str) -> bool:
    value = item.get(field)
    if isinstance(spec, dict):
        if "id" in spec and _ref_id(value) != spec["id"]:
            return False
        if "eq" in spec and not _equals(value, spec["eq"]):
            return False
        if "contains" in spec:
            haystack = str(_scalar(value)).casefold()
            if str(spec["contains"]).casefold() not in haystack:
                return False
        if "gte" in spec and _compare(value, spec["gte"]) < 0:
            return False
        if "lte" in spec and _compare(value, spec["lte"]) > 0:
            return False
        if "gt" in spec and _compare(value, spec["gt"]) <= 0:
            return False
        if "lt" in spec and _compare(value, spec["lt"]) >= 0:
            return False
        return True
    return _equals(value, spec)


def _ref_id(value: Any) -> str:
    if isinstance(value, dict) and "id" in value:
        return str(value["id"])
    return str(value)


def _scalar(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("presentation") or value.get("id") or value
    return value


def _equals(value: Any, expected: Any) -> bool:
    if isinstance(value, dict):
        return expected in {value.get("id"), value.get("presentation"), value.get("ref")}
    return value == expected or str(value) == str(expected)


def _compare(value: Any, bound: Any) -> int:
    left = _scalar(value)
    try:
        return (float(left) > float(bound)) - (float(left) < float(bound))
    except (TypeError, ValueError):
        left_s, right_s = str(left), str(bound)
        return (left_s > right_s) - (left_s < right_s)


def _apply_fields(item: dict[str, Any], fields: str | None) -> dict[str, Any]:
    if not fields:
        return item
    wanted = {part.strip() for part in fields.split(",") if part.strip()}
    always = {"id", "ref"}
    return {key: value for key, value in item.items() if key in wanted or key in always}


def _paginate(
    items: list[dict[str, Any]],
    limit: int,
    cursor: str | None,
) -> tuple[list[dict[str, Any]], str | None, bool]:
    ordered = sorted(items, key=lambda item: item["id"])
    if cursor:
        ordered = [item for item in ordered if item["id"] > cursor]
    page = ordered[:limit]
    has_more = len(ordered) > limit
    next_cursor = page[-1]["id"] if has_more and page else None
    return page, next_cursor, has_more


def _search_items(query: str) -> list[dict[str, Any]]:
    needle = query.casefold()
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in SEMANTIC_DICTIONARY:
        haystack = " ".join(
            [
                entry["kind"],
                entry["name"],
                entry["field"],
                entry["synonyms"],
                entry["description"],
                entry["examples"],
            ]
        ).casefold()
        if needle not in haystack:
            continue
        meta = _META.get((entry["kind"], entry["name"]))
        if meta is None or _is_hidden(meta["name"]):
            continue
        found[(meta["kind"], meta["name"])] = _summary(meta)
    for meta in _public_meta():
        haystack = " ".join(
            [
                meta["name"],
                str(meta.get("synonym") or ""),
                str(meta.get("description") or ""),
                " ".join(meta.get("examples") or []),
            ]
        ).casefold()
        if needle in haystack:
            found[(meta["kind"], meta["name"])] = _summary(meta)
    return list(found.values())


def _param(params: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in params and params[name] not in (None, ""):
            return params[name]
    return None


def _filter_shipments(params: dict[str, Any]) -> list[dict[str, Any]]:
    begin = _param(params, "BeginDate", "begin", "ДатаНачала")
    end = _param(params, "EndDate", "end", "ДатаОкончания")
    counterparty = _param(params, "Counterparty", "Контрагент")
    matched = list(DEMO_SHIPMENTS.values())
    if begin:
        matched = [item for item in matched if _compare(item["Date"], begin) >= 0]
    if end:
        matched = [item for item in matched if _compare(item["Date"], end) <= 0]
    if counterparty:
        spec = counterparty if isinstance(counterparty, dict) else {"id": counterparty}
        matched = [item for item in matched if _match_filter(item, spec, "Counterparty")]
    return matched


def _named_query_rows(name: str, params: dict[str, Any], limit: int) -> dict[str, Any]:
    spec = NAMED_QUERIES[name]
    items = _filter_shipments(params)[:limit]
    rows: list[list[Any]] = []
    for item in items:
        rows.append(
            [
                item["Number"],
                item["Date"],
                item["Counterparty"].get("presentation"),
                item["Amount"],
            ]
        )
    return {
        "content_kind": "data",
        "named_query": name,
        "columns": list(spec["columns"]),
        "rows": rows,
    }


def _literal_select(text: str, params: dict[str, Any], limit: int) -> dict[str, Any]:
    compact = validate_query_text(text)
    folded = compact.casefold()
    if folded in {"выбрать 1", "select 1", "select 1 as x"}:
        return {"content_kind": "data", "columns": ["Value"], "rows": [[1]]}
    if "demoshipments" in folded.replace(".", "").casefold() or "демо-отгруз" in folded:
        payload = _named_query_rows("DemoShipmentsByPeriod", params, limit)
        payload.pop("named_query", None)
        return payload
    return {"content_kind": "data", "columns": [], "rows": []}


def _sales_body(params: dict[str, Any]) -> dict[str, Any]:
    items = _filter_shipments(params)
    grouped: dict[str, dict[str, Any]] = {}
    for item in items:
        title = item["Counterparty"]["presentation"]
        bucket = grouped.setdefault(title, {"Counterparty": title, "Count": 0, "Amount": 0.0})
        bucket["Count"] += 1
        bucket["Amount"] += float(item["Amount"])
    rows = sorted(grouped.values(), key=lambda row: str(row["Counterparty"]))
    totals = {
        "Count": sum(int(row["Count"]) for row in rows),
        "Amount": sum(float(row["Amount"]) for row in rows),
    }
    return {
        "name": "DemoSales",
        "variant": "Default",
        "columns": ["Counterparty", "Count", "Amount"],
        "rows": rows,
        "totals": totals,
    }


def _render_report(body: dict[str, Any], fmt: str) -> Any:
    if fmt == "json":
        return body
    columns = body["columns"]
    rows = body["rows"]
    if fmt == "csv":
        lines = [",".join(columns)]
        for row in rows:
            lines.append(",".join(str(row[col]) for col in columns))
        lines.append(f"Итого,{body['totals']['Count']},{body['totals']['Amount']}")
        return "\n".join(lines) + "\n"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for row in rows:
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    lines.append("")
    lines.append(f"**Итого:** {body['totals']['Count']} / {body['totals']['Amount']}")
    return "\n".join(lines)


def _read_json_body(payload: Any) -> dict[str, Any] | JSONResponse:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        return problem(400, "bad_request", "Bad request", "Тело должно быть JSON-объектом")
    return payload


def _query_result(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    named = payload.get("named_query")
    text = payload.get("text")
    if named and text:
        return problem(400, "bad_request", "Bad request", "Укажите либо named_query, либо text")
    if not named and not text:
        return problem(400, "bad_request", "Bad request", "Нужен named_query или text")
    try:
        limit = resolve_limit(payload.get("limit"))
    except QueryRejected as exc:
        return problem(400, exc.code, "Query rejected", exc.detail)
    params = payload.get("parameters") or {}
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return problem(400, "bad_request", "Bad request", "parameters должен быть объектом")
    if named:
        if named not in NAMED_QUERIES:
            return problem(404, "not_found", "Not found", f"Нет именованного запроса {named}")
        return _named_query_rows(str(named), params, limit)
    try:
        return _literal_select(str(text), params, limit)
    except QueryRejected as exc:
        return problem(400, exc.code, "Query rejected", exc.detail)


def _report_result(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    name = payload.get("name")
    if not name:
        return problem(400, "bad_request", "Bad request", "Нужно имя отчёта")
    if name != "DemoSales":
        return problem(404, "not_found", "Not found", f"Нет отчёта {name}")
    fmt = str(payload.get("format") or "json")
    if fmt not in {"json", "markdown", "csv"}:
        return problem(400, "bad_request", "Bad request", "format: json, markdown или csv")
    params = payload.get("parameters") or {}
    if not isinstance(params, dict):
        return problem(400, "bad_request", "Bad request", "parameters должен быть объектом")
    body = _sales_body(params)
    if payload.get("variant"):
        body["variant"] = payload["variant"]
    return {
        "content_kind": "data",
        "format": fmt,
        "body": _render_report(body, fmt),
    }


def _store_job(operation: str, result: dict[str, Any]) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    record = {
        "job_id": job_id,
        "status": "succeeded",
        "operation": operation,
        "result": result,
    }
    _JOBS[job_id] = record
    return {"job_id": job_id, "status": "queued"}


_WRITE = WriteEngine(_COLLECTIONS)


def _reset_data() -> None:
    DEMO_ITEMS.clear()
    DEMO_ITEMS.update(copy.deepcopy(_ITEMS_SEED))
    DEMO_SHIPMENTS.clear()
    DEMO_SHIPMENTS.update(copy.deepcopy(_SHIPMENTS_SEED))
    _WRITE.reset(_COLLECTIONS)


def create_mock_app() -> FastAPI:
    global _CALL_LOG, _JOBS
    _CALL_LOG = []
    _JOBS = {}
    _reset_data()
    app = FastAPI(title="1cmcp mock adapter", version=__version__)
    app.state.call_log = _CALL_LOG

    @app.middleware("http")
    async def audit(request: Request, call_next):  # noqa: ANN001
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        _CALL_LOG.append(
            {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        app.state.call_log = _CALL_LOG
        return response

    @app.get("/v1/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "1cmcp",
            "version": __version__,
            "api": "v1",
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    @app.get("/v1/diag")
    async def diag() -> dict:
        return build_adapter_diag(
            version=__version__,
            time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    @app.get("/v1/meta")
    async def list_meta(
        request: Request,
        kind: str | None = None,
        limit: int = Query(default=50, ge=1, le=500),
        cursor: str | None = None,
    ) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        items = [_summary(item) for item in _public_meta() if kind is None or item["kind"] == kind]
        if cursor:
            items = [item for item in items if f"{item['kind']}/{item['name']}" > cursor]
        page = items[:limit]
        has_more = len(items) > limit
        next_cursor = f"{page[-1]['kind']}/{page[-1]['name']}" if has_more and page else None
        return JSONResponse(
            {"items": page, "next_cursor": next_cursor, "has_more": has_more},
            headers=data_headers(),
        )

    @app.get("/v1/meta/search")
    async def search_meta(
        request: Request,
        q: str = Query(min_length=1, max_length=200),
        limit: int = Query(default=20, ge=1, le=500),
    ) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        items = _search_items(q)[:limit]
        return JSONResponse({"query": q, "items": items}, headers=data_headers())

    @app.get("/v1/meta/{kind}/{name}")
    async def describe_meta(kind: str, name: str, request: Request) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        if _is_hidden(name):
            return problem(404, "not_found", "Not found", f"Нет объекта {kind}/{name}")
        if not _allowed(auth, kind, name):
            return problem(403, "forbidden", "Forbidden", "Нет доступа к объекту")
        meta = _META.get((kind, name))
        if meta is None:
            return problem(404, "not_found", "Not found", f"Нет объекта {kind}/{name}")
        return JSONResponse(meta, headers=data_headers())

    @app.get("/v1/data/{kind}/{name}")
    async def list_data(
        kind: str,
        name: str,
        request: Request,
        limit: int = Query(default=50, ge=1, le=500),
        cursor: str | None = None,
        filter: str | None = None,
        fields: str | None = None,
    ) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        if _is_hidden(name):
            return problem(404, "not_found", "Not found", f"Нет выборки {kind}/{name}")
        if not _allowed(auth, kind, name):
            return problem(403, "forbidden", "Forbidden", "Нет доступа к объекту")
        collection = _COLLECTIONS.get((kind, name))
        if collection is None:
            return problem(404, "not_found", "Not found", f"Нет выборки {kind}/{name}")
        parsed: dict[str, Any] | None = None
        if filter:
            try:
                loaded = json.loads(filter)
            except json.JSONDecodeError:
                return problem(400, "bad_request", "Bad request", "Некорректный JSON фильтра")
            if not isinstance(loaded, dict):
                return problem(400, "bad_request", "Bad request", "Фильтр должен быть объектом")
            parsed = loaded
        matched = list(collection.values())
        if parsed:
            matched = [
                item
                for item in matched
                if all(_match_filter(item, spec, field) for field, spec in parsed.items())
            ]
        page, next_cursor, has_more = _paginate(matched, limit, cursor)
        projected = [_apply_fields(item, fields) for item in page]
        return JSONResponse(
            {
                "content_kind": "data",
                "kind": kind,
                "name": name,
                "items": projected,
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
            headers=data_headers(),
        )

    @app.get("/v1/data/{kind}/{name}/{item_id}")
    async def get_data(kind: str, name: str, item_id: str, request: Request) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        if _is_hidden(name):
            return problem(404, "not_found", "Not found", "Объект не найден")
        if not _allowed(auth, kind, name):
            return problem(403, "forbidden", "Forbidden", "Нет доступа к объекту")
        collection = _COLLECTIONS.get((kind, name))
        if collection is None or item_id not in collection:
            return problem(404, "not_found", "Not found", "Объект не найден")
        return JSONResponse(
            {
                "content_kind": "data",
                "kind": kind,
                "name": name,
                "item": collection[item_id],
            },
            headers=data_headers(),
        )

    async def _json_payload(request: Request) -> dict[str, Any] | JSONResponse:
        raw = await request.body()
        if not raw:
            return {}
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return problem(400, "bad_request", "Bad request", "Некорректный JSON")
        return _read_json_body(loaded)

    def _maybe_async(payload: dict[str, Any], operation: str, result: dict[str, Any]) -> JSONResponse:
        if payload.get("async") is True:
            accepted = _store_job(operation, result)
            return JSONResponse(accepted, status_code=202)
        return JSONResponse(result, headers=data_headers())

    @app.post("/v1/query")
    async def run_query(request: Request) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        result = _query_result(payload)
        if isinstance(result, JSONResponse):
            return result
        return _maybe_async(payload, "query", result)

    @app.post("/v1/report")
    async def run_report(request: Request) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        result = _report_result(payload)
        if isinstance(result, JSONResponse):
            return result
        return _maybe_async(payload, "report", result)

    @app.post("/v1/job")
    async def start_job(request: Request) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        operation = payload.get("operation")
        inner = payload.get("payload") or {}
        if not isinstance(inner, dict):
            return problem(400, "bad_request", "Bad request", "payload должен быть объектом")
        if operation == "action":
            return problem(
                501,
                "not_implemented",
                "Not implemented",
                "Вызов действий — фаза 3.",
            )
        if operation == "query":
            result = _query_result(inner)
        elif operation == "report":
            result = _report_result(inner)
        else:
            return problem(400, "bad_request", "Bad request", "operation: query или report")
        if isinstance(result, JSONResponse):
            return result
        accepted = _store_job(str(operation), result)
        return JSONResponse(accepted, status_code=202)

    @app.get("/v1/job/{job_id}")
    async def get_job(job_id: str, request: Request) -> JSONResponse:
        auth = _authenticate(request)
        if isinstance(auth, JSONResponse):
            return auth
        record = _JOBS.get(job_id)
        if record is None:
            return problem(404, "not_found", "Not found", "Задание не найдено")
        return JSONResponse(record)

    def _guard_write(request: Request, kind: str, name: str, operation: str = "write"):
        auth = _authenticate(request, scope="write")
        if isinstance(auth, JSONResponse):
            return auth
        if _is_hidden(name):
            return problem(404, "not_found", "Not found", f"Нет объекта {kind}/{name}")
        if not _allowed(auth, kind, name, operation):
            return problem(403, "forbidden", "Forbidden", "Нет доступа на запись")
        return auth

    def _write_result(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "ref": item["ref"],
            "posted": bool(item.get("Posted")),
            "warnings": [],
        }

    @app.post("/v1/data/{kind}/{name}/dry-run")
    async def dry_run_data(kind: str, name: str, request: Request) -> JSONResponse:
        auth = _guard_write(request, kind, name)
        if isinstance(auth, JSONResponse):
            return auth
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        item = payload.get("item")
        if not isinstance(item, dict):
            return problem(400, "bad_request", "Bad request", "Нужно поле item")
        if _COLLECTIONS.get((kind, name)) is None:
            return problem(404, "not_found", "Not found", f"Нет выборки {kind}/{name}")
        return JSONResponse(_WRITE.dry_run(kind, name, item, post=bool(payload.get("post"))))

    @app.post("/v1/data/{kind}/{name}")
    async def create_data(kind: str, name: str, request: Request) -> JSONResponse:
        auth = _guard_write(request, kind, name)
        if isinstance(auth, JSONResponse):
            return auth
        key = _idempotency_key(request)
        if not key or not 8 <= len(key) <= 128:
            return problem(400, "bad_request", "Bad request", "Нужен заголовок Idempotency-Key (8–128 символов)")
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        item = payload.get("item")
        if not isinstance(item, dict):
            return problem(400, "bad_request", "Bad request", "Нужно поле item")
        fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        replayed = _WRITE.replay(auth["id"], key, fingerprint)
        if replayed == "conflict":
            return problem(409, "idempotency_conflict", "Conflict", "Idempotency-Key уже использован с другим телом")
        if isinstance(replayed, dict):
            return JSONResponse(replayed, status_code=201)
        token = payload.get("confirm_token")
        if not token:
            return problem(
                400,
                "confirm_required",
                "Confirmation required",
                "Сначала dry-run, затем запись с confirm_token",
            )
        consumed = _WRITE.consume_token(str(token), kind, name, item)
        if isinstance(consumed, str):
            return problem(400, "confirm_required", "Confirmation required", consumed)
        stored = consumed["item"]
        issues = fill_check(kind, name, stored)
        if issues:
            return problem(422, "fill_check_failed", "Fill check failed", "; ".join(issues))
        collection = _COLLECTIONS.get((kind, name))
        if collection is None:
            return problem(404, "not_found", "Not found", f"Нет выборки {kind}/{name}")
        collection[stored["id"]] = stored
        session = _session_id(request)
        _WRITE.track(session, {"op": "create", "kind": kind, "name": name, "id": stored["id"]})
        want_post = bool(payload.get("post") or consumed.get("post"))
        if want_post:
            errors = posting_check(stored)
            if errors:
                result = {**_write_result(stored), "warnings": errors}
            else:
                previous_posted = bool(stored.get("Posted"))
                stored["Posted"] = True
                _WRITE.track(
                    session,
                    {
                        "op": "post",
                        "kind": kind,
                        "name": name,
                        "id": stored["id"],
                        "previous_posted": previous_posted,
                    },
                )
                result = _write_result(stored)
        else:
            result = _write_result(stored)
        _WRITE.remember(auth["id"], key, result, fingerprint)
        return JSONResponse(result, status_code=201)

    @app.patch("/v1/data/{kind}/{name}/{item_id}")
    async def patch_data(kind: str, name: str, item_id: str, request: Request) -> JSONResponse:
        auth = _guard_write(request, kind, name)
        if isinstance(auth, JSONResponse):
            return auth
        key = _idempotency_key(request)
        if not key or not 8 <= len(key) <= 128:
            return problem(400, "bad_request", "Bad request", "Нужен заголовок Idempotency-Key (8–128 символов)")
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        patch = payload.get("item")
        if not isinstance(patch, dict):
            return problem(400, "bad_request", "Bad request", "Нужно поле item")
        fingerprint = json.dumps({"id": item_id, "item": patch}, ensure_ascii=False, sort_keys=True, default=str)
        replayed = _WRITE.replay(auth["id"], key, fingerprint)
        if replayed == "conflict":
            return problem(409, "idempotency_conflict", "Conflict", "Idempotency-Key уже использован с другим телом")
        if isinstance(replayed, dict):
            return JSONResponse(replayed)
        collection = _COLLECTIONS.get((kind, name))
        if collection is None or item_id not in collection:
            return problem(404, "not_found", "Not found", "Объект не найден")
        token = payload.get("confirm_token")
        if not token:
            return problem(
                400,
                "confirm_required",
                "Confirmation required",
                "Сначала dry-run, затем запись с confirm_token",
            )
        merged = {**collection[item_id], **patch}
        consumed = _WRITE.consume_token(str(token), kind, name, merged)
        if isinstance(consumed, str):
            return problem(400, "confirm_required", "Confirmation required", consumed)
        previous = copy.deepcopy(collection[item_id])
        collection[item_id] = consumed["item"]
        collection[item_id]["id"] = item_id
        result = _write_result(collection[item_id])
        _WRITE.track(
            _session_id(request),
            {"op": "patch", "kind": kind, "name": name, "id": item_id, "previous": previous},
        )
        _WRITE.remember(auth["id"], key, result, fingerprint)
        return JSONResponse(result)

    @app.post("/v1/data/{kind}/{name}/{item_id}/post")
    async def post_document(kind: str, name: str, item_id: str, request: Request) -> JSONResponse:
        auth = _guard_write(request, kind, name, operation="write")
        if isinstance(auth, JSONResponse):
            return auth
        key = _idempotency_key(request)
        if not key or not 8 <= len(key) <= 128:
            return problem(400, "bad_request", "Bad request", "Нужен заголовок Idempotency-Key (8–128 символов)")
        fingerprint = json.dumps({"id": item_id, "op": "post"}, ensure_ascii=False, sort_keys=True)
        replayed = _WRITE.replay(auth["id"], key, fingerprint)
        if replayed == "conflict":
            return problem(409, "idempotency_conflict", "Conflict", "Idempotency-Key уже использован с другим телом")
        if isinstance(replayed, dict):
            return JSONResponse(replayed)
        if kind != "document":
            return problem(400, "bad_request", "Bad request", "Проводить можно только документы")
        collection = _COLLECTIONS.get((kind, name))
        if collection is None or item_id not in collection:
            return problem(404, "not_found", "Not found", "Объект не найден")
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        token = payload.get("confirm_token")
        if not token:
            return problem(
                400,
                "confirm_required",
                "Confirmation required",
                "Сначала dry-run с post=true, затем проведение с confirm_token",
            )
        consumed = _WRITE.consume_for_target(str(token), kind, name, item_id)
        if isinstance(consumed, str):
            return problem(400, "confirm_required", "Confirmation required", consumed)
        errors = posting_check(collection[item_id])
        if errors:
            return problem(422, "posting_failed", "Posting failed", "; ".join(errors))
        previous_posted = bool(collection[item_id].get("Posted"))
        collection[item_id]["Posted"] = True
        result = _write_result(collection[item_id])
        _WRITE.track(
            _session_id(request),
            {
                "op": "post",
                "kind": kind,
                "name": name,
                "id": item_id,
                "previous_posted": previous_posted,
            },
        )
        _WRITE.remember(auth["id"], key, result, fingerprint)
        return JSONResponse(result)

    @app.post("/v1/action")
    async def run_action(request: Request) -> JSONResponse:
        auth = _authenticate(request, scope="write")
        if isinstance(auth, JSONResponse):
            return auth
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        name = payload.get("name")
        if name != "DemoPostShipment":
            return problem(404, "not_found", "Not found", f"Действие {name} не в whitelist")
        arguments = payload.get("arguments") or {}
        item_id = arguments.get("id") if isinstance(arguments, dict) else None
        collection = _COLLECTIONS[("document", "DemoShipments")]
        if not item_id or item_id not in collection:
            return problem(404, "not_found", "Not found", "Документ не найден")
        if not _allowed(auth, "document", "DemoShipments", "write"):
            return problem(403, "forbidden", "Forbidden", "Нет доступа на запись")
        errors = posting_check(collection[item_id])
        if errors:
            return problem(422, "posting_failed", "Posting failed", "; ".join(errors))
        previous_posted = bool(collection[item_id].get("Posted"))
        collection[item_id]["Posted"] = True
        _WRITE.track(
            _session_id(request),
            {
                "op": "post",
                "kind": "document",
                "name": "DemoShipments",
                "id": item_id,
                "previous_posted": previous_posted,
            },
        )
        return JSONResponse(
            {
                "name": "DemoPostShipment",
                "posted": True,
                "ref": collection[item_id]["ref"],
            }
        )

    @app.post("/v1/session/rollback")
    async def rollback_session(request: Request) -> JSONResponse:
        auth = _authenticate(request, scope="write")
        if isinstance(auth, JSONResponse):
            return auth
        payload = await _json_payload(request)
        if isinstance(payload, JSONResponse):
            return payload
        session = payload.get("session_id")
        if not session:
            return problem(400, "bad_request", "Bad request", "Нужен session_id")
        undone = _WRITE.rollback(str(session))
        return JSONResponse({"session_id": session, "undone": undone})

    @app.api_route("/v1/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    async def not_implemented(path: str, request: Request) -> JSONResponse:  # noqa: ARG001
        if request.url.path not in {"/v1/health", "/v1/diag"}:
            auth = _authenticate(request)
            if isinstance(auth, JSONResponse):
                return auth
        return problem(
            501,
            "not_implemented",
            "Not implemented",
            "Операция описана в контракте v1 и будет реализована в следующей фазе.",
        )

    return app
