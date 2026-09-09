from __future__ import annotations

import httpx
import pytest

from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mcp_server import _client, create_mcp
from onecmcp.mock1c import DEMO_CATALOG, create_mock_app


def test_mcp_registers_discovery_tools() -> None:
    server = create_mcp()
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert {"health", "meta_search", "meta_describe", "data_list"} <= names


async def test_mcp_tools_call_adapter() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter")

    def make_client() -> OneCClient:
        return OneCClient(settings, transport=transport)

    server = create_mcp(settings, make_client=make_client)
    health = await server._tool_manager.get_tool("health").fn()
    assert health["status"] == "ok"

    found = await server._tool_manager.get_tool("meta_search").fn(query="контрагент")
    assert found["items"][0]["name"] == DEMO_CATALOG["name"]

    card = await server._tool_manager.get_tool("meta_describe").fn(
        kind="catalog", name="DemoCounterparties"
    )
    assert card["kind"] == "catalog"

    page = await server._tool_manager.get_tool("data_list").fn(
        kind="catalog", name="DemoCounterparties"
    )
    assert page["content_kind"] == "data"


async def test_client_context_closes_and_skips_empty() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter")

    async with _client(lambda: OneCClient(settings, transport=transport)) as client:
        body = await client.health()
        assert body["service"] == "1cmcp"

    empty = _client(lambda: OneCClient(settings, transport=transport))
    await empty.__aexit__(None, None, None)


async def test_mcp_default_factory_connects() -> None:
    server = create_mcp(Settings(onec_base_url="http://127.0.0.1:9"))
    with pytest.raises(httpx.HTTPError):
        await server._tool_manager.get_tool("health").fn()
