from __future__ import annotations

import json
from typing import Any

from onecmcp.client import AdapterError, OneCClient
from onecmcp.presets import merge_search_items, scenario_guide


def mark_as_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Пометить ответ из 1С как данные, а не как инструкции агенту."""
    if "content_kind" not in payload:
        payload = {**payload, "content_kind": "data"}
    return payload


async def health_tool(client: OneCClient) -> dict[str, Any]:
    return await client.health()


async def meta_list_tool(
    client: OneCClient,
    kind: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    try:
        return mark_as_data(await client.meta_list(kind=kind, limit=limit, cursor=cursor))
    except AdapterError as exc:
        return _error_payload(exc)


async def meta_search_tool(
    client: OneCClient,
    query: str,
    limit: int = 20,
    preset: str | None = "auto",
) -> dict[str, Any]:
    try:
        payload = await client.meta_search(query, limit=limit)
    except AdapterError as exc:
        return _error_payload(exc)
    items = payload.get("items") if isinstance(payload, dict) else None
    if isinstance(items, list):
        payload = {
            **payload,
            "items": merge_search_items(items, query, preset, limit=limit),
        }
    return mark_as_data(payload)


def guide_tool(question: str, preset: str | None = "auto") -> dict[str, Any]:
    """Локальный сценарий по вопросу на естественном языке. В 1С не ходит."""
    return scenario_guide(question, preset)


async def meta_describe_tool(client: OneCClient, kind: str, name: str) -> dict[str, Any]:
    try:
        return mark_as_data(await client.meta_describe(kind, name))
    except AdapterError as exc:
        return _error_payload(exc)


async def data_list_tool(
    client: OneCClient,
    kind: str,
    name: str,
    limit: int = 50,
    cursor: str | None = None,
    filter_json: str | None = None,
    fields: str | None = None,
) -> dict[str, Any]:
    try:
        return mark_as_data(
            await client.list_data(
                kind,
                name,
                limit=limit,
                cursor=cursor,
                filter_json=filter_json,
                fields=fields,
            )
        )
    except AdapterError as exc:
        return _error_payload(exc)


async def data_get_tool(client: OneCClient, kind: str, name: str, item_id: str) -> dict[str, Any]:
    try:
        return mark_as_data(await client.get_data(kind, name, item_id))
    except AdapterError as exc:
        return _error_payload(exc)


def _accepted_or_data(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    if status_code == 202:
        return payload
    return mark_as_data(payload)


async def query_tool(
    client: OneCClient,
    named_query: str | None = None,
    text: str | None = None,
    parameters_json: str | None = None,
    limit: int | None = None,
    async_mode: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"async": async_mode}
    if named_query:
        payload["named_query"] = named_query
    if text:
        payload["text"] = text
    if limit is not None:
        payload["limit"] = limit
    if parameters_json:
        params, error = _try_json_object(parameters_json, "parameters")
        if error is not None:
            return error
        payload["parameters"] = params
    try:
        status, body = await client.run_query(payload)
        return _accepted_or_data(status, body)
    except AdapterError as exc:
        return _error_payload(exc)


async def report_tool(
    client: OneCClient,
    name: str,
    variant: str | None = None,
    parameters_json: str | None = None,
    format: str = "json",
    async_mode: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": name, "format": format, "async": async_mode}
    if variant:
        payload["variant"] = variant
    if parameters_json:
        params, error = _try_json_object(parameters_json, "parameters")
        if error is not None:
            return error
        payload["parameters"] = params
    try:
        status, body = await client.run_report(payload)
        return _accepted_or_data(status, body)
    except AdapterError as exc:
        return _error_payload(exc)


async def job_get_tool(client: OneCClient, job_id: str) -> dict[str, Any]:
    try:
        payload = await client.get_job(job_id)
    except AdapterError as exc:
        return _error_payload(exc)
    result = payload.get("result")
    if isinstance(result, dict):
        payload = {**payload, "result": mark_as_data(result)}
    return payload


def _try_json_object(raw: str, field: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None, {
            "type": "https://1cmcp.dev/errors/bad_request",
            "title": "Bad request",
            "status": 400,
            "code": "bad_request",
            "detail": f"{field} должен быть JSON-объектом",
        }
    if not isinstance(loaded, dict):
        return None, {
            "type": "https://1cmcp.dev/errors/bad_request",
            "title": "Bad request",
            "status": 400,
            "code": "bad_request",
            "detail": f"{field} должен быть JSON-объектом",
        }
    return loaded, None


def _error_payload(exc: AdapterError) -> dict[str, Any]:
    payload = exc.payload
    if isinstance(payload, dict):
        return payload
    return {
        "type": "https://1cmcp.dev/errors/upstream_error",
        "title": "Adapter error",
        "status": exc.status_code,
        "code": "upstream_error",
        "detail": str(payload),
    }
