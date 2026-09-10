from __future__ import annotations

from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from onecmcp import __version__
from onecmcp.app import create_app
from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mcp_server import create_mcp
from onecmcp.mock1c import DEV_TOKEN, WRITE_DEV_TOKEN, WRITE_ONLY_TOKEN, bearer_headers, create_mock_app
from onecmcp.tools import audit_list_tool, meta_list_tool

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "extension" / "src"
HELM = ROOT / "deploy" / "helm" / "onecmcp"

ITEM = {
    "Number": "000000201",
    "Date": "2026-09-10",
    "Counterparty": {"id": "8a996f93-36c8-4bcf-b707-f75b8b4bc5e3"},
    "Amount": 10.0,
    "Quantity": 1,
}


def _adapter() -> TestClient:
    return TestClient(create_mock_app())


def _gateway() -> TestClient:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN)
    return TestClient(create_app(settings, adapter_transport=transport))


def test_version_is_080() -> None:
    assert __version__ == "0.9.0"
    chart = (HELM / "Chart.yaml").read_text(encoding="utf-8")
    assert 'appVersion: "0.9.0"' in chart
    version = (SRC / "Configuration.xml").read_text(encoding="utf-8")
    assert "<Version>0.9.0</Version>" in version


def test_audit_requires_read_scope() -> None:
    client = _adapter()
    assert client.get("/v1/audit").status_code == 401
    denied = client.get("/v1/audit", headers=bearer_headers(WRITE_ONLY_TOKEN))
    assert denied.status_code == 403
    ok = client.get("/v1/audit", headers=bearer_headers(DEV_TOKEN))
    assert ok.status_code == 200
    body = ok.json()
    assert body["content_kind"] == "data"
    assert "items" in body


def test_audit_lists_own_calls_not_health() -> None:
    client = _adapter()
    client.get("/v1/health")
    client.get("/v1/meta", headers=bearer_headers(DEV_TOKEN))
    page = client.get("/v1/audit", headers=bearer_headers(DEV_TOKEN)).json()
    paths = [row["path"] for row in page["items"]]
    assert "/v1/meta" in paths
    assert "/v1/health" not in paths
    assert all(row["method"] for row in page["items"])
    assert all("duration_ms" in row for row in page["items"])
    assert all("at" in row for row in page["items"])


def test_audit_since_and_path_filters() -> None:
    client = _adapter()
    client.get("/v1/meta", headers=bearer_headers(DEV_TOKEN))
    client.get("/v1/data/catalog/DemoCounterparties", headers=bearer_headers(DEV_TOKEN))
    empty = client.get(
        "/v1/audit",
        headers=bearer_headers(DEV_TOKEN),
        params={"since": "2099-01-01T00:00:00Z"},
    ).json()
    assert empty["items"] == []
    only_data = client.get(
        "/v1/audit",
        headers=bearer_headers(DEV_TOKEN),
        params={"path": "/v1/data"},
    ).json()
    assert only_data["items"]
    assert all(row["path"].startswith("/v1/data") for row in only_data["items"])


def test_audit_isolates_clients() -> None:
    client = _adapter()
    client.get("/v1/meta", headers=bearer_headers(DEV_TOKEN))
    other = client.get("/v1/audit", headers=bearer_headers(WRITE_DEV_TOKEN)).json()
    paths = [row["path"] for row in other["items"]]
    assert "/v1/meta" not in paths


def test_audit_limit_and_created_refs() -> None:
    client = _adapter()
    client.get("/v1/meta", headers=bearer_headers(WRITE_DEV_TOKEN))
    dry = client.post(
        "/v1/data/document/DemoShipments/dry-run",
        headers=bearer_headers(WRITE_DEV_TOKEN),
        json={"item": ITEM},
    )
    token = dry.json()["confirm_token"]
    created = client.post(
        "/v1/data/document/DemoShipments",
        headers={**bearer_headers(WRITE_DEV_TOKEN), "Idempotency-Key": "audit-key-01"},
        json={"item": ITEM, "confirm_token": token},
    )
    assert created.status_code == 201
    ref = created.json()["ref"]
    page = client.get(
        "/v1/audit",
        headers=bearer_headers(WRITE_DEV_TOKEN),
        params={"limit": 1, "path": "/v1/data/document/DemoShipments"},
    ).json()
    assert len(page["items"]) == 1
    assert page["items"][0]["path"].startswith("/v1/data/document/DemoShipments")
    assert ref in page["items"][0]["created_refs"]


def test_gateway_proxies_audit() -> None:
    with _gateway() as gw:
        gw.get("/v1/meta")
        page = gw.get("/v1/audit").json()
    assert page["content_kind"] == "data"
    assert any(row["path"] == "/v1/meta" for row in page["items"])


async def test_mcp_audit_list_tool() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN), transport=transport)
    try:
        await meta_list_tool(client)
        page = await audit_list_tool(client, limit=20, path="/v1/meta")
        assert page["content_kind"] == "data"
        assert any(row["path"] == "/v1/meta" for row in page["items"])
    finally:
        await client.aclose()
    names = {tool.name for tool in create_mcp()._tool_manager.list_tools()}
    assert "audit_list" in names


def test_extension_audit_route_and_refs_field() -> None:
    http = (SRC / "HTTPServices" / "мкпAPI.xml").read_text(encoding="utf-8")
    assert "/v1/audit" in http
    assert "AuditGET" in http
    module = (SRC / "HTTPServices" / "мкпAPI" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "Функция AuditGET" in module
    router = (SRC / "CommonModules" / "мкпМаршрутизатор" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "/v1/audit" in router
    journal = (SRC / "InformationRegisters" / "мкпЖурналВызовов.xml").read_text(encoding="utf-8")
    assert "СсылкиJSON" in journal
    security = (SRC / "CommonModules" / "мкпБезопасность" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "ЖурналКлиента" in security
    assert "СсылкиJSON" in security
