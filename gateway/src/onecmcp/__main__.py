from __future__ import annotations

import argparse

import uvicorn

from onecmcp.app import create_app
from onecmcp.config import load_settings
from onecmcp.mcp_server import create_mcp
from onecmcp.mock1c import create_mock_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="onecmcp", description="Шлюз 1cmcp")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="REST-шлюз")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    mock = sub.add_parser("mock1c", help="Мок слоя A для локальной разработки и CI")
    mock.add_argument("--host", default="0.0.0.0")
    mock.add_argument("--port", type=int, default=18080)

    sub.add_parser("mcp", help="MCP stdio для Claude Desktop")

    args = parser.parse_args()
    settings = load_settings()

    if args.command == "serve":
        app = create_app(settings)
        uvicorn.run(
            app,
            host=args.host or settings.gateway_host,
            port=args.port or settings.gateway_port,
        )
        return

    if args.command == "mock1c":
        uvicorn.run(create_mock_app(), host=args.host, port=args.port)
        return

    if args.command == "mcp":
        create_mcp(settings).run(transport="stdio")
        return


if __name__ == "__main__":
    main()
