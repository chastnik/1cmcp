from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from onecmcp.app import create_app
from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mock1c import (
    DEMO_ID_ROMA,
    DENIED_SHIPMENTS_TOKEN,
    DEV_TOKEN,
    WRITE_ONLY_TOKEN,
    bearer_headers,
    call_log,
    create_mock_app,
)
from onecmcp.tools import data_get_tool, data_list_tool, meta_list_tool, meta_search_tool


AUGUST_FILTER = json.dumps(
    {
        "Date": {"gte": "2026-08-01", "lte": "2026-08-31"},
        "Counterparty": {"id": DEMO_ID_ROMA},
    }
)


def test_future_route_without_token_is_unauthorized() -> None:
    with TestClient(create_mock_app()) as client:
        response = client.post("/v1/query", json={"text": "ВЫБРАТЬ 1"})
    assert response.status_code == 401


def test_health_without_token() -> None:
    with TestClient(create_mock_app()) as client:
        response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_meta_and_data_require_bearer() -> None:
    with TestClient(create_mock_app()) as client:
        meta = client.get("/v1/meta")
        data = client.get("/v1/data/catalog/DemoCounterparties")
        bad = client.get("/v1/meta", headers=bearer_headers("no-such-token"))
    assert meta.status_code == 401
    assert meta.json()["code"] == "unauthorized"
    assert data.status_code == 401
    assert bad.status_code == 401


def test_write_only_token_is_forbidden() -> None:
    with TestClient(create_mock_app()) as client:
        response = client.get("/v1/meta", headers=bearer_headers(WRITE_ONLY_TOKEN))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_acl_denies_shipments_but_allows_catalog() -> None:
    with TestClient(create_mock_app()) as client:
        catalog = client.get(
            "/v1/meta/catalog/DemoCounterparties",
            headers=bearer_headers(DENIED_SHIPMENTS_TOKEN),
        )
        shipments = client.get(
            "/v1/data/document/DemoShipments",
            headers=bearer_headers(DENIED_SHIPMENTS_TOKEN),
        )
    assert catalog.status_code == 200
    assert shipments.status_code == 403


def test_connector_objects_are_hidden() -> None:
    with TestClient(create_mock_app()) as client:
        listed = client.get("/v1/meta", headers=bearer_headers())
        hidden = client.get("/v1/meta/catalog/мкпКлиентыИнтеграции", headers=bearer_headers())
        names = [item["name"] for item in listed.json()["items"]]
    assert all(not name.startswith("мкп") for name in names)
    assert hidden.status_code == 404


def test_semantic_search_finds_shipments_by_otgruzka() -> None:
    with TestClient(create_mock_app()) as client:
        response = client.get(
            "/v1/meta/search",
            params={"q": "отгрузка"},
            headers=bearer_headers(),
        )
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert "DemoShipments" in names


def test_august_shipments_for_romashka() -> None:
    with TestClient(create_mock_app()) as client:
        described = client.get("/v1/meta/document/DemoShipments", headers=bearer_headers())
        listing = client.get(
            "/v1/data/document/DemoShipments",
            params={"filter": AUGUST_FILTER},
            headers=bearer_headers(),
        )
    assert described.status_code == 200
    field_names = {field["name"] for field in described.json()["fields"]}
    assert {"Date", "Amount", "Counterparty"} <= field_names

    page = listing.json()
    assert page["content_kind"] == "data"
    assert len(page["items"]) == 2
    total = sum(item["Amount"] for item in page["items"])
    assert total == 150000.0
    assert all(item["Counterparty"]["id"] == DEMO_ID_ROMA for item in page["items"])
    assert all(item["Date"].startswith("2026-08-") for item in page["items"])


def test_pagination_and_get_by_id() -> None:
    with TestClient(create_mock_app()) as client:
        first = client.get(
            "/v1/data/document/DemoShipments",
            params={"limit": 1},
            headers=bearer_headers(),
        )
        body = first.json()
        assert body["has_more"] is True
        second = client.get(
            "/v1/data/document/DemoShipments",
            params={"limit": 1, "cursor": body["next_cursor"]},
            headers=bearer_headers(),
        )
        item_id = body["items"][0]["id"]
        got = client.get(
            f"/v1/data/document/DemoShipments/{item_id}",
            headers=bearer_headers(),
        )
    assert second.status_code == 200
    assert second.json()["items"][0]["id"] != item_id
    assert got.status_code == 200
    assert got.json()["item"]["id"] == item_id


