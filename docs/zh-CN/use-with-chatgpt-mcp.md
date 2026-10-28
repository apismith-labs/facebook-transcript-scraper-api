# 配合 ChatGPT 使用（MCP 连接器）

[English](../use-with-chatgpt-mcp.md)

在支持连接器的套餐上，ChatGPT 可以把远程 MCP 服务器当作连接器调用。可用性、命名和菜单位置都会变化，请把
本文当作结构参考，而不是逐步点击的脚本。

## 配置

1. 在 ChatGPT 中打开 **Settings → Connectors**（或你所在套餐里的 Apps/Connectors 区域）。
2. 添加自定义连接器，填入 MCP 地址：

   ```
   https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api
   ```

3. 按提示完成 Apify 的 OAuth 授权。
4. 新开一个会话，为该会话启用这个连接器。

如果你的套餐或工作区不允许自定义连接器，请直接调用 API，或在本地运行示例。

## 第一次请求

```
用已连接的 Apify 工具转写这条公开的 Facebook 视频：
https://www.facebook.com/watch/?v=1234567890

返回转写文本和分段数量。如果 errMsg 不为空，原样引用它并停止。
```

## 需要预期的行为

- 一次调用只转写一个链接，没有多链接参数。
- 工具返回的是 Dataset 条目，不是一段转写字符串；模型必须自己读 `text`。
- Run 状态 `SUCCEEDED` 但 `text` 为空，对你的用途来说仍是失败。
- ChatGPT 可能会重试失败的工具调用，而每次重试都可能创建新的计费 Run。请在提示词和连接器说明里写明
  “不要重试”。

## 共享工作区的护栏

- 使用专门的 Apify token，并设置消费上限。
- 在不应让成员发起付费 Run 的工作区里，默认关闭该连接器。
- 不要往聊天消息里粘贴 token；用 OAuth 连接器或工作区密钥存储。
- 记录工具返回的 `runId`，便于对账。

## 限制

- 仅支持公开视频。
- Apify 免费套餐：视频不超过 5 分钟。
- 这个 Actor 没有主页或个人页列表模式。

另见：[Apify MCP](use-with-apify-mcp.md) · [FAQ](faq.md) · [成本](cost-and-limits.md)。
