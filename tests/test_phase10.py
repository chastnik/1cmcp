from __future__ import annotations

from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from onecmcp import __version__
from onecmcp.app import create_app
from onecmcp.config import Settings
from onecmcp.mcp_server import create_mcp
from onecmcp.mock1c import DEV_TOKEN, create_mock_app

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "extension" / "src"
HELM = ROOT / "deploy" / "helm" / "onecmcp"
CONSOLE = ROOT / "gateway" / "src" / "onecmcp" / "console" / "static"


def _gateway(tmp_path: Path, *, token: str = "bootstrap-secret") -> TestClient:
    transport = httpx.ASGITransport(app=create_mock_app())
    settings = Settings(
        onec_base_url="http://adapter",
        onec_token=DEV_TOKEN,
        gateway_data_dir=str(tmp_path),
        admin_bootstrap_token=token,
    )
    return TestClient(create_app(settings, adapter_transport=transport))


def test_version_is_0110() -> None:
    assert __version__ == "0.11.0"
    chart = (HELM / "Chart.yaml").read_text(encoding="utf-8")
    assert 'appVersion: "0.11.0"' in chart
    version = (SRC / "Configuration.xml").read_text(encoding="utf-8")
    assert "<Version>0.11.0</Version>" in version
    spec = (ROOT / "specs" / "openapi.yaml").read_text(encoding="utf-8")
    assert "version: 0.11.0" in spec
    assert "/console" in spec


def test_console_static_and_help_markup() -> None:
    html = (CONSOLE / "index.html").read_text(encoding="utf-8")
    css = (CONSOLE / "app.css").read_text(encoding="utf-8")
    js = (CONSOLE / "app.js").read_text(encoding="utf-8")
    assert "1cmcp" in html
    assert "Администрирование" in html
    assert "data-help" in js or "help-tip" in css
    assert ".help-tip" in css
    assert "operators" in js
    assert "bases" in js
    assert 'name="token"' in js
    assert "type=\"password\"" in js
    assert 'id="login-token"' in js
    assert "сохранён, пустое — не менять" in js
    assert 'value="сохранён"' not in js
    assert "Введите токен первого входа" in js
    assert 'id="new-operator-login"' in js


def test_console_home_and_catalog(tmp_path: Path) -> None:
    client = _gateway(tmp_path)
    home = client.get("/")
    assert home.status_code == 200
    assert "text/html" in home.headers.get("content-type", "")
    assert "1cmcp" in home.text
    catalog = client.get("/console/api/catalog").json()
    mcp_names = {tool["name"] for tool in catalog["mcp"]}
    assert {"health", "guide", "job_list", "job_get", "audit_list", "session_get"} <= mcp_names
    assert any(tool.get("description") for tool in catalog["mcp"])
    rest_paths = {item["method"] + " " + item["path"] for item in catalog["rest"]}
    assert "GET /v1/job" in rest_paths
    assert "POST /v1/query" in rest_paths
    assert catalog["version"] == "0.11.0"


def test_console_serves_all_instructions(tmp_path: Path) -> None:
    client = _gateway(tmp_path)
    index = client.get("/console/api/docs").json()
    ids = {page["id"] for page in index["pages"]}
    for needle in (
        "usage",
        "install",
        "admin/clients",
        "admin/tenants",
        "reference/api",
        "reference/settings",
        "connect/README",
        "skills",
    ):
        assert needle in ids, needle
    page = client.get("/console/api/docs/usage.md")
    assert page.status_code == 200
    body = page.json()
    assert "job_list" in body["markdown"]
    assert "<h" in body["html"]


def test_admin_requires_bootstrap_or_operator(tmp_path: Path) -> None:
    client = _gateway(tmp_path)
    assert client.get("/console/api/settings").status_code == 401
    denied = client.get("/console/api/settings", headers={"Authorization": "Bearer nope"})
    assert denied.status_code == 401
    ok = client.get("/console/api/settings", headers={"Authorization": "Bearer bootstrap-secret"})
    assert ok.status_code == 200
    payload = ok.json()
    fields = {item["name"]: item for item in payload["fields"]}
    assert "onec_base_url" in fields
    assert fields["onec_base_url"]["help"]
    assert "слоя A" in fields["onec_base_url"]["help"] or "слой A" in fields["onec_base_url"]["help"]
    env_only = {item["name"] for item in payload["fields"] if item.get("source") == "env"}
    assert env_only == {"gateway_host", "gateway_port", "gateway_data_dir", "admin_bootstrap_token"}


def test_admin_persists_bases_and_operators(tmp_path: Path) -> None:
    client = _gateway(tmp_path)
    headers = {"Authorization": "Bearer bootstrap-secret"}
    saved = client.put(
        "/console/api/settings",
        headers=headers,
        json={
            "onec_timeout_seconds": 45,
            "onec_preset": "ut11",
            "meta_cache_ttl_seconds": 10,
            "rate_limit_per_minute": 30,
        },
    )
    assert saved.status_code == 200
    bases = client.put(
        "/console/api/bases",
        headers=headers,
        json={
            "items": [
                {
                    "id": "erp",
                    "url": "http://erp.example/ib/hs/mcp",
                    "token": "erp-token",
                }
            ],
            "default_id": "erp",
        },
    )
    assert bases.status_code == 200
    created = client.post(
        "/console/api/operators",
        headers=headers,
        json={"login": "alice", "password": "secret-pass"},
    )
    assert created.status_code == 201
    listed_ops = client.get("/console/api/operators", headers=headers)
    assert listed_ops.status_code == 200
    assert listed_ops.json()["items"][0]["login"] == "alice"
    login = client.post("/console/api/login", json={"login": "alice", "password": "secret-pass"})
    assert login.status_code == 200
    session = login.json()["access_token"]
    via_user = client.get("/console/api/settings", headers={"Authorization": f"Bearer {session}"})
    assert via_user.status_code == 200
    again = TestClient(
        create_app(
            Settings(
                onec_base_url="http://ignored",
                onec_token="ignored",
                gateway_data_dir=str(tmp_path),
                admin_bootstrap_token="bootstrap-secret",
            ),
            adapter_transport=httpx.ASGITransport(app=create_mock_app()),
        )
    )
    stored = again.get("/console/api/settings", headers=headers)
    assert stored.status_code == 200
    body = stored.json()["values"]
    assert body["onec_preset"] == "ut11"
    assert body["onec_timeout_seconds"] == 45
    assert body["onec_base_url"] == "http://erp.example/ib/hs/mcp"
    listed = again.get("/console/api/bases", headers=headers).json()
    assert listed["items"][0]["id"] == "erp"
    assert listed["items"][0]["token_set"] is True
    assert listed["items"][0].get("token") in {None, ""}
    relogin = again.post("/console/api/login", json={"login": "alice", "password": "secret-pass"})
    assert relogin.status_code == 200


def test_env_example_is_bootstrap_only() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ADMIN_BOOTSTRAP_TOKEN" in example
    assert "GATEWAY_DATA_DIR" in example
    assert "GATEWAY_HOST" in example
    assert "веб-консол" in example.lower() or "консол" in example.lower()


def test_mcp_still_registers_tools() -> None:
    names = {tool.name for tool in create_mcp()._tool_manager.list_tools()}
    assert "job_list" in names
    assert "guide" in names
