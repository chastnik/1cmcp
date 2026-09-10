# Подключение агентов

Готовые пресеты. Ключ продукта 1cmcp не нужен. 1С в интернет не публикуйте: агент видит шлюз или stdio MCP.

| Файл | Куда |
|---|---|
| [claude-desktop.mcp.json](claude-desktop.mcp.json) | Claude Desktop: `claude_desktop_config.json` |
| [cursor.mcp.json](cursor.mcp.json) | Cursor / Claude Code: `.mcp.json` проекта |
| [n8n-guide.json](n8n-guide.json) | n8n: импорт workflow, `GATEWAY` = `http://gateway:8000` |

Тот же JSON для Claude Desktop лежит в [`../claude-desktop.mcp.json`](../claude-desktop.mcp.json).

Dify и любой HTTP-клиент: `GET {{gateway}}/guide?q=...` (плейбук) и OpenAPI `GET {{gateway}}/openapi.yaml`. PIX Operator — REST на шлюз, не `/hs/mcp`.

Подставьте абсолютный путь к Python из venv и боевые `ONEC_BASE_URL` / `ONEC_TOKEN` / `ONEC_PRESET`.
