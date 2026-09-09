from __future__ import annotations

from onecmcp import __version__
from onecmcp.mock1c import DEMO_CATALOG, DEMO_ID_ROMA


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
