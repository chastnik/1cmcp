from __future__ import annotations

import time

import httpx

from onecmcp.cache import MetaCache
from onecmcp.client import OneCClient
from onecmcp.config import Settings
from onecmcp.mock1c import DEV_TOKEN, create_mock_app


def test_meta_cache_put_get_and_expire() -> None:
    cache = MetaCache(ttl_seconds=0.05)
    cache.put("k", {"ok": True})
    assert cache.get("k") == {"ok": True}
    time.sleep(0.06)
    assert cache.get("k") is None
    disabled = MetaCache(ttl_seconds=0)
    assert disabled.put("k", 1) == 1
    assert disabled.get("k") is None
    forever = MetaCache(ttl_seconds=-1)
    forever.put("k", 2)
    assert forever.get("k") == 2
    forever.clear()
    assert forever.get("k") is None


async def test_client_reuses_meta_cache() -> None:
    calls = {"n": 0}

    class CountingTransport(httpx.AsyncBaseTransport):
        def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
            self._inner = inner

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            if request.url.path.startswith("/v1/meta/"):
                calls["n"] += 1
            return await self._inner.handle_async_request(request)

    inner = httpx.ASGITransport(app=create_mock_app())
    client = OneCClient(
        Settings(onec_base_url="http://adapter", onec_token=DEV_TOKEN, meta_cache_ttl_seconds=60),
        transport=CountingTransport(inner),
    )
    try:
        first = await client.meta_describe("catalog", "DemoCounterparties")
        second = await client.meta_describe("catalog", "DemoCounterparties")
        listed = await client.meta_list(kind="catalog")
        listed_again = await client.meta_list(kind="catalog")
        assert first["name"] == second["name"]
        assert listed["items"] == listed_again["items"]
        assert calls["n"] == 1
    finally:
        await client.aclose()
