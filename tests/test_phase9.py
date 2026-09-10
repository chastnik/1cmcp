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
from onecmcp.tools import job_list_tool

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "extension" / "src"
HELM = ROOT / "deploy" / "helm" / "onecmcp"

AUGUST = {
    "BeginDate": "2026-08-01",
    "EndDate": "2026-08-31",
    "Counterparty": {"id": "8a996f93-36c8-4bcf-b707-f75b8b4bc5e3"},
}


def _adapter() -> TestClient:
    return TestClient(create_mock_app())


def _start_query(client: TestClient, token: str = WRITE_DEV_TOKEN) -> str:
    accepted = client.post(
        "/v1/query",
        json={"named_query": "DemoShipmentsByPeriod", "parameters": AUGUST, "async": True},
        headers=bearer_headers(token),
    )
    assert accepted.status_code == 202
    return accepted.json()["job_id"]


def test_version_is_0100() -> None:
    assert __version__ == "0.11.0"
    chart = (HELM / "Chart.yaml").read_text(encoding="utf-8")
    assert 'appVersion: "0.11.0"' in chart
    version = (SRC / "Configuration.xml").read_text(encoding="utf-8")
    assert "<Version>0.11.0</Version>" in version
    spec = (ROOT / "specs" / "openapi.yaml").read_text(encoding="utf-8")
    assert "version: 0.11.0" in spec
    assert "operationId: listJobs" in spec
    assert "JobListPage" in spec


def test_job_list_requires_read_scope() -> None:
    client = _adapter()
    assert client.get("/v1/job").status_code == 401
    denied = client.get("/v1/job", headers=bearer_headers(WRITE_ONLY_TOKEN))
    assert denied.status_code == 403
    empty = client.get("/v1/job", headers=bearer_headers(DEV_TOKEN))
    assert empty.status_code == 200
    body = empty.json()
    assert body["content_kind"] == "data"
    assert body["items"] == []


def test_job_list_own_jobs_not_others() -> None:
    client = _adapter()
    job_id = _start_query(client, WRITE_DEV_TOKEN)
    own = client.get("/v1/job", headers=bearer_headers(WRITE_DEV_TOKEN)).json()
    ids = [row["job_id"] for row in own["items"]]
    assert job_id in ids
    assert own["items"][0]["operation"] == "query"
    assert own["items"][0]["status"] == "succeeded"
    assert "at" in own["items"][0]
    assert "result" not in own["items"][0]
    other = client.get("/v1/job", headers=bearer_headers(DEV_TOKEN)).json()
    assert other["items"] == []
    hidden = client.get(f"/v1/job/{job_id}", headers=bearer_headers(DEV_TOKEN))
    assert hidden.status_code == 404
    visible = client.get(f"/v1/job/{job_id}", headers=bearer_headers(WRITE_DEV_TOKEN))
    assert visible.status_code == 200
    assert visible.json()["result"]["content_kind"] == "data"


def test_job_list_limit() -> None:
    client = _adapter()
    _start_query(client, WRITE_DEV_TOKEN)
    client.post(
        "/v1/job",
        json={"operation": "report", "payload": {"name": "DemoSales", "parameters": AUGUST}},
        headers=bearer_headers(WRITE_DEV_TOKEN),
    )
    page = client.get("/v1/job", headers=bearer_headers(WRITE_DEV_TOKEN), params={"limit": 1}).json()
    assert len(page["items"]) == 1


def test_gateway_proxies_job_list() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=WRITE_DEV_TOKEN)
    with TestClient(create_app(settings, adapter_transport=transport)) as gw:
        accepted = gw.post(
            "/v1/query",
            json={"named_query": "DemoShipmentsByPeriod", "parameters": AUGUST, "async": True},
        )
        assert accepted.status_code == 202
        page = gw.get("/v1/job").json()
    assert page["content_kind"] == "data"
    assert any(row["job_id"] == accepted.json()["job_id"] for row in page["items"])


async def test_mcp_job_list_tool() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(
        Settings(onec_base_url="http://adapter", onec_token=WRITE_DEV_TOKEN),
        transport=transport,
    )
    try:
        empty = await job_list_tool(client)
        assert empty["items"] == []
    finally:
        await client.aclose()
    names = {tool.name for tool in create_mcp()._tool_manager.list_tools()}
    assert "job_list" in names


def test_extension_job_list_route() -> None:
    http = (SRC / "HTTPServices" / "мкпAPI.xml").read_text(encoding="utf-8")
    assert "JobListGET" in http
    module = (SRC / "HTTPServices" / "мкпAPI" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "Функция JobListGET" in module
    jobs = (SRC / "CommonModules" / "мкпЗадания" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "СписокКлиента" in jobs
    router = (SRC / "CommonModules" / "мкпМаршрутизатор" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "СписокКлиента" in router
