# Команды CLI

Пакет: `python -m onecmcp` или команда `onecmcp` после `pip install -e gateway`.

```bash
python -m onecmcp --help
```

Должны быть подкоманды `serve`, `mock1c`, `mcp`.

## `serve` — REST и MCP HTTP

```bash
python -m onecmcp serve --host 127.0.0.1 --port 8000
```

| Флаг | Умолчание | Смысл |
|---|---|---|
| `--host` | `GATEWAY_HOST` (`0.0.0.0`) | адрес bind |
| `--port` | `GATEWAY_PORT` (`8000`) | порт |

На этом же порту: веб-консоль `/`, `/health`, `/ready`, `/diag`, `/guide`, `/openapi.yaml`, `/v1/*`, `/t/{tenant}/v1/*`, streamable HTTP на `MCP_HTTP_PATH` (`/mcp`).

## `mock1c` — мок слоя A

```bash
python -m onecmcp mock1c --host 127.0.0.1 --port 18080
```

| Флаг | Умолчание |
|---|---|
| `--host` | `0.0.0.0` |
| `--port` | `18080` |

Контракт как у расширения, без платформы 1С. Токены — в [справочнике настроек](settings.md).

## `mcp` — процесс MCP

```bash
python -m onecmcp mcp
python -m onecmcp mcp --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

| Флаг | Значения | Умолчание |
|---|---|---|
| `--transport` | `stdio`, `streamable-http` | `stdio` |
| `--host` | адрес HTTP | `127.0.0.1` |
| `--port` | порт HTTP | `GATEWAY_PORT` |
| `--path` | путь HTTP | `/mcp` |

Claude Desktop использует **stdio** без флагов. Для HTTP-агентов предпочтителен `serve` (REST+MCP в одном процессе), а не отдельный `mcp --transport streamable-http`.
