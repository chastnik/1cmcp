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
from onecmcp.tools import session_get_tool

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "extension" / "src"
HELM = ROOT / "deploy" / "helm" / "onecmcp"

ITEM = {
    "Number": "000000301",
    "Date": "2026-09-10",
    "Counterparty": {"id": "8a996f93-36c8-4bcf-b707-f75b8b4bc5e3"},
    "Amount": 10.0,
    "Quantity": 1,
}


def _adapter() -> TestClient:
    return TestClient(create_mock_app())


def _gateway() -> TestClient:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=WRITE_DEV_TOKEN)
    return TestClient(create_app(settings, adapter_transport=transport))


def _create(client: TestClient, *, session: str, idempotency: str) -> str:
    dry = client.post(
        "/v1/data/document/DemoShipments/dry-run",
        headers=bearer_headers(WRITE_DEV_TOKEN),
        json={"item": ITEM},
    )
    created = client.post(
        "/v1/data/document/DemoShipments",
        headers={
            **bearer_headers(WRITE_DEV_TOKEN),
            "Idempotency-Key": idempotency,
            "X-Session-Id": session,
        },
        json={"item": ITEM, "confirm_token": dry.json()["confirm_token"]},
    )
    assert created.status_code == 201
    return created.json()["ref"]["id"]


def test_version_is_090() -> None:
    assert __version__ == "0.9.0"
    chart = (HELM / "Chart.yaml").read_text(encoding="utf-8")
    assert 'appVersion: "0.9.0"' in chart
    version = (SRC / "Configuration.xml").read_text(encoding="utf-8")
    assert "<Version>0.9.0</Version>" in version


def test_session_get_requires_read_scope() -> None:
    client = _adapter()
    assert client.get("/v1/session/sess-x").status_code == 401
    denied = client.get("/v1/session/sess-x", headers=bearer_headers(WRITE_ONLY_TOKEN))
    assert denied.status_code == 403
    empty = client.get("/v1/session/sess-x", headers=bearer_headers(DEV_TOKEN))
    assert empty.status_code == 200
    body = empty.json()
    assert body["content_kind"] == "data"
    assert body["session_id"] == "sess-x"
    assert body["items"] == []


def test_session_get_lists_own_ops_before_rollback() -> None:
    client = _adapter()
    new_id = _create(client, session="sess-preview", idempotency="idem-sess-1")
    page = client.get("/v1/session/sess-preview", headers=bearer_headers(WRITE_DEV_TOKEN)).json()
    assert page["content_kind"] == "data"
    assert page["session_id"] == "sess-preview"
    assert page["items"]
    assert page["items"][0]["op"] == "create"
    assert page["items"][0]["kind"] == "document"
    assert page["items"][0]["name"] == "DemoShipments"
    assert page["items"][0]["id"] == new_id
    other = client.get("/v1/session/sess-preview", headers=bearer_headers(DEV_TOKEN)).json()
    assert other["items"] == []


def test_session_rollback_isolates_clients() -> None:
    client = _adapter()
    new_id = _create(client, session="sess-shared", idempotency="idem-sess-iso")
    alien = client.post(
        "/v1/session/rollback",
        headers=bearer_headers(WRITE_ONLY_TOKEN),
        json={"session_id": "sess-shared"},
    )
    assert alien.status_code == 200
    assert alien.json()["undone"] == []
    still = client.get(
        f"/v1/data/document/DemoShipments/{new_id}",
        headers=bearer_headers(WRITE_DEV_TOKEN),
    )
    assert still.status_code == 200
    own = client.post(
        "/v1/session/rollback",
        headers=bearer_headers(WRITE_DEV_TOKEN),
        json={"session_id": "sess-shared"},
    )
    assert own.json()["undone"]
    gone = client.get(
        f"/v1/data/document/DemoShipments/{new_id}",
        headers=bearer_headers(WRITE_DEV_TOKEN),
    )
    assert gone.status_code == 404


def test_audit_carries_session_id() -> None:
    client = _adapter()
    _create(client, session="sess-audit", idempotency="idem-sess-audit")
    page = client.get(
        "/v1/audit",
        headers=bearer_headers(WRITE_DEV_TOKEN),
        params={"session": "sess-audit", "path": "/v1/data/document/DemoShipments"},
    ).json()
    assert page["items"]
    assert all(row.get("session_id") == "sess-audit" for row in page["items"])


def test_gateway_proxies_session_get() -> None:
    with _gateway() as gw:
        dry = gw.post("/v1/data/document/DemoShipments/dry-run", json={"item": ITEM})
        created = gw.post(
            "/v1/data/document/DemoShipments",
            headers={"Idempotency-Key": "idem-gw-sess", "X-Session-Id": "sess-gw"},
            json={"item": ITEM, "confirm_token": dry.json()["confirm_token"]},
        )
        assert created.status_code == 201
        page = gw.get("/v1/session/sess-gw").json()
    assert page["content_kind"] == "data"
    assert any(row["op"] == "create" for row in page["items"])


async def test_mcp_session_get_tool() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=WRITE_DEV_TOKEN)
    client = OneCClient(settings, transport=transport)
    try:
        empty = await session_get_tool(client, "sess-mcp-empty")
        assert empty["items"] == []
    finally:
        await client.aclose()
    names = {tool.name for tool in create_mcp()._tool_manager.list_tools()}
    assert "session_get" in names


def test_extension_session_get_route() -> None:
    http = (SRC / "HTTPServices" / "мкпAPI.xml").read_text(encoding="utf-8")
    assert "/v1/session/{session_id}" in http
    assert "SessionGetGET" in http
    module = (SRC / "HTTPServices" / "мкпAPI" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "Функция SessionGetGET" in module
    router = (SRC / "CommonModules" / "мкпМаршрутизатор" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "/v1/session/" in router
    data = (SRC / "CommonModules" / "мкпДанные" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "СессияКлиента" in data
    session_reg = (SRC / "InformationRegisters" / "мкпОперацииСессии.xml").read_text(encoding="utf-8")
    assert ">Клиент<" in session_reg or "<Name>Клиент</Name>" in session_reg
    journal = (SRC / "InformationRegisters" / "мкпЖурналВызовов.xml").read_text(encoding="utf-8")
    assert "<Name>Сессия</Name>" in journal
