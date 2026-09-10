from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from onecmcp import __version__
from onecmcp.app import create_app
from onecmcp.config import Settings, parse_tenant_map
from onecmcp.limits import RateLimiter
from onecmcp.mcp_server import create_mcp
from onecmcp.mock1c import WRITE_DEV_TOKEN, bearer_headers, create_mock_app
from onecmcp.models import GatewayDiag
from onecmcp.tracing import configure_tracing, install_memory_tracer, reset_tracing
from onecmcp.writes import check_client_limits

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "extension" / "src"
HELM = ROOT / "deploy" / "helm" / "onecmcp"
LIMITED_TOKEN = "dev-limit-token"

ITEM = {
    "Number": "000000199",
    "Date": "2026-09-10",
    "Counterparty": {"id": "8a996f93-36c8-4bcf-b707-f75b8b4bc5e3"},
    "Amount": 5000.0,
    "Quantity": 3,
}


def _gateway(settings: Settings | None = None) -> TestClient:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = settings or Settings(onec_base_url="http://adapter", onec_token=WRITE_DEV_TOKEN)
    app = create_app(settings, adapter_transport=transport)
    return TestClient(app)


def test_version_is_at_least_070() -> None:
    assert tuple(int(part) for part in __version__.split(".")[:2]) >= (0, 7)


def test_parse_tenant_map_csv_and_json() -> None:
    csv_map = parse_tenant_map(
        "erp=http://erp.internal/hs/mcp,bp=http://bp.internal/hs/mcp",
        default_id="default",
        default_url="http://127.0.0.1:18080",
    )
    assert csv_map["default"] == "http://127.0.0.1:18080"
    assert csv_map["erp"] == "http://erp.internal/hs/mcp"
    assert csv_map["bp"] == "http://bp.internal/hs/mcp"
    json_map = parse_tenant_map(
        '{"demo": "http://demo:18080/"}',
        default_id="demo",
        default_url="http://demo:18080",
    )
    assert json_map["demo"] == "http://demo:18080"


def test_rate_limiter_blocks_after_quota() -> None:
    limiter = RateLimiter(per_minute=2)
    assert limiter.allow("tok:a")[0] is True
    assert limiter.allow("tok:a")[0] is True
    allowed, retry_after = limiter.allow("tok:a")
    assert allowed is False
    assert retry_after >= 1
    assert limiter.allow("tok:b")[0] is True


def test_gateway_rate_limit_returns_429() -> None:
    settings = Settings(
        onec_base_url="http://adapter",
        onec_token=WRITE_DEV_TOKEN,
        rate_limit_per_minute=2,
    )
    with _gateway(settings) as client:
        assert client.get("/guide").status_code == 200
        assert client.get("/guide").status_code == 200
        limited = client.get("/guide")
        assert limited.status_code == 429
        assert limited.json()["code"] == "rate_limited"
        assert "application/problem+json" in limited.headers.get("content-type", "")
        assert limited.headers.get("Retry-After")
        health = client.get("/health")
        assert health.status_code == 200


def test_unknown_tenant_is_404() -> None:
    settings = Settings(
        onec_base_url="http://adapter",
        onec_token=WRITE_DEV_TOKEN,
        tenant="default",
        onec_tenants="erp=http://erp.internal",
    )
    with _gateway(settings) as client:
        missing = client.get("/v1/health", headers={"X-Tenant": "unknown"})
        assert missing.status_code == 404
        assert missing.json()["code"] == "unknown_tenant"
        ok = client.get("/v1/health", headers={"X-Tenant": "erp"})
        assert ok.status_code == 200
        path = client.get("/t/erp/v1/health")
        assert path.status_code == 200


def test_gateway_diag_lists_tenants_and_mcp_http() -> None:
    settings = Settings(
        onec_base_url="http://adapter",
        onec_token=WRITE_DEV_TOKEN,
        onec_tenants="erp=http://erp.internal",
        rate_limit_per_minute=60,
    )
    with _gateway(settings) as client:
        body = client.get("/diag").json()
    parsed = GatewayDiag.model_validate(body)
    assert parsed.gateway.mcp_http_path == "/mcp"
    assert parsed.gateway.rate_limit_per_minute == 60
    assert "default" in parsed.gateway.tenants
    assert "erp" in parsed.gateway.tenants
    dumped = json.dumps(body)
    assert WRITE_DEV_TOKEN not in dumped


