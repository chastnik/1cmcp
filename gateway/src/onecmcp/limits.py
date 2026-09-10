from __future__ import annotations

import hashlib
import time

from fastapi import Request


class RateLimiter:
    """Скользящее окно: не больше `per_minute` запросов с одного ключа за 60 с."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> tuple[bool, float]:
        if self.per_minute <= 0:
            return True, 0.0
        current = time.monotonic() if now is None else now
        window = self._hits.setdefault(key, [])
        cutoff = current - 60.0
        window[:] = [stamp for stamp in window if stamp > cutoff]
        if len(window) >= self.per_minute:
            oldest = window[0]
            retry_after = max(1.0, 60.0 - (current - oldest))
            return False, retry_after
        window.append(current)
        return True, 0.0


def request_limit_key(request: Request) -> str:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
            return f"tok:{digest}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"
