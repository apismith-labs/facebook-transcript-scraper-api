# 配合 Cursor 与 VS Code 使用

[English](../use-with-cursor-vscode-mcp.md)

两个编辑器都支持通过项目级或用户级配置文件接入 MCP 服务器。

## Cursor

项目内的 `.cursor/mcp.json`，或全局 MCP 设置：

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

Cursor 支持带 OAuth 的远程服务器，按提示在浏览器里完成登录即可。

## VS Code

`.vscode/mcp.json`：

```json
{
  "servers": {
    "apify": {
      "type": "http",
      "url": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

在命令面板里执行 **MCP: List Servers** 启动服务器并查看工具。部分 VS Code 版本需要 `inputs` 条目来传密钥；
请把 token 放在编辑器的密钥存储里，而不是提交进仓库的文件。

## 本地 stdio 备选方案

当远程 MCP 被策略阻止时：

```json
{
  "mcpServers": {
    "apify": {
      "command": "npx",
      "args": ["-y", "@apify/actors-mcp-server"],
      "env": {
        "APIFY_TOKEN": "${env:APIFY_TOKEN}",
        "ACTORS": "apple_yang/facebook-transcript-scraper-api"
      }
    }
  }
}
```

## 给智能体的提示词

```
对下面这个链接，用 Apify 的 Facebook Transcript 工具只调用一次：
https://www.facebook.com/watch/?v=1234567890

然后：
- 如果 errMsg 非空，报告失败并停止；
- 否则逐字打印 text 和分段数量。
调用超时绝不重试；第一个 Run 可能已经存在。
```

## 仓库卫生

- 本仓库已忽略 `.vscode/` 与 `.cursor/`；团队需要时可以提交一份不含密钥的示例配置。
- 不要让智能体把 token 写进 `.cursor/mcp.json`。

另见：[Apify MCP](use-with-apify-mcp.md) · [生产环境清单](production-integration-checklist.md)。
