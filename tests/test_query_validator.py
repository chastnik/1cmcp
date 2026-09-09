from __future__ import annotations

import pytest

from onecmcp.query_validator import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    QueryRejected,
    resolve_limit,
    validate_query_text,
)


def test_accepts_select_and_vybrat() -> None:
    assert validate_query_text("ВЫБРАТЬ 1") == "ВЫБРАТЬ 1"
    assert validate_query_text("  SELECT 1 AS X  ") == "SELECT 1 AS X"


def test_strips_comments_before_select() -> None:
    text = validate_query_text("// комментарий\nВЫБРАТЬ\n\tСсылка\nИЗ Документ.DemoShipments")
    assert text.startswith("ВЫБРАТЬ")


def test_rejects_empty_and_non_select() -> None:
    with pytest.raises(QueryRejected) as empty:
        validate_query_text("   ")
    assert empty.value.code == "query_rejected"
    with pytest.raises(QueryRejected):
        validate_query_text("УНИЧТОЖИТЬ ВТ")
    with pytest.raises(QueryRejected):
        validate_query_text("ВЫПОЛНИТЬ ВТ")


def test_rejects_dangerous_constructs() -> None:
    for text in (
        "ВЫБРАТЬ 1; УНИЧТОЖИТЬ ВТ",
        "ВЫБРАТЬ * ИЗ Т ДЛЯ ИЗМЕНЕНИЯ",
        "SELECT * FROM T FOR UPDATE",
        "ВЫБРАТЬ 1 ПОМЕСТИТЬ ВТ",
        "SELECT 1 INTO tmp",
        "ВЫБРАТЬ 1; DROP TABLE X",
        "/* ok */ DELETE FROM T",
    ):
        with pytest.raises(QueryRejected):
            validate_query_text(text)


def test_rejects_too_long() -> None:
    with pytest.raises(QueryRejected):
        validate_query_text("ВЫБРАТЬ 1" + " " * 20001)


def test_resolve_limit_bounds() -> None:
    assert resolve_limit(None) == DEFAULT_LIMIT
    assert resolve_limit(10) == 10
    assert resolve_limit(MAX_LIMIT) == MAX_LIMIT
    with pytest.raises(QueryRejected):
        resolve_limit(0)
    with pytest.raises(QueryRejected):
        resolve_limit(MAX_LIMIT + 1)
