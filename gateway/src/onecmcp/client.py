from __future__ import annotations

from typing import Any

import httpx

from onecmcp.cache import MetaCache
from onecmcp.config import Settings


class AdapterError(Exception):
    def __init__(self, status_code: int, payload: Any, headers: dict[str, str]) -> None:
        super().__init__(f"adapter HTTP {status_code}")
        self.status_code = status_code
        self.payload = payload
        self.headers = headers


class OneCClient:
    """HTTP-клиент к слою A (расширение 1С или мок контракта)."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if settings.onec_token:
            headers["Authorization"] = f"Bearer {settings.onec_token}"
        if settings.tenant:
            headers["X-Tenant"] = settings.tenant
        self._meta_cache = MetaCache(ttl_seconds=settings.meta_cache_ttl_seconds)
        self._client = httpx.AsyncClient(
            base_url=settings.onec_base_url.rstrip("/"),
            headers=headers,
            timeout=settings.onec_timeout_seconds,
            transport=transport,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
    ) -> httpx.Response:
        response = await self._client.request(
            method,
            path,
            params=params,
            json=json,
            headers=headers,
            content=content,
        )
        return response

    async def get_json(self, path: str, **kwargs: Any) -> Any:
        response = await self.request("GET", path, **kwargs)
        if response.status_code >= 400:
            raise AdapterError(response.status_code, _payload(response), dict(response.headers))
        return response.json()

    async def post_json(self, path: str, json: Any | None = None) -> tuple[int, Any]:
        response = await self.request("POST", path, json=json)
        if response.status_code >= 400:
            raise AdapterError(response.status_code, _payload(response), dict(response.headers))
        return response.status_code, response.json()

    async def health(self) -> dict[str, Any]:
        return await self.get_json("/v1/health")

    async def meta_list(
        self,
        *,
        kind: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        key = f"list:{kind}:{limit}:{cursor}"
        cached = self._meta_cache.get(key)
        if cached is not None:
            return cached
        params: dict[str, Any] = {"limit": limit}
        if kind:
            params["kind"] = kind
        if cursor:
            params["cursor"] = cursor
        data = await self.get_json("/v1/meta", params=params)
        return self._meta_cache.put(key, data)

    async def meta_search(self, query: str, limit: int = 20) -> dict[str, Any]:
        key = f"search:{query}:{limit}"
        cached = self._meta_cache.get(key)
        if cached is not None:
            return cached
        data = await self.get_json("/v1/meta/search", params={"q": query, "limit": limit})
        return self._meta_cache.put(key, data)

    async def meta_describe(self, kind: str, name: str) -> dict[str, Any]:
        key = f"describe:{kind}:{name}"
        cached = self._meta_cache.get(key)
        if cached is not None:
            return cached
        data = await self.get_json(f"/v1/meta/{kind}/{name}")
        return self._meta_cache.put(key, data)

    async def list_data(
        self,
        kind: str,
        name: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        filter_json: str | None = None,
        fields: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if filter_json:
            params["filter"] = filter_json
        if fields:
            params["fields"] = fields
        return await self.get_json(f"/v1/data/{kind}/{name}", params=params)

    async def get_data(self, kind: str, name: str, item_id: str) -> dict[str, Any]:
        return await self.get_json(f"/v1/data/{kind}/{name}/{item_id}")

    async def run_query(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return await self.post_json("/v1/query", json=payload)

    async def run_report(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return await self.post_json("/v1/report", json=payload)

    async def start_job(self, operation: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        return await self.post_json("/v1/job", json={"operation": operation, "payload": payload or {}})

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self.get_json(f"/v1/job/{job_id}")


def _payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"detail": response.text, "status": response.status_code, "code": "upstream_error"}
