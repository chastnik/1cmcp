from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

DEMO_ID_ROMA = "8a996f93-36c8-4bcf-b707-f75b8b4bc5e3"

TTL_SECONDS = 600
ACTIONS = {
    "DemoPostShipment": {
        "description": "Провести демо-отгрузку по id",
        "arguments": {"id": "uuid документа DemoShipments"},
    }
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


REQUIRED_FIELDS = {
    ("catalog", "DemoCounterparties"): [
        ("Description", "Наименование"),
    ],
    ("document", "DemoShipments"): [
        ("Number", "Номер"),
        ("Date", "Дата"),
        ("Counterparty", "Контрагент"),
        ("Amount", "Сумма"),
    ],
}


def fill_check(kind: str, name: str, item: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for field_name, synonym in REQUIRED_FIELDS.get((kind, name), []):
        value = item.get(field_name)
        if value in (None, "", []):
            messages.append(f"Не заполнено поле {field_name} ({synonym})")
    if (kind, name) == ("document", "DemoShipments"):
        amount = item.get("Amount")
        if amount is not None:
            try:
                if float(amount) < 0:
                    messages.append("Сумма не может быть отрицательной. Укажите Amount больше или равный 0.")
            except (TypeError, ValueError):
                messages.append("Поле Amount (Сумма) должно быть числом")
        counterparty = item.get("Counterparty")
        if isinstance(counterparty, dict) and not counterparty.get("id"):
            messages.append("В Contragent/Counterparty нужен id ссылки, не только представление")
    return messages


def posting_check(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        amount = float(item.get("Amount") or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        errors.append("Нельзя провести документ: сумма (Amount) должна быть больше 0")
    counterparty = item.get("Counterparty")
    cid = counterparty.get("id") if isinstance(counterparty, dict) else None
    if not cid:
        errors.append("Нельзя провести документ: не указан контрагент (Counterparty.id)")
    if not item.get("Date"):
        errors.append("Нельзя провести документ: не указана дата")
    return errors


def posting_effects(item: dict[str, Any]) -> list[str]:
    amount = item.get("Amount")
    party = item.get("Counterparty")
    title = party.get("presentation") if isinstance(party, dict) else party
    return [
        f"Будет установлен признак Posted=true",
        f"Движения: отгрузка {title or 'контрагенту'} на сумму {amount}",
    ]


def normalize_item(kind: str, name: str, item: dict[str, Any], item_id: str | None = None) -> dict[str, Any]:
    body = copy.deepcopy(item)
    new_id = item_id or str(uuid4())
    if kind == "document" and name == "DemoShipments":
        counterparty = body.get("Counterparty")
        if isinstance(counterparty, dict) and counterparty.get("id") == DEMO_ID_ROMA:
            counterparty.setdefault("ref", "Catalog.DemoCounterparties")
            counterparty.setdefault("presentation", "ООО Ромашка")
        body.setdefault("Posted", False)
        presentation = f"{body.get('Number', '')} от {body.get('Date', '')}".strip()
        body["id"] = new_id
        body["ref"] = {"ref": "Document.DemoShipments", "id": new_id, "presentation": presentation}
        return body
    body.setdefault("Description", "")
    body["id"] = new_id
    body["ref"] = {
        "ref": "Catalog.DemoCounterparties",
        "id": new_id,
        "presentation": body.get("Description") or new_id,
    }
    return body


class WriteEngine:
    def __init__(self, collections: dict[tuple[str, str], dict[str, dict[str, Any]]]) -> None:
        self.collections = collections
        self.dry_runs: dict[str, dict[str, Any]] = {}
        self.idempotency: dict[tuple[str, str], dict[str, Any]] = {}
        self.sessions: dict[str, list[dict[str, Any]]] = {}

    def reset(self, collections: dict[tuple[str, str], dict[str, dict[str, Any]]]) -> None:
        self.collections = collections
        self.dry_runs.clear()
        self.idempotency.clear()
        self.sessions.clear()

    def dry_run(self, kind: str, name: str, item: dict[str, Any], *, post: bool = False) -> dict[str, Any]:
        preview = normalize_item(kind, name, item, item_id=item.get("id") if isinstance(item.get("id"), str) else None)
        checks = fill_check(kind, name, preview)
        token = f"dry-{uuid4()}"
        expires = utc_now() + timedelta(seconds=TTL_SECONDS)
        self.dry_runs[token] = {
            "kind": kind,
            "name": name,
            "item": preview,
            "post": post,
            "expires": expires,
            "fingerprint": _fingerprint(preview),
        }
        result: dict[str, Any] = {
            "confirm_token": token,
            "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "preview": preview,
            "fill_check": checks,
        }
        if post or kind == "document":
            result["posting_effects"] = posting_effects(preview) if post else []
            if post:
                result["fill_check"] = checks + posting_check(preview)
        return result

    def consume_token(self, token: str, kind: str, name: str, item: dict[str, Any]) -> dict[str, Any] | str:
        record = self.dry_runs.get(token or "")
        if record is None:
            return "Нет действительного confirm_token. Сначала вызовите dry-run."
        if record["expires"] < utc_now():
            return "Срок confirm_token истёк. Повторите dry-run."
        if record["kind"] != kind or record["name"] != name:
            return "confirm_token выдан для другого объекта метаданных"
        submitted = normalize_item(kind, name, item, item_id=record["item"]["id"])
        if _fingerprint(submitted) != record["fingerprint"]:
            return "Данные не совпадают с dry-run. Повторите предпросмотр."
        return record

    def consume_for_target(self, token: str, kind: str, name: str, item_id: str) -> dict[str, Any] | str:
        record = self.dry_runs.get(token or "")
        if record is None:
            return "Нет действительного confirm_token. Сначала вызовите dry-run."
        if record["expires"] < utc_now():
            return "Срок confirm_token истёк. Повторите dry-run."
        if record["kind"] != kind or record["name"] != name:
            return "confirm_token выдан для другого объекта метаданных"
        if record["item"]["id"] != item_id:
            return "confirm_token относится к другому объекту"
        return record

    def remember(
        self,
        client_id: str,
        key: str,
        result: dict[str, Any],
        fingerprint: str = "",
    ) -> None:
        self.idempotency[(client_id, key)] = {"result": result, "fingerprint": fingerprint}

    def replay(
        self,
        client_id: str,
        key: str | None,
        fingerprint: str | None = None,
    ) -> dict[str, Any] | str | None:
        if not key:
            return None
        record = self.idempotency.get((client_id, key))
        if record is None:
            return None
        if fingerprint is not None and record.get("fingerprint") not in {"", fingerprint}:
            return "conflict"
        return record["result"]

    def track(self, session_id: str | None, event: dict[str, Any]) -> None:
        if not session_id:
            return
        self.sessions.setdefault(session_id, []).append(event)

    def rollback(self, session_id: str) -> list[dict[str, str]]:
        events = list(reversed(self.sessions.get(session_id) or []))
        undone: list[dict[str, str]] = []
        for event in events:
            collection = self.collections.get((event["kind"], event["name"]))
            if collection is None:
                continue
            item_id = event["id"]
            if event["op"] == "create":
                item = collection.pop(item_id, None)
                if item:
                    undone.append(item["ref"])
            elif event["op"] == "patch" and item_id in collection:
                collection[item_id] = event["previous"]
                undone.append(collection[item_id]["ref"])
            elif event["op"] == "post" and item_id in collection:
                collection[item_id]["Posted"] = bool(event.get("previous_posted", False))
                undone.append(collection[item_id]["ref"])
        self.sessions[session_id] = []
        return undone


def _fingerprint(item: dict[str, Any]) -> str:
    payload = {key: value for key, value in item.items() if key not in {"id", "ref"}}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
