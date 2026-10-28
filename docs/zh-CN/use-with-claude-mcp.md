# 配合 Claude 使用（MCP 连接器）

[English](../use-with-claude-mcp.md)

在符合条件的套餐上，Claude 的桌面端与网页端支持远程 MCP 连接器，Claude Desktop 也支持本地 stdio 服务器。
两条路径都能接到这个 Actor。

## 远程连接器

1. 打开 **Settings → Connectors → Add custom connector**。
2. 填入地址：

   ```
   https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api
   ```

3. 完成 Apify 的 OAuth 登录。
4. 新建会话并启用该连接器。

## Claude Desktop（stdio）

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

改完配置后重启 Claude Desktop。条件允许时，把 token 放在桌面端的环境变量里，而不是放在会被同步的文件中。

## 第一次请求

```
用 Apify 工具转写这条公开的 Facebook 视频：
https://www.facebook.com/watch/?v=1234567890

展示：状态、转写文本、分段数量、时长。
如果条目的 errMsg 非空，原样引用它，并且不要重试这次调用。
```

## 关于模型行为的提醒

- Claude 可能倾向于概括而不是逐字引用。需要精确文本时，明确要求逐字输出。
- Dataset 条目里包含 CDN 媒体链接，会过期，不要当作长期地址。
- 如果模型在超时后提议再调用一次，请拒绝——第一个 Run 可能已经存在了。

## 不新建 Run 也能核对

调用超时后，先要到 `runId`，然后做只读检查：

```bash
export APIFY_TOKEN='...'
python scripts/check_apify_run.py RUN_ID
```

另见：[Apify MCP](use-with-apify-mcp.md) · [错误处理](error-handling-and-retries.md)。
