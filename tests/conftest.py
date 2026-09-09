from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
import httpx

from onecmcp.app import create_app
from onecmcp.config import Settings
from onecmcp.mock1c import create_mock_app


@pytest.fixture
def mock_app():
    return create_mock_app()


@pytest.fixture
def gateway_client(mock_app):
    transport = httpx.ASGITransport(app=mock_app)
    settings = Settings(onec_base_url="http://adapter")
    app = create_app(settings, adapter_transport=transport)
    with TestClient(app) as client:
        yield client
