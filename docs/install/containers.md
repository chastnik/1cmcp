# Docker Compose и Helm

## Compose

Из корня репозитория:

```bash
docker compose up --build
```

| Сервис | Порт | Назначение |
|---|---|---|
| `mock1c` | 18080 | мок адаптера |
| `gateway` | 8000 | REST + `/mcp`; ходит в мок с `dev-token` |

Полная таблица ключей Compose, Dockerfile и Helm — в [справочнике настроек](../reference/settings.md). В поставке у шлюза явно заданы только `ONEC_BASE_URL=http://mock1c:18080` и `ONEC_TOKEN=dev-token`. Healthcheck ждёт мок (`/v1/health`), затем шлюз (`/health`).

## Helm

Чарт: `deploy/helm/onecmcp`.

```bash
helm install 1cmcp deploy/helm/onecmcp \
  --set onec.baseUrl=http://1c.internal/ib/hs/mcp \
  --set onec.token='<plaintext-токена>'
```

Все ключи `values.yaml` описаны в справочнике настроек (включая `replicaCount`, `resources`, `gateway.mcpHttpPath`). Боевой токен не коммитить: он уходит в Secret.

Образ собирается из `gateway/Dockerfile` (Python 3.12, `CMD serve`).
