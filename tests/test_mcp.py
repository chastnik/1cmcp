from __future__ import annotations

from onecmcp.mcp_server import create_mcp


def test_mcp_registers_discovery_tools() -> None:
    server = create_mcp()
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert {"health", "meta_search", "meta_describe", "data_list"} <= names
