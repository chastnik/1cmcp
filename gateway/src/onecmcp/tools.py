from __future__ import annotations

import json
from typing import Any

from onecmcp.client import AdapterError, OneCClient
from onecmcp.config import Settings
from onecmcp.diag import build_gateway_diag
from onecmcp.presets import merge_search_items, scenario_guide


def mark_as_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Пометить ответ из 1С как данные, а не как инструкции агенту."""
    if "content_kind" not in payload:
        payload = {**payload, "content_kind": "data"}
    return payload


async def health_tool(client: OneCClient) -> dict[str, Any]:
    return await client.health()


async def diag_tool(client: OneCClient, settings: Settings) -> dict[str, Any]:
    try:
        adapter = await client.diag()
        return build_gateway_diag(settings, adapter=adapter)
    except AdapterError as exc:
        return build_gateway_diag(settings, adapter_error=str(exc.payload or exc))
    except Exception as exc:  # noqa: BLE001
        return build_gateway_diag(settings, adapter_error=str(exc))


async def audit_list_tool(
    client: OneCClient,
    limit: int = 50,
    since: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    try:
        return mark_as_data(await client.audit_list(limit=limit, since=since, path=path))
    except AdapterError as exc:
        return _error_payload(exc)


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


async def data_dry_run_tool(
    client: OneCClient,
    kind: str,
    name: str,
    item_json: str,
    post: bool = False,
) -> dict[str, Any]:
    item, error = _try_json_object(item_json, "item")
    if error is not None:
        return error
    try:
        return await client.dry_run(kind, name, item or {}, post=post)
    except AdapterError as exc:
        return _error_payload(exc)


async def data_create_tool(
    client: OneCClient,
    kind: str,
    name: str,
    item_json: str,
    confirm_token: str,
    idempotency_key: str,
    session_id: str | None = None,
    post: bool = False,
) -> dict[str, Any]:
    item, error = _try_json_object(item_json, "item")
    if error is not None:
        return error
    try:
        _, body = await client.create_data(
            kind,
            name,
            item or {},
            confirm_token=confirm_token,
            idempotency_key=idempotency_key,
            session_id=session_id,
            post=post,
        )
        return body
    except AdapterError as exc:
        return _error_payload(exc)


async def data_patch_tool(
    client: OneCClient,
    kind: str,
    name: str,
    item_id: str,
    item_json: str,
    confirm_token: str,
    idempotency_key: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    item, error = _try_json_object(item_json, "item")
    if error is not None:
        return error
    try:
        _, body = await client.patch_data(
            kind,
            name,
            item_id,
            item or {},
            confirm_token=confirm_token,
            idempotency_key=idempotency_key,
            session_id=session_id,
        )
        return body
    except AdapterError as exc:
        return _error_payload(exc)


async def data_post_tool(
    client: OneCClient,
    kind: str,
    name: str,
    item_id: str,
    confirm_token: str,
    idempotency_key: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    try:
        _, body = await client.post_document(
            kind,
            name,
            item_id,
            confirm_token=confirm_token,
            idempotency_key=idempotency_key,
            session_id=session_id,
        )
        return body
    except AdapterError as exc:
        return _error_payload(exc)


async def action_tool(
    client: OneCClient,
    name: str,
    arguments_json: str | None = None,
    confirm_token: str | None = None,
    idempotency_key: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    if arguments_json:
        parsed, error = _try_json_object(arguments_json, "arguments")
        if error is not None:
            return error
        arguments = parsed or {}
    try:
        _, body = await client.run_action(
            name,
            arguments,
            confirm_token=confirm_token,
            idempotency_key=idempotency_key,
            session_id=session_id,
        )
        return body
    except AdapterError as exc:
        return _error_payload(exc)


async def session_rollback_tool(client: OneCClient, session_id: str) -> dict[str, Any]:
    try:
        return await client.rollback_session(session_id)
    except AdapterError as exc:
        return _error_payload(exc)


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
