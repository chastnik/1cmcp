# Подключение агентов

Готовые пресеты. Ключ продукта 1cmcp не нужен. 1С в интернет не публикуйте: агент видит шлюз или stdio MCP.

| Файл | Куда |
|---|---|
| [claude-desktop.mcp.json](claude-desktop.mcp.json) | Claude Desktop: `claude_desktop_config.json` |
| [cursor.mcp.json](cursor.mcp.json) | Cursor / Claude Code: `.mcp.json` проекта, stdio |
| [http.mcp.json](http.mcp.json) | Cursor и HTTP-агенты: `url` на `serve` `/mcp` |
| [n8n-guide.json](n8n-guide.json) | n8n: импорт workflow, `GATEWAY` = `http://gateway:8000` |

Тот же JSON для Claude Desktop лежит в [`../claude-desktop.mcp.json`](../claude-desktop.mcp.json).

Dify, GigaChat, YandexGPT, PIX Operator и любой HTTP-клиент: `GET {{gateway}}/guide?q=...` и OpenAPI `GET {{gateway}}/openapi.yaml`. Отдельный MCP-пресет им не нужен.

Подставьте абсолютный путь к Python из venv. URL и токен базы задайте в веб-консоли шлюза (`GATEWAY_DATA_DIR` общий с `serve`). Семя `ONEC_BASE_URL` / `ONEC_TOKEN` в env — только для первого старта.
