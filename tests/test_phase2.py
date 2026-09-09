from __future__ import annotations

import json

from fastapi.testclient import TestClient

from onecmcp.mock1c import DEMO_ID_ROMA, DEV_TOKEN, bearer_headers, create_mock_app
from onecmcp.tools import guide_tool


AUGUST = {
    "BeginDate": "2026-08-01",
    "EndDate": "2026-08-31",
    "Counterparty": {"id": DEMO_ID_ROMA},
}


def test_named_query_august_roma() -> None:
    with TestClient(create_mock_app()) as client:
        response = client.post(
            "/v1/query",
            json={"named_query": "DemoShipmentsByPeriod", "parameters": AUGUST},
            headers=bearer_headers(),
        )
    assert response.status_code == 200
    assert response.headers.get("x-1cmcp-content-kind") == "data"
    body = response.json()
    assert body["content_kind"] == "data"
    assert body["columns"] == ["Number", "Date", "Counterparty", "Amount"]
    assert len(body["rows"]) == 2
    amounts = [row[3] for row in body["rows"]]
    assert sum(amounts) == 150000.0


def test_select_one_and_rejected_mutate() -> None:
    with TestClient(create_mock_app()) as client:
        ok = client.post(
            "/v1/query",
            json={"text": "ВЫБРАТЬ 1"},
            headers=bearer_headers(),
        )
        bad = client.post(
            "/v1/query",
            json={"text": "УНИЧТОЖИТЬ ВТ"},
            headers=bearer_headers(),
        )
        both = client.post(
            "/v1/query",
            json={"named_query": "DemoShipmentsByPeriod", "text": "ВЫБРАТЬ 1"},
            headers=bearer_headers(),
        )
        empty = client.post("/v1/query", json={}, headers=bearer_headers())
        missing = client.post(
            "/v1/query",
            json={"named_query": "NoSuchQuery"},
            headers=bearer_headers(),
        )
    assert ok.status_code == 200
    assert ok.json()["rows"] == [[1]]
    assert bad.status_code == 400
    assert bad.json()["code"] == "query_rejected"
    assert both.status_code == 400
    assert empty.status_code == 400
    assert missing.status_code == 404


def test_sales_report_json_markdown_csv() -> None:
    with TestClient(create_mock_app()) as client:
        json_resp = client.post(
            "/v1/report",
            json={"name": "DemoSales", "parameters": AUGUST, "format": "json"},
            headers=bearer_headers(),
        )
        md_resp = client.post(
            "/v1/report",
            json={"name": "DemoSales", "parameters": AUGUST, "format": "markdown"},
            headers=bearer_headers(),
        )
        csv_resp = client.post(
            "/v1/report",
            json={"name": "DemoSales", "parameters": AUGUST, "format": "csv", "variant": "Default"},
            headers=bearer_headers(),
        )
        missing = client.post(
            "/v1/report",
            json={"name": "UnknownReport"},
            headers=bearer_headers(),
        )
    assert json_resp.status_code == 200
    payload = json_resp.json()
    assert payload["content_kind"] == "data"
    assert payload["format"] == "json"
    assert payload["body"]["totals"]["Amount"] == 150000.0
    assert payload["body"]["totals"]["Count"] == 2
    assert md_resp.status_code == 200
    assert md_resp.json()["format"] == "markdown"
    assert "150000" in md_resp.json()["body"]
    assert csv_resp.json()["format"] == "csv"
    assert "Amount" in csv_resp.json()["body"]
    assert missing.status_code == 404


def test_async_query_returns_job_then_result() -> None:
    with TestClient(create_mock_app()) as client:
        accepted = client.post(
            "/v1/query",
            json={"named_query": "DemoShipmentsByPeriod", "parameters": AUGUST, "async": True},
            headers=bearer_headers(),
        )
        assert accepted.status_code == 202
        job = accepted.json()
        assert job["status"] in {"queued", "running"}
        job_id = job["job_id"]
        status = client.get(f"/v1/job/{job_id}", headers=bearer_headers())
        assert status.status_code == 200
        body = status.json()
        assert body["job_id"] == job_id
        assert body["status"] == "succeeded"
        assert body["result"]["content_kind"] == "data"
        assert len(body["result"]["rows"]) == 2

        started = client.post(
            "/v1/job",
            json={"operation": "report", "payload": {"name": "DemoSales", "parameters": AUGUST}},
            headers=bearer_headers(),
        )
        assert started.status_code == 202
        report_job = client.get(f"/v1/job/{started.json()['job_id']}", headers=bearer_headers())
        assert report_job.json()["status"] == "succeeded"
        assert report_job.json()["result"]["body"]["totals"]["Amount"] == 150000.0

        missing = client.get(
            "/v1/job/00000000-0000-0000-0000-000000000000",
            headers=bearer_headers(),
        )
        assert missing.status_code == 404

        action = client.post(
            "/v1/job",
            json={"operation": "action", "payload": {"name": "x"}},
            headers=bearer_headers(),
        )
        assert action.status_code == 501

        invalid = client.post(
            "/v1/query",
            content=b"not-json",
            headers={**bearer_headers(), "Content-Type": "application/json"},
        )
        assert invalid.status_code == 400
        nameless = client.post("/v1/report", json={"format": "json"}, headers=bearer_headers())
        assert nameless.status_code == 400
        bad_op = client.post(
            "/v1/job",
            json={"operation": "sleep", "payload": {}},
            headers=bearer_headers(),
        )
        assert bad_op.status_code == 400
        too_many = client.post(
            "/v1/query",
            json={"text": "ВЫБРАТЬ 1", "limit": 10001},
            headers=bearer_headers(),
        )
        assert too_many.status_code == 400


def test_report_is_discoverable_and_guide_points_to_skd() -> None:
    with TestClient(create_mock_app()) as client:
        found = client.get("/v1/meta/search", params={"q": "продажи"}, headers=bearer_headers())
        listed = client.get("/v1/meta", params={"kind": "report"}, headers=bearer_headers())
        card = client.get("/v1/meta/report/DemoSales", headers=bearer_headers())
    names = [item["name"] for item in found.json()["items"]]
    assert "DemoSales" in names
    assert listed.json()["items"][0]["name"] == "DemoSales"
    assert {field["name"] for field in card.json()["fields"]} >= {"BeginDate", "EndDate"}

    guided = guide_tool("покажи отчёт по продажам за август", preset="ut11")
    tools = [step["tool"] for step in guided["steps"]]
    assert "report" in tools
    assert guided["report_name"] == "Продажи"


def test_query_via_gateway_and_tool_errors(gateway_client) -> None:
    response = gateway_client.post("/v1/query", json={"text": "ВЫБРАТЬ 1"})
    assert response.status_code == 200
    assert response.json()["rows"] == [[1]]

    shipments = gateway_client.post(
        "/v1/query",
        json={"text": "ВЫБРАТЬ Ссылка ИЗ Документ.DemoShipments", "parameters": AUGUST},
    )
    assert shipments.status_code == 200
    assert len(shipments.json()["rows"]) >= 2
    with TestClient(create_mock_app()) as client:
        no_token = client.post("/v1/report", json={"name": "DemoSales"})
        write_only = client.post(
            "/v1/report",
            json={"name": "DemoSales"},
            headers={"Authorization": "Bearer write-only-token"},
        )
    assert no_token.status_code == 401
    assert write_only.status_code == 403
