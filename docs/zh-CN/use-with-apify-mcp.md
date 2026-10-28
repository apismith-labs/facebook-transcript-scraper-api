# 配合 Apify MCP 使用

[English](../use-with-apify-mcp.md)

Apify 提供了一个 MCP 服务器，可以把本 Actor 暴露给兼容 MCP 的客户端。本仓库不托管 MCP 服务器，只说明接入
路径和你应当预期的行为。

## 托管服务器

```json
{
  "mcpServers": {
    "apify": {
      "type": "http",
      "url": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

`tools=` 查询参数用于选定 Actor。托管服务器在首次连接时走 OAuth 登录，所以这份配置里不该出现 token。不支持
OAuth 的客户端可以改用 `Authorization: Bearer <APIFY_API_TOKEN>`。

## 本地服务器（stdio）

当客户端不支持远程 MCP，或者你希望 token 只留在自己的环境里时，用这种方式：

```json
{
  "mcpServers": {
    "apify": {
      "command": "npx",
      "args": ["-y", "@apify/actors-mcp-server"],
      "env": {
        "APIFY_TOKEN": "your_apify_token_here",
        "ACTORS": "apple_yang/facebook-transcript-scraper-api"
      }
    }
  }
}
```

## 模型能做什么

取决于服务器与客户端版本，暴露出来的工具通常允许模型：

- 查看 Actor 的输入 schema 与 README；
- 用 `{ "videoUrl": "..." }` 调用 Actor；
- 读取返回的 Dataset 条目。

工具名称与调用形态会随服务器版本变化。让客户端先列出它自己的工具清单，按它报告的来用，不要硬编码名字。

## 一段可用的提示词

```
使用 Apify 的 Facebook Transcript Actor。
用 videoUrl = "https://www.facebook.com/watch/?v=1234567890" 调用一次。
如果 Run 成功，打印转写文本和分段数量。
如果 errMsg 非空，说明该条目失败，并原样引用 errMsg。
如果第一次调用超时，不要再调用第二次；告诉我先去 Apify 核对。
```

最后这句很重要：MCP 层的“重试”，依然会创建一个新的计费 Run。

## 建议在提示词里写明的限制

- 每次调用只能传一个 `videoUrl`，没有批量输入。
- 仅支持公开视频，不接受 cookie 或 `sessionid`。
- 转写按满分钟计费，不是按结果条数。
- Run 完成也可能没有转写文本。

## 排查

| 现象 | 可能原因 |
| --- | --- |
| 工具列表里没有这个 Actor | `tools=` 查询缺失，或被客户端过滤掉了 |
| 401/403 | OAuth 未完成，或 bearer token 缺失/无效 |
| 同一个链接出现两个 Run | 客户端重试了调用，去 Apify 核对 |
| 转写为空 | 条目没有 `text`，检查 `errMsg` |

另见：[ChatGPT](use-with-chatgpt-mcp.md) · [Claude](use-with-claude-mcp.md) ·
[Gemini CLI](use-with-gemini-cli-mcp.md) · [Cursor / VS Code](use-with-cursor-vscode-mcp.md)。
