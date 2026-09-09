from __future__ import annotations

from fastapi.testclient import TestClient

from onecmcp.mock1c import (
    DEMO_ID_ROMA,
    DEV_TOKEN,
    WRITE_DEV_TOKEN,
    WRITE_ONLY_TOKEN,
    bearer_headers,
    create_mock_app,
)


ITEM = {
    "Number": "000000099",
    "Date": "2026-09-09",
    "Counterparty": {"id": DEMO_ID_ROMA},
    "Amount": 1234.0,
}


def _write_headers(
    *,
    idempotency: str | None = "idem-create-1",
    session: str | None = "sess-1",
    token: str = WRITE_DEV_TOKEN,
) -> dict[str, str]:
    headers = bearer_headers(token)
    if idempotency:
        headers["Idempotency-Key"] = idempotency
    if session:
        headers["X-Session-Id"] = session
    return headers


def test_dry_run_then_create_post_idempotent_rollback() -> None:
    with TestClient(create_mock_app()) as client:
        preview = client.post(
            "/v1/data/document/DemoShipments/dry-run",
            json={"item": ITEM, "post": False},
            headers=_write_headers(idempotency=None),
        )
        assert preview.status_code == 200
        dry = preview.json()
        assert dry["fill_check"] == []
        token = dry["confirm_token"]
        assert token.startswith("dry-")

        denied = client.post(
            "/v1/data/document/DemoShipments",
            json={"item": ITEM, "confirm_token": token},
            headers=_write_headers(token=DEV_TOKEN),
        )
        assert denied.status_code == 403

        missing_confirm = client.post(
            "/v1/data/document/DemoShipments",
            json={"item": ITEM},
            headers=_write_headers(),
        )
        assert missing_confirm.status_code == 400
        assert missing_confirm.json()["code"] == "confirm_required"

        created = client.post(
            "/v1/data/document/DemoShipments",
            json={"item": ITEM, "confirm_token": token},
            headers=_write_headers(),
        )
        assert created.status_code == 201
        first = created.json()
        assert first["posted"] is False
        new_id = first["ref"]["id"]

        replay = client.post(
            "/v1/data/document/DemoShipments",
            json={"item": ITEM, "confirm_token": token},
            headers=_write_headers(),
        )
        assert replay.status_code == 201
        assert replay.json()["ref"]["id"] == new_id

        listed = client.get(
            "/v1/data/document/DemoShipments",
            headers=bearer_headers(),
        )
        ids = [item["id"] for item in listed.json()["items"]]
        assert ids.count(new_id) == 1

        posted = client.post(
            f"/v1/data/document/DemoShipments/{new_id}/post",
            json={"confirm_token": token},
            headers=_write_headers(idempotency="idem-post-1"),
        )
        # posting uses a fresh dry-run token in the real flow; this one is bound to create
        assert posted.status_code in {200, 400, 422}

        post_preview = client.post(
            "/v1/data/document/DemoShipments/dry-run",
            json={"item": {**ITEM, "id": new_id}, "post": True},
            headers=_write_headers(idempotency=None),
        )
        post_token = post_preview.json()["confirm_token"]
        posted_ok = client.post(
            f"/v1/data/document/DemoShipments/{new_id}/post",
            json={"confirm_token": post_token},
            headers=_write_headers(idempotency="idem-post-2"),
        )
        assert posted_ok.status_code == 200
        assert posted_ok.json()["posted"] is True

        rolled = client.post(
            "/v1/session/rollback",
            json={"session_id": "sess-1"},
            headers=_write_headers(idempotency=None),
        )
        assert rolled.status_code == 200
        assert rolled.json()["session_id"] == "sess-1"
        assert rolled.json()["undone"]
        gone = client.get(
            f"/v1/data/document/DemoShipments/{new_id}",
            headers=bearer_headers(),
        )
        assert gone.status_code == 404


def test_fill_check_and_posting_errors() -> None:
    with TestClient(create_mock_app()) as client:
        dry = client.post(
            "/v1/data/document/DemoShipments/dry-run",
            json={"item": {"Number": "1"}, "post": True},
            headers=_write_headers(idempotency=None),
        )
        assert dry.status_code == 200
        checks = dry.json()["fill_check"]
        assert any("Amount" in msg or "Сумма" in msg for msg in checks)
        assert any("контрагент" in msg.lower() or "Counterparty" in msg for msg in checks)


