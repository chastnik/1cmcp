from __future__ import annotations

import httpx
import pytest

from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mcp_server import _client, create_mcp
from onecmcp.mock1c import DEMO_CATALOG, DEMO_ID_ROMA, DEV_TOKEN, WRITE_DEV_TOKEN, create_mock_app


def test_mcp_registers_discovery_tools() -> None:
    server = create_mcp()
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert {
        "health",
        "diag",
        "guide",
        "meta_search",
        "meta_describe",
        "meta_list",
        "data_list",
        "data_get",
        "report",
        "query",
        "job_get",
        "data_dry_run",
        "data_create",
        "data_patch",
        "data_post",
        "action",
        "session_rollback",
        "session_get",
        "audit_list",
    } <= names


async def test_mcp_tools_call_adapter() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN)

    def make_client() -> OneCClient:
        return OneCClient(settings, transport=transport)

    server = create_mcp(settings, make_client=make_client)
    health = await server._tool_manager.get_tool("health").fn()
    assert health["status"] == "ok"

    found = await server._tool_manager.get_tool("meta_search").fn(query="контрагент")
    assert found["items"][0]["name"] == DEMO_CATALOG["name"]

    guided = await server._tool_manager.get_tool("guide").fn(question="продажи за август")
    assert guided["matched"] is True

    listed = await server._tool_manager.get_tool("meta_list").fn(kind="catalog")
    assert listed["items"][0]["name"] == DEMO_CATALOG["name"]

    card = await server._tool_manager.get_tool("meta_describe").fn(
        kind="catalog", name="DemoCounterparties"
    )
    assert card["kind"] == "catalog"

    page = await server._tool_manager.get_tool("data_list").fn(
        kind="catalog", name="DemoCounterparties"
    )
    assert page["content_kind"] == "data"

    item = await server._tool_manager.get_tool("data_get").fn(
        kind="catalog", name="DemoCounterparties", id=DEMO_ID_ROMA
    )
    assert item["item"]["Description"] == "ООО Ромашка"

    sales = await server._tool_manager.get_tool("report").fn(
        name="DemoSales",
        parameters='{"BeginDate":"2026-08-01","EndDate":"2026-08-31"}',
    )
    assert sales["body"]["totals"]["Amount"] == 180000.0

    queried = await server._tool_manager.get_tool("query").fn(text="ВЫБРАТЬ 1")
    assert queried["rows"] == [[1]]

    accepted = await server._tool_manager.get_tool("query").fn(
        named_query="DemoShipmentsByPeriod",
        parameters='{"BeginDate":"2026-08-01","EndDate":"2026-08-31"}',
        async_mode=True,
    )
    assert "job_id" in accepted
    job = await server._tool_manager.get_tool("job_get").fn(id=accepted["job_id"])
    assert job["status"] == "succeeded"


async def test_mcp_write_tools() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=WRITE_DEV_TOKEN)

    def make_client() -> OneCClient:
        return OneCClient(settings, transport=transport)

    server = create_mcp(settings, make_client=make_client)
    item = (
        '{"Number":"000000077","Date":"2026-09-09",'
        f'"Counterparty":{{"id":"{DEMO_ID_ROMA}"}},"Amount":10}}'
    )
    dry = await server._tool_manager.get_tool("data_dry_run").fn(
        kind="document", name="DemoShipments", item=item
    )
    assert dry["confirm_token"].startswith("dry-")
    created = await server._tool_manager.get_tool("data_create").fn(
        kind="document",
        name="DemoShipments",
        item=item,
        confirm_token=dry["confirm_token"],
        idempotency_key="idem-mcp-1",
        session_id="sess-mcp",
    )
    new_id = created["ref"]["id"]
    post_item = (
        '{"Number":"000000077","Date":"2026-09-09",'
        f'"Counterparty":{{"id":"{DEMO_ID_ROMA}"}},"Amount":10,"id":"{new_id}"}}'
    )
    post_dry = await server._tool_manager.get_tool("data_dry_run").fn(
        kind="document", name="DemoShipments", item=post_item, post=True
    )
    posted = await server._tool_manager.get_tool("data_post").fn(
        kind="document",
        name="DemoShipments",
        id=new_id,
        confirm_token=post_dry["confirm_token"],
        idempotency_key="idem-mcp-post",
        session_id="sess-mcp",
    )
    assert posted["posted"] is True
    rolled = await server._tool_manager.get_tool("session_rollback").fn(session_id="sess-mcp")
    assert rolled["session_id"] == "sess-mcp"
    unknown = await server._tool_manager.get_tool("action").fn(name="DropDatabase", arguments="{}")
    assert unknown["status"] == 404


async def test_client_context_closes_and_skips_empty() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN)

    async with _client(lambda: OneCClient(settings, transport=transport)) as client:
        body = await client.health()
        assert body["service"] == "1cmcp"

    empty = _client(lambda: OneCClient(settings, transport=transport))
    await empty.__aexit__(None, None, None)


async def test_mcp_default_factory_connects() -> None:
    server = create_mcp(Settings(onec_base_url="http://127.0.0.1:9"))
    with pytest.raises(httpx.HTTPError):
        await server._tool_manager.get_tool("health").fn()
