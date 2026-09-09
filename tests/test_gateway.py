from __future__ import annotations

from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from onecmcp import __version__
from onecmcp.app import _openapi_path, create_app
from onecmcp.config import Settings
from onecmcp.mock1c import DEMO_CATALOG, DEMO_ID_ROMA, bearer_headers, create_mock_app


def test_gateway_liveness(gateway_client) -> None:
    response = gateway_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "1cmcp-gateway"


def test_ready_and_adapter_health(gateway_client) -> None:
    ready = gateway_client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["adapter"]["service"] == "1cmcp"

    health = gateway_client.get("/v1/health")
    assert health.status_code == 200
    body = health.json()
    assert body == {
        "status": "ok",
        "service": "1cmcp",
        "version": __version__,
        "api": "v1",
        "time": body["time"],
    }
    assert body["time"].endswith("Z")


def test_meta_search_finds_demo_catalog(gateway_client) -> None:
    response = gateway_client.get("/v1/meta/search", params={"q": "контрагент"})
    assert response.status_code == 200
    assert response.headers.get("x-1cmcp-content-kind") == "data"
    items = response.json()["items"]
    assert items[0]["name"] == DEMO_CATALOG["name"]
    assert items[0]["kind"] == "catalog"


def test_meta_describe_and_data_roundtrip(gateway_client) -> None:
    described = gateway_client.get("/v1/meta/catalog/DemoCounterparties")
    assert described.status_code == 200
    card = described.json()
    assert {field["name"] for field in card["fields"]} >= {"Description", "INN"}

    listing = gateway_client.get("/v1/data/catalog/DemoCounterparties")
    assert listing.status_code == 200
    page = listing.json()
    assert page["content_kind"] == "data"
    assert len(page["items"]) == 2

    item = gateway_client.get(f"/v1/data/catalog/DemoCounterparties/{DEMO_ID_ROMA}")
    assert item.status_code == 200
    envelope = item.json()
    assert envelope["item"]["Description"] == "ООО Ромашка"
    assert envelope["item"]["ref"]["ref"] == "Catalog.DemoCounterparties"


def test_future_operations_return_501_problem(gateway_client) -> None:
    response = gateway_client.post("/v1/query", json={"text": "ВЫБРАТЬ 1"})
    assert response.status_code == 501
    problem = response.json()
    assert problem["code"] == "not_implemented"
    assert problem["status"] == 501
    assert "application/problem+json" in response.headers.get("content-type", "")


def test_openapi_is_served(gateway_client) -> None:
    response = gateway_client.get("/openapi.yaml")
    assert response.status_code == 200
    assert b"/v1/health" in response.content


def test_meta_list_and_not_found_paths(gateway_client) -> None:
    listed = gateway_client.get("/v1/meta")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["name"] == DEMO_CATALOG["name"]

    documents = gateway_client.get("/v1/meta", params={"kind": "document"})
    assert documents.json()["items"][0]["name"] == "DemoShipments"

    empty = gateway_client.get("/v1/meta", params={"kind": "report"})
    assert empty.json()["items"] == []

    missing_list = gateway_client.get("/v1/data/catalog/Unknown")
    assert missing_list.status_code == 404

    missing_item = gateway_client.get(
        "/v1/data/catalog/DemoCounterparties/00000000-0000-0000-0000-000000000000"
    )
    assert missing_item.status_code == 404


def test_ready_when_adapter_down() -> None:
    class FailingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("adapter down")

    app = create_app(Settings(onec_base_url="http://adapter"), adapter_transport=FailingTransport())
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["code"] == "adapter_unavailable"


def test_create_app_default_settings() -> None:
    app = create_app()
    assert app.title == "1cmcp gateway"


def test_openapi_path_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    path = _openapi_path()
    assert path.name == "openapi.yaml"


def test_mock_app_direct_meta_limit() -> None:
    with TestClient(create_mock_app()) as client:
        response = client.get("/v1/meta", params={"kind": "catalog", "limit": 1}, headers=bearer_headers())
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
