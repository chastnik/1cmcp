from __future__ import annotations

import re

DEFAULT_LIMIT = 1000
MAX_LIMIT = 10_000
MAX_TEXT_LENGTH = 20_000

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//.*?$", re.MULTILINE)
_FIRST_TOKEN = re.compile(r"^([A-Za-zА-Яа-яЁё_]+)", re.UNICODE)

_FORBIDDEN: tuple[re.Pattern[str], ...] = (
    re.compile(r";"),
    re.compile(r"\bвыполнить\b", re.IGNORECASE),
    re.compile(r"\bexecute\b", re.IGNORECASE),
    re.compile(r"\bуничтожить\b", re.IGNORECASE),
    re.compile(r"\bdrop\b", re.IGNORECASE),
    re.compile(r"\bудалить\b", re.IGNORECASE),
    re.compile(r"\bdelete\b", re.IGNORECASE),
    re.compile(r"\bпоместить\b", re.IGNORECASE),
    re.compile(r"\binto\b", re.IGNORECASE),
    re.compile(r"\bдля\s+изменения\b", re.IGNORECASE),
    re.compile(r"\bfor\s+update\b", re.IGNORECASE),
    re.compile(r"\binsert\b", re.IGNORECASE),
    re.compile(r"\bupdate\b", re.IGNORECASE),
    re.compile(r"\bmerge\b", re.IGNORECASE),
    re.compile(r"\bexec\b", re.IGNORECASE),
)


class QueryRejected(ValueError):
    def __init__(self, detail: str, *, code: str = "query_rejected") -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code


def strip_comments(text: str) -> str:
    without_blocks = _BLOCK_COMMENT.sub(" ", text)
    return _LINE_COMMENT.sub(" ", without_blocks)


def validate_query_text(text: str | None) -> str:
    if text is None or not str(text).strip():
        raise QueryRejected("Нужен текст запроса или имя именованного запроса")
    raw = str(text)
    if len(raw) > MAX_TEXT_LENGTH:
        raise QueryRejected("Текст запроса слишком длинный")
    stripped = strip_comments(raw)
    compact = " ".join(stripped.split())
    if not compact:
        raise QueryRejected("После удаления комментариев запрос пуст")
    match = _FIRST_TOKEN.match(compact)
    first = (match.group(1) if match else "").casefold()
    if first not in {"выбрать", "select"}:
        raise QueryRejected("Разрешена только выборка: запрос должен начинаться с ВЫБРАТЬ или SELECT")
    for pattern in _FORBIDDEN:
        if pattern.search(compact):
            raise QueryRejected("Запрос содержит запрещённую конструкцию")
    return compact


def resolve_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise QueryRejected("Лимит строк должен быть целым числом")
    if limit < 1 or limit > MAX_LIMIT:
        raise QueryRejected(f"Лимит строк должен быть от 1 до {MAX_LIMIT}")
    return limit