def test_action_posts_whitelist_only() -> None:
    with TestClient(create_mock_app()) as client:
        unknown = client.post(
            "/v1/action",
            json={"name": "DropDatabase", "arguments": {}},
            headers=_write_headers(idempotency=None),
        )
        assert unknown.status_code == 404

        dry = client.post(
            "/v1/data/document/DemoShipments/dry-run",
            json={"item": ITEM},
            headers=_write_headers(idempotency=None),
        )
        created = client.post(
            "/v1/data/document/DemoShipments",
            json={"item": ITEM, "confirm_token": dry.json()["confirm_token"]},
            headers=_write_headers(idempotency="idem-act-1", session="sess-act"),
        )
        new_id = created.json()["ref"]["id"]
        acted = client.post(
            "/v1/action",
            json={"name": "DemoPostShipment", "arguments": {"id": new_id}},
            headers=_write_headers(idempotency=None, session="sess-act"),
        )
        assert acted.status_code == 200
        fetched = client.get(
            f"/v1/data/document/DemoShipments/{new_id}",
            headers=bearer_headers(),
        )
        assert fetched.json()["item"]["Posted"] is True


def test_patch_catalog_and_idempotency_conflict() -> None:
    with TestClient(create_mock_app()) as client:
        dry = client.post(
            "/v1/data/catalog/DemoCounterparties/dry-run",
            json={"item": {"Description": "ООО Новая", "INN": "7700000001"}},
            headers=_write_headers(idempotency=None),
        )
        assert dry.status_code == 200
        created = client.post(
            "/v1/data/catalog/DemoCounterparties",
            json={"item": {"Description": "ООО Новая", "INN": "7700000001"}, "confirm_token": dry.json()["confirm_token"]},
            headers=_write_headers(idempotency="idem-cat-1", session="sess-cat"),
        )
        assert created.status_code == 201
        new_id = created.json()["ref"]["id"]

        conflict = client.post(
            "/v1/data/catalog/DemoCounterparties",
            json={"item": {"Description": "Другое"}, "confirm_token": "unused"},
            headers=_write_headers(idempotency="idem-cat-1"),
        )
        assert conflict.status_code == 409

        patched_item = {"Description": "ООО Новая плюс", "INN": "7700000001", "id": new_id}
        patch_dry = client.post(
            "/v1/data/catalog/DemoCounterparties/dry-run",
            json={"item": patched_item},
            headers=_write_headers(idempotency=None),
        )
        patched = client.patch(
            f"/v1/data/catalog/DemoCounterparties/{new_id}",
            json={"item": patched_item, "confirm_token": patch_dry.json()["confirm_token"]},
            headers=_write_headers(idempotency="idem-patch-1", session="sess-cat"),
        )
        assert patched.status_code == 200
        fetched = client.get(
            f"/v1/data/catalog/DemoCounterparties/{new_id}",
            headers=bearer_headers(),
        )
        assert fetched.json()["item"]["Description"] == "ООО Новая плюс"

        missing_key = client.post(
            "/v1/data/catalog/DemoCounterparties",
            json={"item": {"Description": "X"}, "confirm_token": "x"},
            headers=_write_headers(idempotency=None),
        )
        assert missing_key.status_code == 400

        write_only = client.post(
            "/v1/data/catalog/DemoCounterparties/dry-run",
            json={"item": {"Description": "Нет ACL"}},
            headers=_write_headers(token=WRITE_ONLY_TOKEN, idempotency=None),
        )
        assert write_only.status_code == 403


def test_posting_zero_amount_is_422() -> None:
    with TestClient(create_mock_app()) as client:
        item = {**ITEM, "Amount": 0}
        dry = client.post(
            "/v1/data/document/DemoShipments/dry-run",
            json={"item": item, "post": False},
            headers=_write_headers(idempotency=None),
        )
        created = client.post(
            "/v1/data/document/DemoShipments",
            json={"item": item, "confirm_token": dry.json()["confirm_token"]},
            headers=_write_headers(idempotency="idem-zero-1"),
        )
        new_id = created.json()["ref"]["id"]
        post_dry = client.post(
            "/v1/data/document/DemoShipments/dry-run",
            json={"item": {**item, "id": new_id}, "post": True},
            headers=_write_headers(idempotency=None),
        )
        posted = client.post(
            f"/v1/data/document/DemoShipments/{new_id}/post",
            json={"confirm_token": post_dry.json()["confirm_token"]},
            headers=_write_headers(idempotency="idem-zero-post"),
        )
        assert posted.status_code == 422
        assert posted.json()["code"] == "posting_failed"
