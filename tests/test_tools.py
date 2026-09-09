from __future__ import annotations

import httpx

from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mock1c import DEMO_CATALOG, create_mock_app
from onecmcp.tools import data_list_tool, health_tool, meta_describe_tool, meta_search_tool


async def test_discovery_tools_against_mock() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter"), transport=transport)
    try:
        health = await health_tool(client)
        assert health["status"] == "ok"

        found = await meta_search_tool(client, "ромашка")
        assert found["items"][0]["name"] == DEMO_CATALOG["name"]
        assert found["content_kind"] == "data"

        card = await meta_describe_tool(client, "catalog", "DemoCounterparties")
        assert card["kind"] == "catalog"

        page = await data_list_tool(client, "catalog", "DemoCounterparties")
        assert page["content_kind"] == "data"
        assert page["has_more"] is False
    finally:
        await client.aclose()


async def test_unknown_object_is_problem_json() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter"), transport=transport)
    try:
        payload = await meta_describe_tool(client, "catalog", "Несуществующий")
        assert payload["code"] == "not_found"
        assert payload["status"] == 404
    finally:
        await client.aclose()
