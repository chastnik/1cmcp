from __future__ import annotations

import json
from pathlib import Path

import httpx
import yaml
from fastapi.testclient import TestClient

from onecmcp import __version__
from onecmcp.app import create_app
from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mcp_server import create_mcp
from onecmcp.mock1c import DEV_TOKEN, create_mock_app
from onecmcp.models import AdapterDiag, DiagCheck, GatewayDiag
from onecmcp.tools import diag_tool

ROOT = Path(__file__).resolve().parents[1]
HELM = ROOT / "deploy" / "helm" / "onecmcp"


def test_adapter_diag_without_token() -> None:
    with TestClient(create_mock_app()) as client:
        response = client.get("/v1/diag")
    assert response.status_code == 200
    body = response.json()
    parsed = AdapterDiag.model_validate(body)
    assert parsed.status == "ok"
    assert parsed.service == "1cmcp"
    assert parsed.version == __version__
    assert parsed.api == "v1"
    assert parsed.product_license == "not_required"
    assert parsed.compatibility.platform == "8.3.20+"
    assert parsed.compatibility.modes == ["file", "client_server"]
    assert parsed.publication.root_url == "mcp"
    assert parsed.publication.reuse_sessions == "AutoUse"
    assert parsed.publication.session_max_age == 20
    ids = {check.id: check for check in parsed.checks}
    assert ids["http_service"].ok is True
    assert ids["session_reuse"].ok is True
    assert ids["role"].ok is True
    assert ids["product_license"].ok is True
    assert ids["product_license"].detail == "not_required"


def test_gateway_diag_merges_adapter_and_hides_secrets(gateway_client) -> None:
    response = gateway_client.get("/diag")
    assert response.status_code == 200
    body = response.json()
    parsed = GatewayDiag.model_validate(body)
    assert parsed.status == "ok"
    assert parsed.service == "1cmcp-gateway"
    assert parsed.version == __version__
    assert parsed.product_license == "not_required"
    assert parsed.gateway.preset == "auto"
    assert parsed.gateway.meta_cache_ttl_seconds == 60.0
    assert parsed.gateway.tenant == "default"
    assert parsed.adapter is not None
    assert parsed.adapter.product_license == "not_required"
    dumped = json.dumps(body)
    assert DEV_TOKEN not in dumped
    assert "Authorization" not in dumped
    assert "onec_token" not in dumped


def test_gateway_proxies_adapter_diag(gateway_client) -> None:
    response = gateway_client.get("/v1/diag")
    assert response.status_code == 200
    assert response.json()["product_license"] == "not_required"


def test_gateway_diag_degraded_when_adapter_down() -> None:
    class FailingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("adapter down")

    secret = "super-secret-token-xyz"
    app = create_app(
        Settings(onec_base_url="http://adapter.internal:18080", onec_token=secret),
        adapter_transport=FailingTransport(),
    )
    with TestClient(app) as client:
        response = client.get("/diag")
    assert response.status_code == 200
    body = response.json()
    parsed = GatewayDiag.model_validate(body)
    assert parsed.status == "degraded"
    assert parsed.adapter is None
    ids = {check.id: check for check in parsed.checks}
    assert ids["adapter_reachable"].ok is False
    assert ids["product_license"].ok is True
    dumped = json.dumps(body)
    assert secret not in dumped
    assert parsed.gateway.adapter_host == "adapter.internal"


async def test_mcp_diag_tool() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN, onec_preset="ut11")

    def make_client() -> OneCClient:
        return OneCClient(settings, transport=transport)

    server = create_mcp(settings, make_client=make_client)
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert "diag" in names
    payload = await server._tool_manager.get_tool("diag").fn()
    parsed = GatewayDiag.model_validate(payload)
    assert parsed.status == "ok"
    assert parsed.gateway.preset == "ut11"
    assert parsed.product_license == "not_required"


async def test_diag_tool_helper() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN)
    client = OneCClient(settings, transport=transport)
    try:
        payload = await diag_tool(client, settings)
    finally:
        await client.aclose()
    assert payload["status"] == "ok"
    assert payload["adapter"]["service"] == "1cmcp"


def test_diag_models_roundtrip() -> None:
    check = DiagCheck(id="product_license", ok=True, detail="not_required")
    assert check.ok is True
    adapter = AdapterDiag(
        status="ok",
        service="1cmcp",
        version="0.5.0",
        api="v1",
        time="2026-09-09T20:00:00Z",
        product_license="not_required",
        compatibility={"platform": "8.3.20+", "modes": ["file", "client_server"]},
        publication={"root_url": "mcp", "reuse_sessions": "AutoUse", "session_max_age": 20},
        checks=[check],
    )
    assert adapter.publication.session_max_age == 20
    gateway = GatewayDiag(
        status="ok",
        service="1cmcp-gateway",
        version="0.5.0",
        api="v1",
        product_license="not_required",
        gateway={
            "preset": "auto",
            "meta_cache_ttl_seconds": 60,
            "tenant": "default",
            "adapter_host": "127.0.0.1",
        },
        adapter=adapter,
        checks=[check],
    )
    assert gateway.gateway.adapter_host == "127.0.0.1"


def test_helm_chart_ships_gateway_without_product_license() -> None:
    chart = yaml.safe_load((HELM / "Chart.yaml").read_text(encoding="utf-8"))
    assert chart["name"] == "onecmcp"
    assert chart["appVersion"] == __version__
    values = yaml.safe_load((HELM / "values.yaml").read_text(encoding="utf-8"))
    env = json.dumps(values)
    assert "LICENSE_KEY" not in env
    assert "product_license" not in env
    assert "onec" in values
    assert values["onec"]["baseUrl"]
    deployment = (HELM / "templates" / "deployment.yaml").read_text(encoding="utf-8")
    assert "ONEC_BASE_URL" in deployment
    assert "ONEC_TOKEN" in deployment
    assert "/health" in deployment or "/diag" in deployment


def test_compose_has_healthchecks() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert "healthcheck" in compose["services"]["mock1c"]
    assert "healthcheck" in compose["services"]["gateway"]
    gateway = json.dumps(compose["services"]["gateway"])
    assert "LICENSE" not in gateway
