# Docker Compose и Helm

## Compose

Из корня репозитория:

```bash
docker compose up --build
```

| Сервис | Порт | Назначение |
|---|---|---|
| `mock1c` | 18080 | мок адаптера |
| `gateway` | 8000 | REST, MCP `/mcp`, веб-консоль `/`; семя `dev-token` + `ADMIN_BOOTSTRAP_TOKEN=dev-admin` |

Полная таблица ключей Compose, Dockerfile и Helm — в [справочнике настроек](../reference/settings.md). Healthcheck ждёт мок (`/v1/health`), затем шлюз (`/health`). Консоль: `http://127.0.0.1:8000`, первый вход — `dev-admin`.

## Helm

Чарт: `deploy/helm/onecmcp`.

```bash
helm install 1cmcp deploy/helm/onecmcp \
  --set onec.baseUrl=http://1c.internal/ib/hs/mcp \
  --set gateway.adminBootstrapToken='<токен-первого-входа>'
```

Все ключи `values.yaml` описаны в справочнике настроек (включая `replicaCount`, `resources`, `gateway.mcpHttpPath`). Боевой токен не коммитить: он уходит в Secret.

Образ собирается из `gateway/Dockerfile` (Python 3.12, `CMD serve`).
