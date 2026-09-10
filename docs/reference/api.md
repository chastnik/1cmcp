# HTTP API и MCP-инструменты

Контракт: [`specs/openapi.yaml`](https://github.com/chastnik/1cmcp/blob/main/specs/openapi.yaml). У живого шлюза: `GET /openapi.yaml`.

Базовый путь адаптера: `{ib}/hs/mcp/v1/...`. Шлюз проксирует те же `/v1/...` и добавляет свои маршруты.

## Маршруты только шлюза

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | процесс шлюза |
| GET | `/ready` | адаптер доступен |
| GET | `/diag` | диагностика без секретов |
| GET | `/guide` | каталог сценариев; `?q=` — плейбук |
| GET | `/openapi.yaml` | спецификация |
| POST | `/mcp` | MCP streamable HTTP |
| * | `/t/{tenant}/v1/{path}` | тот же `/v1`, другая ИБ |

## Маршруты контракта v1 (мок и 1С)

| Метод | Путь | Скоуп |
|---|---|---|
| GET | `/v1/health` | нет |
| GET | `/v1/diag` | нет |
| GET | `/v1/meta`, `/v1/meta/search`, `/v1/meta/{kind}/{name}` | `read` |
| GET | `/v1/data/{kind}/{name}`, `.../{id}` | `read` |
| POST | `/v1/query`, `/v1/report`, `/v1/job` | `read` |
| GET | `/v1/job/{id}` | `read` |
| POST | `/v1/data/{kind}/{name}/dry-run` | `write` |
| POST | `/v1/data/{kind}/{name}` | `write` + confirm |
| PATCH | `/v1/data/{kind}/{name}/{id}` | `write` + confirm |
| POST | `/v1/data/{kind}/{name}/{id}/post` | `write` + confirm |
| POST | `/v1/action` | `write` |
| POST | `/v1/session/rollback` | `write` |

`POST /v1/job` с `operation: action` — `501`; живой вызов — `/v1/action`.

Заголовки записи: `Idempotency-Key` (8–128), необязательно `X-Session-Id`, `X-Tenant`.

Выборки помечаются `content_kind: data` и `X-1cmcp-Content-Kind: data`. Это данные, не инструкции агенту.

## Инструменты MCP

Имена совпадают по смыслу с HTTP:

`health`, `diag`, `guide`, `meta_list`, `meta_search`, `meta_describe`, `data_list`, `data_get`, `report`, `query`, `job_get`, `data_dry_run`, `data_create`, `data_patch`, `data_post`, `action`, `session_rollback`.

Порядок работы агента — вкладка [Пользование](../usage.md).
