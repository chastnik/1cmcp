from __future__ import annotations

import httpx

from onecmcp.client import AdapterError, OneCClient, _payload
from onecmcp.config import Settings, load_settings
from onecmcp.mock1c import DEMO_CATALOG, DEMO_ID_ROMA, DEV_TOKEN, WRITE_DEV_TOKEN, create_mock_app
from onecmcp.tools import (
    action_tool,
    data_create_tool,
    data_dry_run_tool,
    data_list_tool,
    data_patch_tool,
    health_tool,
    job_get_tool,
    meta_describe_tool,
    meta_list_tool,
    meta_search_tool,
    query_tool,
    report_tool,
    session_rollback_tool,
)


async def test_discovery_tools_against_mock() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN), transport=transport)
    try:
        health = await health_tool(client)
        assert health["status"] == "ok"

        found = await meta_search_tool(client, "ромашка")
        assert found["items"][0]["name"] == DEMO_CATALOG["name"]
        assert found["content_kind"] == "data"

        card = await meta_describe_tool(client, "catalog", "DemoCounterparties")
        assert card["kind"] == "catalog"

        page = await data_list_tool(client, "catalog", "DemoCounterparties", cursor="0")
        assert page["content_kind"] == "data"
        assert page["has_more"] is False
    finally:
        await client.aclose()


async def test_unknown_object_is_problem_json() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN, tenant=""), transport=transport)
    try:
        payload = await meta_describe_tool(client, "catalog", "Несуществующий")
        assert payload["code"] == "not_found"
        assert payload["status"] == 404
    finally:
        await client.aclose()


async def test_list_data_and_search_errors() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN), transport=transport)
    try:
        missing = await data_list_tool(client, "catalog", "НетТакого")
        assert missing["status"] == 404
        empty = await meta_search_tool(client, "zzzz-no-match")
        assert empty["items"] == []
        listed = await meta_list_tool(client, kind="report")
        assert listed["items"][0]["name"] == "DemoSales"
        denied = OneCClient(
            Settings(onec_base_url="http://adapter", onec_token="nope"),
            transport=transport,
        )
        try:
            forbidden = await meta_list_tool(denied)
            assert forbidden["status"] == 401
        finally:
            await denied.aclose()
        filtered = await client.list_data(
            "catalog",
            "DemoCounterparties",
            cursor="abc",
            filter_json='{"INN":"7701234567"}',
            fields="Description,INN",
        )
        assert filtered["content_kind"] == "data"
    finally:
        await client.aclose()


async def test_non_json_adapter_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal boom")

    client = OneCClient(Settings(onec_base_url="http://adapter"), transport=httpx.MockTransport(handler))
    try:
        payload = await meta_search_tool(client, "x")
        assert payload["code"] == "upstream_error"
        assert payload["status"] == 500
        assert "boom" in payload["detail"]
    finally:
        await client.aclose()


def test_payload_helper_and_adapter_error() -> None:
    response = httpx.Response(502, text="not-json")
    body = _payload(response)
    assert body["code"] == "upstream_error"
    err = AdapterError(502, "raw", {"x": "y"})
    assert "502" in str(err)
    assert err.headers["x"] == "y"
    from onecmcp.tools import _error_payload

    unstructured = _error_payload(AdapterError(500, "raw-text", {}))
    assert unstructured["code"] == "upstream_error"
    assert unstructured["detail"] == "raw-text"


def test_load_settings_defaults() -> None:
    settings = load_settings()
    assert settings.gateway_port == 8000
    assert settings.onec_base_url.startswith("http")
    assert settings.meta_cache_ttl_seconds == 60.0
    assert settings.onec_preset == "auto"


async def test_query_report_job_tools() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN), transport=transport)
    try:
        one = await query_tool(client, text="SELECT 1 AS X")
        assert one["rows"] == [[1]]
        bad_params = await query_tool(client, named_query="DemoShipmentsByPeriod", parameters_json="[1]")
        assert bad_params["code"] == "bad_request"
        broken = await report_tool(client, "DemoSales", parameters_json="{")
        assert broken["code"] == "bad_request"
        missing = await report_tool(client, "NoSuchReport")
        assert missing["status"] == 404
        missing_job = await job_get_tool(client, "00000000-0000-0000-0000-000000000000")
        assert missing_job["status"] == 404
        accepted = await query_tool(client, text="ВЫБРАТЬ 1", async_mode=True)
        done = await job_get_tool(client, accepted["job_id"])
        assert done["status"] == "succeeded"
    finally:
        await client.aclose()


async def test_write_tools_against_mock() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(
        Settings(onec_base_url="http://adapter", onec_token=WRITE_DEV_TOKEN),
        transport=transport,
    )
    try:
        bad_item = await data_dry_run_tool(client, "catalog", "DemoCounterparties", "[")
        assert bad_item["code"] == "bad_request"
        item = '{"Description":"ООО Инструмент","INN":"7700000099"}'
        dry = await data_dry_run_tool(client, "catalog", "DemoCounterparties", item)
        created = await data_create_tool(
            client,
            "catalog",
            "DemoCounterparties",
            item,
            dry["confirm_token"],
            "idem-tool-1",
            session_id="sess-tool",
        )
        new_id = created["ref"]["id"]
        patched_item = f'{{"Description":"ООО Инструмент-2","INN":"7700000099","id":"{new_id}"}}'
        patch_dry = await data_dry_run_tool(client, "catalog", "DemoCounterparties", patched_item)
        patched = await data_patch_tool(
            client,
            "catalog",
            "DemoCounterparties",
            new_id,
            patched_item,
            patch_dry["confirm_token"],
            "idem-tool-patch",
            session_id="sess-tool",
        )
        assert patched["ref"]["id"] == new_id
        unknown = await action_tool(client, "NoSuchAction", "{}")
        assert unknown["status"] == 404
        rolled = await session_rollback_tool(client, "sess-tool")
        assert rolled["undone"]
        denied = OneCClient(
            Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN),
            transport=transport,
        )
        try:
            blocked = await data_dry_run_tool(
                denied,
                "catalog",
                "DemoCounterparties",
                '{"Description":"X"}',
            )
            assert blocked["status"] == 403
        finally:
            await denied.aclose()
    finally:
        await client.aclose()
