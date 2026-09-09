from __future__ import annotations

import time
from typing import Any


class MetaCache:
    """Кэш карточек и списков метаданных: ERP не выгружается в контекст целиком."""

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if self._ttl >= 0 and expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def put(self, key: str, value: Any) -> Any:
        if self._ttl == 0:
            return value
        ttl = self._ttl if self._ttl > 0 else 10**9
        self._store[key] = (time.monotonic() + ttl, value)
        return value

    def clear(self) -> None:
        self._store.clear()