def test_serve_exposes_streamable_http_mcp() -> None:
    with _gateway() as client:
        response = client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
    assert response.status_code != 404


def test_mcp_cli_streamable_http(monkeypatch) -> None:
    from onecmcp.__main__ import main

    calls: list[tuple] = []

    class FakeMcp:
        def run(self, transport: str, **kwargs: object) -> None:
            calls.append((transport, kwargs))

    monkeypatch.setattr("onecmcp.__main__.load_settings", lambda: Settings())
    monkeypatch.setattr("onecmcp.__main__.create_mcp", lambda settings: FakeMcp())
    monkeypatch.setattr(sys, "argv", ["onecmcp", "mcp", "--transport", "streamable-http", "--port", "9001"])
    main()
    assert calls[0][0] == "streamable-http"
    assert calls[0][1]["port"] == 9001


def test_mcp_cli_rejects_unknown_transport(monkeypatch) -> None:
    from onecmcp.__main__ import main

    monkeypatch.setattr(sys, "argv", ["onecmcp", "mcp", "--transport", "ftp"])
    with pytest.raises(SystemExit):
        main()


def test_client_amount_and_quantity_limits() -> None:
    ok = check_client_limits({"Amount": 100, "Quantity": 1}, max_amount=1000, max_quantity=10)
    assert ok == []
    amount = check_client_limits({"Amount": 5001, "СуммаДокумента": 1}, max_amount=5000, max_quantity=0)
    assert any("сумм" in msg.lower() for msg in amount)
    qty = check_client_limits(
        {"Товары": [{"Количество": 4}, {"Quantity": 1}]},
        max_amount=0,
        max_quantity=3,
    )
    assert any("количеств" in msg.lower() for msg in qty)


def test_mock_write_limit_exceeded() -> None:
    with TestClient(create_mock_app()) as client:
        headers = bearer_headers(LIMITED_TOKEN)
        preview = client.post(
            "/v1/data/document/DemoShipments/dry-run",
            json={"item": ITEM, "post": False},
            headers=headers,
        )
        assert preview.status_code == 200
        assert any("лимит" in msg.lower() or "сумм" in msg.lower() for msg in preview.json()["fill_check"])
        token = preview.json()["confirm_token"]
        headers = {**headers, "Idempotency-Key": "limit-key-01"}
        created = client.post(
            "/v1/data/document/DemoShipments",
            json={"item": ITEM, "confirm_token": token},
            headers=headers,
        )
        assert created.status_code == 400
        assert created.json()["code"] == "limit_exceeded"


def test_tracing_records_http_span() -> None:
    exporter = install_memory_tracer()
    try:
        with _gateway() as client:
            assert client.get("/health").status_code == 200
        names = [span.name for span in exporter.get_finished_spans()]
        assert "http.request" in names
    finally:
        reset_tracing()


def test_configure_tracing_without_endpoint_is_noop() -> None:
    configure_tracing(Settings(otel_exporter_otlp_endpoint=""))


def test_extension_has_client_limits_and_version() -> None:
    catalog = (SRC / "Catalogs" / "мкпКлиентыИнтеграции.xml").read_text(encoding="utf-8")
    assert "ЛимитСуммы" in catalog
    assert "ЛимитКоличества" in catalog
    security = (SRC / "CommonModules" / "мкпБезопасность" / "Ext" / "Module.bsl").read_text(
        encoding="utf-8"
    )
    assert "Функция ПроверитьЛимитыКлиента" in security
    data = (SRC / "CommonModules" / "мкпДанные" / "Ext" / "Module.bsl").read_text(encoding="utf-8")
    assert "ПроверитьЛимитыКлиента" in data
    version = (SRC / "Configuration.xml").read_text(encoding="utf-8")
    assert "<Version>0.10.0</Version>" in version


def test_helm_exposes_rate_limit_and_tenants() -> None:
    values = (HELM / "values.yaml").read_text(encoding="utf-8")
    deployment = (HELM / "templates" / "deployment.yaml").read_text(encoding="utf-8")
    assert "rateLimitPerMinute" in values
    assert "RATE_LIMIT_PER_MINUTE" in deployment
    assert "ONEC_TENANTS" in deployment
    assert create_mcp() is not None
