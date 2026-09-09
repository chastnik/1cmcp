from __future__ import annotations

import httpx

from onecmcp.client import AdapterError, OneCClient, _payload
from onecmcp.config import Settings, load_settings
from onecmcp.mock1c import DEMO_CATALOG, DEV_TOKEN, create_mock_app
from onecmcp.tools import data_list_tool, health_tool, meta_describe_tool, meta_search_tool


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
