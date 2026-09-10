from __future__ import annotations

import json
from pathlib import Path

from onecmcp import __version__
from onecmcp.presets import (
    dictionary_seed,
    list_scenario_catalog,
    scenario_guide,
)
from onecmcp.tools import guide_tool

ROOT = Path(__file__).resolve().parents[1]
CONNECT = ROOT / "docs" / "connect"


def test_guide_rest_on_question(gateway_client) -> None:
    response = gateway_client.get("/guide", params={"q": "покажи отчёт по продажам за август"})
    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["id"] == "sales_for_period"
    assert body["playbook"] == "report"
    tools = [step["tool"] for step in body["steps"]]
    assert "report" in tools
    assert "meta_search" in tools


def test_guide_catalog_without_query(gateway_client) -> None:
    response = gateway_client.get("/guide")
    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["scenarios"]}
    assert {
        "sales_for_period",
        "orders_count",
        "cash_request_approval",
        "period_reports",
        "primary_from_mail",
    } <= ids
    assert body["product_license"] == "not_required"


def test_write_playbook_uses_dry_run() -> None:
    guided = scenario_guide("введи поступление из письма", "ut11")
    assert guided["matched"] is True
    assert guided["id"] == "primary_from_mail"
    assert guided["playbook"] == "write"
    tools = [step["tool"] for step in guided["steps"]]
    assert "data_dry_run" in tools
    assert "data_create" in tools
    assert guided["likely_object"]["name"] == "ПриобретениеТоваровУслуг"


def test_primary_from_mail_on_bp() -> None:
    guided = guide_tool("накладная из почты", preset="bp30")
    assert guided["likely_object"]["name"] == "ПоступлениеТоваровУслуг"


def test_cash_request_and_reports_pack() -> None:
    cash = scenario_guide("согласуй заявку на расход", "erp2")
    assert cash["id"] == "cash_request_approval"
    assert cash["likely_object"]["name"] == "ЗаявкаНаРасходованиеДенежныхСредств"
    pack = scenario_guide("собери отчётность по звонку", "bp30")
    assert pack["id"] == "period_reports"
    assert pack["playbook"] == "report"


def test_dictionary_seed_has_public_names() -> None:
    rows = dictionary_seed("ut11")
    names = {row["name"] for row in rows}
    assert "РеализацияТоваровУслуг" in names
    assert "ЗаказКлиента" in names
    for row in rows:
        assert row["kind"]
        assert row["name"]
        assert "synonyms" in row


def test_connection_kits_parse() -> None:
    desktop = json.loads((CONNECT / "claude-desktop.mcp.json").read_text(encoding="utf-8"))
    assert desktop["mcpServers"]["1cmcp"]["args"] == ["-m", "onecmcp", "mcp"]
    cursor = json.loads((CONNECT / "cursor.mcp.json").read_text(encoding="utf-8"))
    assert cursor["mcpServers"]["1cmcp"]["env"]["ONEC_PRESET"]
    n8n = json.loads((CONNECT / "n8n-guide.json").read_text(encoding="utf-8"))
    dumped = json.dumps(n8n)
    assert "/guide" in dumped
    assert "LICENSE_KEY" not in dumped


def test_catalog_helper_lists_playbooks() -> None:
    catalog = list_scenario_catalog("auto")
    playbooks = {item["playbook"] for item in catalog["scenarios"]}
    assert {"read", "report", "write"} <= playbooks
    assert catalog["version"] == __version__
