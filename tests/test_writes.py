from __future__ import annotations

from datetime import timedelta

from onecmcp.writes import (
    WriteEngine,
    fill_check,
    normalize_item,
    posting_check,
    utc_now,
)


def test_fill_and_posting_messages_are_actionable() -> None:
    missing = fill_check("document", "DemoShipments", {"Number": "1", "Amount": "x"})
    assert any("Date" in msg or "Дата" in msg for msg in missing)
    assert any("Amount" in msg or "Сумма" in msg for msg in missing)
    negative = fill_check("document", "DemoShipments", {"Number": "1", "Date": "2026-01-01", "Amount": -1})
    assert any("отрицатель" in msg for msg in negative)
    catalog = fill_check("catalog", "DemoCounterparties", {})
    assert any("Description" in msg or "Наименование" in msg for msg in catalog)
    posting = posting_check({"Amount": 0, "Counterparty": {"presentation": "X"}})
    assert any("провест" in msg.lower() or "сумма" in msg.lower() for msg in posting)


def test_engine_token_mismatch_expiry_and_rollback() -> None:
    collections = {("catalog", "DemoCounterparties"): {}}
    engine = WriteEngine(collections)
    item = {"Description": "А"}
    preview = engine.dry_run("catalog", "DemoCounterparties", item)
    token = preview["confirm_token"]
    assert engine.consume_token("nope", "catalog", "DemoCounterparties", item).startswith("Нет")
    assert "другого объекта" in engine.consume_token(token, "document", "DemoShipments", item)
    engine.dry_runs[token]["expires"] = utc_now() - timedelta(seconds=1)
    assert "истёк" in engine.consume_token(token, "catalog", "DemoCounterparties", item)

    fresh = engine.dry_run("catalog", "DemoCounterparties", item)
    consumed = engine.consume_token(fresh["confirm_token"], "catalog", "DemoCounterparties", {"Description": "Б"})
    assert isinstance(consumed, str)
    assert "не совпадают" in consumed

    stored = normalize_item("catalog", "DemoCounterparties", item)
    collections[("catalog", "DemoCounterparties")][stored["id"]] = stored
    engine.track("s1", {"op": "create", "kind": "catalog", "name": "DemoCounterparties", "id": stored["id"]})
    undone = engine.rollback("s1")
    assert undone
    assert stored["id"] not in collections[("catalog", "DemoCounterparties")]
    assert engine.replay("c", None) is None
    engine.remember("c", "key-aaaa", {"ok": True}, "fp-1")
    assert engine.replay("c", "key-aaaa", "fp-1") == {"ok": True}
    assert engine.replay("c", "key-aaaa", "fp-other") == "conflict"
