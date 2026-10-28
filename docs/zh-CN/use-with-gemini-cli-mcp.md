# 配合 Gemini CLI 使用

[English](../use-with-gemini-cli-mcp.md)

Gemini CLI 从设置文件读取 MCP 服务器配置（通常是 `~/.gemini/settings.json`），可以直接连接远程 HTTP 服务器。

## 配置

```json
{
  "mcpServers": {
    "apify": {
      "httpUrl": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

如果你的 Gemini CLI 版本要求用请求头而非 OAuth：

```json
{
  "mcpServers": {
    "apify": {
      "httpUrl": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api",
      "headers": {
        "Authorization": "Bearer ${APIFY_TOKEN}"
      }
    }
  }
}
```

优先用环境变量，不要粘贴字面 token——shell 历史和 dotfiles 都会泄露。

## 确认已发现

```bash
gemini
/mcp
```

Apify 服务器应当出现在列表里，并附带工具清单。工具名称随服务器版本变化，请以 `/mcp` 的输出为准，不要照抄
本文里的名字。

## 第一次请求

```
用 Apify MCP 工具转写：
https://www.facebook.com/watch/?v=1234567890

打印转写文本、分段数量和 run ID。
如果工具调用失败或超时，不要重试，直接报告错误。
```

## 非交互调用

```bash
gemini -p "用 Apify 工具转写 https://www.facebook.com/watch/?v=1234567890，只打印转写文本" \
  --allowed-mcp-server-names apify
```

参数名随版本变化，写脚本前先用 `gemini --help` 确认。

## 注意事项

- 每次调用都可能创建一个计费 Run。
- 一次只能传一个链接，没有批量参数。
- 仅支持公开视频。

另见：[Apify MCP](use-with-apify-mcp.md) · [成本](cost-and-limits.md)。
