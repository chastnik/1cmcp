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

    serve = sub.add_parser("serve", help="REST-шлюз и MCP streamable HTTP на /mcp")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    mock = sub.add_parser("mock1c", help="Мок слоя A для локальной разработки и CI")
    mock.add_argument("--host", default="0.0.0.0")
    mock.add_argument("--port", type=int, default=18080)

    mcp = sub.add_parser("mcp", help="MCP: stdio или streamable HTTP")
    mcp.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="stdio для Claude Desktop; streamable-http для HTTP-агентов",
    )
    mcp.add_argument("--host", default=None)
    mcp.add_argument("--port", type=int, default=None)
    mcp.add_argument("--path", default="/mcp")

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
        server = create_mcp(settings)
        if args.transport == "stdio":
            server.run(transport="stdio")
            return
        server.run(
            transport="streamable-http",
            host=args.host or "127.0.0.1",
            port=args.port or settings.gateway_port,
            streamable_http_path=args.path,
        )
        return


if __name__ == "__main__":
    main()
