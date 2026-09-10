from __future__ import annotations

import httpx

from onecmcp.client import OneCClient
from onecmcp.config import Settings


class UnknownTenant(KeyError):
    """Запрошен тенант вне ONEC_TENANTS / TENANT."""


class AdapterPool:
    """Один шлюз — несколько ИБ. Клиент на тенант, URL из карты."""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
        tokens: dict[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._urls = settings.tenant_map()
        self._tokens = tokens or {}
        self._clients: dict[str, OneCClient] = {}

    def resolve(self, tenant: str | None) -> str:
        key = (tenant or "").strip() or self._settings.tenant
        if key not in self._urls:
            raise UnknownTenant(key)
        return key

    def client(self, tenant: str | None = None) -> OneCClient:
        key = self.resolve(tenant)
        stored = self._clients.get(key)
        if stored is not None:
            return stored
        token = self._tokens.get(key) or self._settings.onec_token
        settings = self._settings.model_copy(
            update={"tenant": key, "onec_base_url": self._urls[key], "onec_token": token}
        )
        created = OneCClient(settings, transport=self._transport)
        self._clients[key] = created
        return created

    def ids(self) -> list[str]:
        return sorted(self._urls)

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