def test_invalid_filter_and_fields_projection() -> None:
    with TestClient(create_mock_app()) as client:
        bad = client.get(
            "/v1/data/catalog/DemoCounterparties",
            params={"filter": "not-json"},
            headers=bearer_headers(),
        )
        not_object = client.get(
            "/v1/data/catalog/DemoCounterparties",
            params={"filter": "[]"},
            headers=bearer_headers(),
        )
        projected = client.get(
            "/v1/data/catalog/DemoCounterparties",
            params={"filter": json.dumps({"INN": "7701234567"}), "fields": "Description,INN"},
            headers=bearer_headers(),
        )
        contains = client.get(
            "/v1/data/catalog/DemoCounterparties",
            params={"filter": json.dumps({"Description": {"contains": "Ромашка"}})},
            headers=bearer_headers(),
        )
        amount = client.get(
            "/v1/data/document/DemoShipments",
            params={"filter": json.dumps({"Amount": {"gt": 40000, "lt": 110000}})},
            headers=bearer_headers(),
        )
        meta_page = client.get(
            "/v1/meta",
            params={"limit": 1},
            headers=bearer_headers(),
        )
        meta_next = client.get(
            "/v1/meta",
            params={"limit": 1, "cursor": meta_page.json()["next_cursor"]},
            headers=bearer_headers(),
        )
    assert bad.status_code == 400
    assert not_object.status_code == 400
    item = projected.json()["items"][0]
    assert item["Description"] == "ООО Ромашка"
    assert "id" in item
    assert "ref" in item
    assert contains.json()["items"][0]["Description"] == "ООО Ромашка"
    assert {row["Amount"] for row in amount.json()["items"]} == {50000.0, 100000.0}
    assert meta_page.json()["has_more"] is True
    assert meta_next.json()["items"][0]["name"] != meta_page.json()["items"][0]["name"]


def test_gateway_august_scenario(gateway_client) -> None:
    search = gateway_client.get("/v1/meta/search", params={"q": "реализация"})
    assert any(item["name"] == "DemoShipments" for item in search.json()["items"])
    listing = gateway_client.get(
        "/v1/data/document/DemoShipments",
        params={"filter": AUGUST_FILTER},
    )
    items = listing.json()["items"]
    assert len(items) == 2
    assert sum(item["Amount"] for item in items) == 150000.0


def test_gateway_without_token_is_unauthorized() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    app = create_app(Settings(onec_base_url="http://adapter", onec_token=""), adapter_transport=transport)
    with TestClient(app) as client:
        response = client.get("/v1/meta")
        health = client.get("/v1/health")
    assert response.status_code == 401
    assert health.status_code == 200


def test_call_log_records_meta() -> None:
    create_mock_app()
    with TestClient(create_mock_app()) as client:
        client.get("/v1/meta", headers=bearer_headers())
    paths = [entry["path"] for entry in call_log()]
    assert "/v1/meta" in paths


async def test_tools_cover_filter_and_get() -> None:
    transport = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN), transport=transport)
    try:
        listed = await meta_list_tool(client, kind="document")
        assert listed["items"][0]["name"] == "DemoShipments"
        found = await meta_search_tool(client, "август")
        assert any(item["name"] == "DemoShipments" for item in found["items"])
        page = await data_list_tool(
            client,
            "document",
            "DemoShipments",
            filter_json=AUGUST_FILTER,
        )
        assert len(page["items"]) == 2
        item = await data_get_tool(client, "document", "DemoShipments", page["items"][0]["id"])
        assert item["item"]["Amount"] in {100000.0, 50000.0}
        missing = await data_get_tool(client, "document", "DemoShipments", "00000000-0000-0000-0000-000000000000")
        assert missing["status"] == 404
        eq_filter = await data_list_tool(
            client,
            "document",
            "DemoShipments",
            filter_json=json.dumps({"Number": {"eq": "000000001"}}),
        )
        assert eq_filter["items"][0]["Number"] == "000000001"
    finally:
        await client.aclose()
