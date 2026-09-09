from __future__ import annotations

import sys

import pytest

from onecmcp.__main__ import main
from onecmcp.config import Settings


def test_main_serve_mock_and_mcp(monkeypatch) -> None:
    calls: list[tuple] = []

    monkeypatch.setattr(
        "onecmcp.__main__.load_settings",
        lambda: Settings(gateway_host="127.0.0.1", gateway_port=8000),
    )
    monkeypatch.setattr(
        "onecmcp.__main__.create_app",
        lambda settings: {"app": "gateway"},
    )
    monkeypatch.setattr(
        "onecmcp.__main__.create_mock_app",
        lambda: {"app": "mock"},
    )

    class FakeMcp:
        def run(self, transport: str) -> None:
            calls.append(("mcp", transport))

    monkeypatch.setattr("onecmcp.__main__.create_mcp", lambda settings: FakeMcp())
    monkeypatch.setattr(
        "onecmcp.__main__.uvicorn.run",
        lambda app, host, port: calls.append(("uvicorn", app, host, port)),
    )

    monkeypatch.setattr(sys, "argv", ["onecmcp", "serve", "--host", "0.0.0.0", "--port", "9"])
    main()
    monkeypatch.setattr(sys, "argv", ["onecmcp", "serve"])
    main()
    monkeypatch.setattr(sys, "argv", ["onecmcp", "mock1c", "--host", "127.0.0.1", "--port", "18080"])
    main()
    monkeypatch.setattr(sys, "argv", ["onecmcp", "mcp"])
    main()

    assert calls[0][0] == "uvicorn"
    assert calls[0][1] == {"app": "gateway"}
    assert calls[0][3] == 9
    assert calls[1][2] == "127.0.0.1"
    assert calls[1][3] == 8000
    assert calls[2][1] == {"app": "mock"}
    assert calls[3] == ("mcp", "stdio")


def test_main_requires_command(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["onecmcp"])
    with pytest.raises(SystemExit):
        main()
