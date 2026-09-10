# Коды ошибок

Тело — RFC 7807, `Content-Type: application/problem+json`. Поля: `type`, `title`, `status`, `code`, `detail`.

| HTTP | `code` | Когда | Что делать |
|---|---|---|---|
| 401 | `unauthorized` | нет/неверный Bearer | выпустить токен, проверить хеш и `Активен` |
| 403 | `forbidden` | нет скоупа или ACL | скоупы и `мкпПравилаДоступа` |
| 404 | `not_found` | нет объекта, ссылки или имя `мкп*` | `meta_search`, не служебные объекты |
| 404 | `unknown_tenant` | `X-Tenant` не из `ONEC_TENANTS` | карта тенантов |
| 400 | `bad_request` | кривой JSON, нет `Idempotency-Key` | исправить тело/заголовок |
| 400 | `query_rejected` | запрос не выборка / лимит строк | валидатор: только `ВЫБРАТЬ`/`SELECT` |
| 400 | `confirm_required` | запись без dry-run или просроченный токен | сначала dry-run |
| 400 | `limit_exceeded` | сумма или количество выше лимита клиента | уменьшить документ или поднять `ЛимитСуммы` / `ЛимитКоличества` |
| 409 | `idempotency_conflict` | тот же ключ, другое тело | новый `Idempotency-Key` |
| 422 | `fill_check_failed` | не заполнено поле | текст `detail` — что исправить |
| 422 | `posting_failed` | проведение платформы | исправить по сообщению 1С |
| 429 | `rate_limited` | шлюз, слишком часто | подождать `Retry-After` или поднять `RATE_LIMIT_PER_MINUTE` |
| 501 | `not_implemented` | путь не из этой сборки v1 | смотреть OpenAPI |
| 503 | `adapter_unavailable` | `/ready`, 1С/мок недоступен | `ONEC_BASE_URL`, сеть, публикация |

Шлюз не исполняет текст из полей 1С как команды.
