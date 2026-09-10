# Справочник настроек

Здесь перечислены **все** ручки продукта: переменные окружения шлюза, флаги CLI, значения Helm, свойства HTTP-сервиса и реквизиты расширения, которые консультант заполняет данными. Если настройки нет в этой таблице — это ошибка документации (тест `test_docs_completeness` должен упасть).

Файл-образец: [`.env.example`](https://github.com/chastnik/1cmcp/blob/cursor/phase6-gateway-http-e909/.env.example) в корне репозитория. Скопируйте в `.env` (в git не коммитится). Перед правкой `.env` сделайте копию.

Лицензионный ключ продукта **не задаётся**.

## Переменные окружения шлюза и MCP

Имена совпадают с полями `Settings` (пакет `onecmcp`). Файл `.env` читается из **текущей рабочей директории** процесса.

| Переменная | Поле Settings | Умолчание | Смысл | Как изменить |
|---|---|---|---|---|
| `ONEC_BASE_URL` | `onec_base_url` | `http://127.0.0.1:18080` | корень слоя A **без** `/v1`. Мок: хост мока. Живая 1С: `http(s)://{host}/{ib}/hs/mcp` | `.env`, Compose `environment`, Helm `onec.baseUrl`; перезапуск шлюза/MCP |
| `ONEC_TOKEN` | `onec_token` | пусто | Bearer к слою A (plaintext токена). На моке `dev-token` | секрет; Helm `onec.token` → Secret `onec-token` |
| `ONEC_TIMEOUT_SECONDS` | `onec_timeout_seconds` | `30` | таймаут HTTP к адаптеру | `.env` / Helm `onec.timeoutSeconds` |
| `GATEWAY_HOST` | `gateway_host` | `0.0.0.0` | bind REST и `/mcp` у `serve` | `.env` или `serve --host` (флаг важнее). Helm: `gateway.host` → args `--host` |
| `GATEWAY_PORT` | `gateway_port` | `8000` | порт `serve` и умолчание порта `mcp --transport streamable-http` | `.env` или `--port`. Helm: `gateway.port` → args `--port` и `containerPort`; сверяйте с `service.port` |
| `TENANT` | `tenant` | `default` | тенант по умолчанию, заголовок `X-Tenant` на слой A | `.env` / Helm `gateway.tenant` |
| `ONEC_TENANTS` | `onec_tenants` | пусто | карта `id=url` или JSON нескольких ИБ | `.env` / Helm `gateway.tenants`; [тенанты](../admin/tenants.md) |
| `META_CACHE_TTL_SECONDS` | `meta_cache_ttl_seconds` | `60` | кэш ответов `/v1/meta*` на шлюзе; `0` — не кэшировать | `.env` / Helm `gateway.metaCacheTtlSeconds` |
| `ONEC_PRESET` | `onec_preset` | `auto` | `auto` \| `ut11` \| `ka2` \| `erp2` \| `bp30` \| `none` | `.env` / Helm `onec.preset`; [пресеты](../skills.md) |
| `RATE_LIMIT_PER_MINUTE` | `rate_limit_per_minute` | `120` | скользящее окно **60 с**: не больше N запросов с одного ключа; `0` — выключить. Не считаются `/`, `/health`, `/ready` | `.env` / Helm `gateway.rateLimitPerMinute` |
| `MCP_HTTP_PATH` | `mcp_http_path` | `/mcp` | путь streamable HTTP на процессе `serve` | `.env` / Helm `gateway.mcpHttpPath` / `mcp --path` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `otel_exporter_otlp_endpoint` | пусто | экспорт OTLP; нужен extra `otel` | `.env` / Helm `gateway.otelExporterOtlpEndpoint` |

Ключ rate limit: SHA-256 префикс Bearer (`tok:…`); если токена нет — IP клиента (`ip:…`).

Неизвестные ключи в `.env` игнорируются (`extra=ignore`). `.env` читается из **текущей рабочей директории** процесса шлюза/MCP.

## Флаги командной строки

Полные команды: [CLI](cli.md).

| Команда | Флаг | Умолчание | Как связано с env |
|---|---|---|---|
| `serve` | `--host` | `GATEWAY_HOST` | перекрывает env |
| `serve` | `--port` | `GATEWAY_PORT` | перекрывает env |
| `mock1c` | `--host` | `0.0.0.0` | только CLI |
| `mock1c` | `--port` | `18080` | только CLI |
| `mcp` | `--transport` | `stdio` | `stdio` или `streamable-http` |
| `mcp` | `--host` | `127.0.0.1` (HTTP) | только HTTP-транспорт |
| `mcp` | `--port` | `GATEWAY_PORT` | HTTP-транспорт |
| `mcp` | `--path` | `/mcp` | путь streamable HTTP |

## Helm `deploy/helm/onecmcp`

Чарт версии приложения совпадает с пакетом (`0.7.0`). Ключа продукта в values нет.

| Ключ values.yaml | Куда попадает | Умолчание | Как изменить |
|---|---|---|---|
| `replicaCount` | число подов | `1` | `helm upgrade --set replicaCount=2` |
| `image.repository` | образ | `onecmcp` | свой registry |
| `image.tag` | тег образа | `0.7.0` | тег сборки |
| `image.pullPolicy` | политика pull | `IfNotPresent` | |
| `imagePullSecrets` | secrets pull | `[]` | private registry |
| `nameOverride` | имя чарта | `""` | |
| `fullnameOverride` | полное имя | `""` | |
| `service.type` | Service | `ClusterIP` | `NodePort` / `LoadBalancer` |
| `service.port` | порт Service | `8000` | должен совпадать с портом контейнера |
| `resources` | CPU/RAM | `{}` | limits/requests |
| `nodeSelector` | узлы | `{}` | |
| `tolerations` | taints | `[]` | |
| `affinity` | anti-affinity | `{}` | |
| `onec.baseUrl` | `ONEC_BASE_URL` | `http://1c.internal/ib/hs/mcp` | |
| `onec.token` | Secret `onec-token` → `ONEC_TOKEN` | `""` | не коммитить боевой токен |
| `onec.timeoutSeconds` | `ONEC_TIMEOUT_SECONDS` | `30` | |
| `onec.preset` | `ONEC_PRESET` | `auto` | |
| `gateway.host` | `serve --host` | `0.0.0.0` | bind внутри пода |
| `gateway.port` | `serve --port` и `containerPort` | `8000` | должен совпадать с `service.port`, если targetPort = имя `http` |
| `gateway.tenant` | `TENANT` | `default` | |
| `gateway.tenants` | `ONEC_TENANTS` | `""` | |
| `gateway.metaCacheTtlSeconds` | `META_CACHE_TTL_SECONDS` | `60` | |
| `gateway.rateLimitPerMinute` | `RATE_LIMIT_PER_MINUTE` | `120` | |
| `gateway.otelExporterOtlpEndpoint` | `OTEL_EXPORTER_OTLP_ENDPOINT` | `""` | |
| `gateway.mcpHttpPath` | `MCP_HTTP_PATH` | `/mcp` | |

Чарт: `Chart.yaml` `version` / `appVersion` = `0.7.0` (совпадает с пакетом `onecmcp`). Probes зашиты в шаблон: liveness `GET /health`, readiness `GET /ready` (не выносятся в values). Secret `onec-token` берётся из `onec.token`.

## Docker Compose (`docker-compose.yml`)

| Ключ в файле | Умолчание поставки | Как изменить |
|---|---|---|
| `mock1c.build.context` / `dockerfile` | `.` / `gateway/Dockerfile` | свой контекст |
| `mock1c.command` | `python -m onecmcp mock1c --host 0.0.0.0 --port 18080` | другой порт мока |
| `mock1c.ports` | `18080:18080` | проброс на хост |
| `mock1c.healthcheck` | `GET /v1/health` каждые 5 с, timeout 3 с, 8 попыток | интервалы Compose |
| `gateway.build` | тот же Dockerfile | |
| `gateway.command` | `python -m onecmcp serve --host 0.0.0.0 --port 8000` | `--port` вместе с `ports` |
| `gateway.environment.ONEC_BASE_URL` | `http://mock1c:18080` | URL живой 1С, если Compose без мока |
| `gateway.environment.ONEC_TOKEN` | `dev-token` | plaintext клиента |
| `gateway.ports` | `8000:8000` | проброс REST и `/mcp` |
| `gateway.depends_on.mock1c.condition` | `service_healthy` | не стартовать шлюз до мока |
| `gateway.healthcheck` | `GET /health` каждые 5 с, timeout 3 с, 8 попыток | |

Любую переменную из таблицы env добавьте в `gateway.environment`, если умолчания не подходят (`ONEC_PRESET`, `RATE_LIMIT_PER_MINUTE`, `ONEC_TENANTS`, …).

## HTTP-сервис расширения `мкпAPI`

| Свойство | Значение поставки | Как изменить |
|---|---|---|
| `RootURL` | `mcp` | Конфигуратор; синхронно поменять публикацию и `ONEC_BASE_URL` |
| `ReuseSessions` | `AutoUse` | Конфигуратор |
| `SessionMaxAge` | `20` | Конфигуратор, секунды |

## Настройки в данных 1С (не env)

| Объект | Поля | Как изменить |
|---|---|---|
| `мкпКлиентыИнтеграции` | `ХешТокена`, `Скоупы`, `ПользовательИБ`, `Активен`, `ЛимитСуммы`, `ЛимитКоличества` | карточка; токен — обработка администрирования. [Клиенты](../admin/clients.md) |
| `мкпПравилаДоступа` | `Клиент`, `ВидОбъекта`, `ИмяОбъекта`, `Операция`, `Разрешено`, `Поля` | записи регистра. [ACL](../admin/access.md) |
| `мкпИменованныеЗапросы` | `ТекстЗапроса`, `СхемаПараметров`, `СхемаРезультата`, `ЛимитСтрок`, `ТаймаутСекунд`, `Активен` | карточка запроса |
| `мкпДействияИнтеграции` | `ИмяДействия`, `Разрешено`, `ВидОбъекта`, `ИмяОбъекта` | карточка; `Разрешено = нет` → не 200 на `/v1/action` |
| `мкпСемантическийСловарь` | `ВидОбъекта`, `ИмяОбъекта`, `ИмяПоля`, `Синонимы`, `Описание`, `Примеры` | записи регистра; шлюз подмешивает пресет |

Служебные регистры (`мкпЖурналВызовов`, `мкпКлючиИдемпотентности`, `мкпТокеныПодтверждения`, `мкпОперацииСессии`, `мкпСостоянияЗаданий`) консультант **не заполняет** — их пишет адаптер.

## Стендовые токены мока

| Токен | Скоупы | Лимиты |
|---|---|---|
| `dev-token` | `read` | нет |
| `dev-write-token` | `read,write` + ACL демо-объектов | нет |
| `dev-limit-token` | `read,write` + ACL | сумма 100, количество 1 |
| `write-only-token` | `write` | нет |
| `deny-shipments-token` | `read`, отгрузки запрещены ACL | нет |

## Вшитые константы (не переменные окружения)

Их нельзя поменять `.env` без правки кода/расширения. Чтобы изменить — форк/патч и новая сборка.

| Константа | Значение | Где | Зачем |
|---|---|---|---|
| TTL `confirm_token` | **600 с** | мок `writes.TTL_SECONDS`, регистр `мкпТокеныПодтверждения.Истекает` | dry-run протухает, нужен новый предпросмотр |
| Длина `Idempotency-Key` | **8–128** символов | заголовок записи | повтор с тем же телом не создаёт дубль |
| Лимит строк произвольного `query` | **1–10000**, умолчание **1000** | валидатор слоя A | отсекает «выгрузить всё» |
| Длина текста `query` | **≤ 20000** | валидатор | |
| `meta_search` `q` | **1–200** символов | мок/OpenAPI | |
| Окно rate limit | **60 с** | шлюз | число — `RATE_LIMIT_PER_MINUTE` |
| `ХешТокена` | SHA-256, **64** символа hex | справочник | plaintext в карточке не хранится |
| `PYTHONUNBUFFERED` | `1` | `gateway/Dockerfile` | логи без буфера |
| `EXPOSE` / `CMD` образа | порт **8000**, `serve --host 0.0.0.0 --port 8000` | Dockerfile | Helm перекрывает `args` из `gateway.host`/`gateway.port` |

## Пакет Python `onecmcp`

| Установка | Что даёт |
|---|---|
| `pip install -e gateway` / образ | runtime: FastAPI, MCP, uvicorn |
| `pip install -e "gateway[dev]"` | pytest, coverage, openapi-spec-validator, pyyaml |
| `pip install -e "gateway[otel]"` | SDK + OTLP HTTP exporter; без extra спаны no-op даже при заданном endpoint |

Версия пакета: **0.7.0** (`gateway/pyproject.toml`). Ключа продукта нет.
