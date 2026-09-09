from __future__ import annotations

from typing import Any

import httpx

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

    async def health(self) -> dict[str, Any]:
        return await self.get_json("/v1/health")

    async def meta_search(self, query: str, limit: int = 20) -> dict[str, Any]:
        return await self.get_json("/v1/meta/search", params={"q": query, "limit": limit})

    async def meta_describe(self, kind: str, name: str) -> dict[str, Any]:
        return await self.get_json(f"/v1/meta/{kind}/{name}")

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


def _payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"detail": response.text, "status": response.status_code, "code": "upstream_error"}
