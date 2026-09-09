from __future__ import annotations

import httpx

from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mcp_server import create_mcp
from onecmcp.mock1c import DEV_TOKEN, create_mock_app
from onecmcp.presets import (
    KNOWN_PRESETS,
    load_pack,
    mcp_instructions,
    merge_search_items,
    normalize_preset,
    scenario_guide,
    search_entries,
)
from onecmcp.tools import guide_tool, meta_search_tool


def test_packs_load_and_extend() -> None:
    ut = load_pack("ut11")
    erp = load_pack("erp2")
    names_ut = {item["name"] for item in ut["entries"]}
    names_erp = {item["name"] for item in erp["entries"]}
    assert "ЗаказКлиента" in names_ut
    assert "РеализацияТоваровУслуг" in names_ut
    assert "ЗаказКлиента" in names_erp
    assert "ЗаказНаПроизводство" in names_erp
    assert set(KNOWN_PRESETS) == {"ut11", "ka2", "erp2", "bp30"}
    assert normalize_preset("БП") == "bp30"
    assert normalize_preset("none") == "none"


def test_search_orders_and_sales() -> None:
    orders = search_entries("сколько пришло заказов", "ut11")
    assert any(item["name"] == "ЗаказКлиента" for item in orders)
    sales = search_entries("отчет по продажам", "bp30")
    assert any(item["name"] == "РеализацияТоваровУслуг" for item in sales)
    bp_orders = search_entries("заказы", "bp30")
    assert any(item["name"] == "СчетНаОплатуПокупателю" for item in bp_orders)


def test_merge_keeps_adapter_hits_first() -> None:
    remote = [{"kind": "catalog", "name": "DemoCounterparties", "synonym": "Демо"}]
    merged = merge_search_items(remote, "контрагент", "auto", limit=20)
    assert merged[0]["name"] == "DemoCounterparties"
    assert any(item["name"] == "Контрагенты" and item.get("source") == "preset" for item in merged)


def test_guide_sales_and_orders() -> None:
    sales = scenario_guide("Покажи отчет по продажам за август", "ut11")
    assert sales["matched"] is True
    assert sales["id"] == "sales_for_period"
    assert sales["likely_object"]["name"] == "РеализацияТоваровУслуг"
    assert sales["steps"][0]["tool"] == "meta_search"

    orders = guide_tool("Сколько пришло заказов за март?", preset="erp2")
    assert orders["id"] == "orders_count"
    assert orders["likely_object"]["name"] == "ЗаказКлиента"

    bp = guide_tool("сколько пришло заказов", preset="bp30")
    assert bp["likely_object"]["name"] == "СчетНаОплатуПокупателю"

    unknown = scenario_guide("какая погода в Москве", "none")
    assert unknown["matched"] is False


async def test_meta_search_injects_preset_hints() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN), transport=transport)
    try:
        found = await meta_search_tool(client, "заказ", preset="ut11")
        names = [item["name"] for item in found["items"]]
        assert "ЗаказКлиента" in names
        demo = await meta_search_tool(client, "ромашка", preset="auto")
        assert demo["items"][0]["name"] == "DemoCounterparties"
    finally:
        await client.aclose()


def test_mcp_registers_guide_and_mentions_preset() -> None:
    server = create_mcp(Settings(onec_preset="bp30"))
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert "guide" in names
    assert "bp30" in mcp_instructions("bp30")
