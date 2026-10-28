# Actor 审计 —— `apple_yang/facebook-transcript-scraper-api`

[English](../../audit/actor_audit_20261028.md)

审计日期：**2026-10-28**。锁定 build：**0.0.18**（`fZIlpYENof2jYqIJc`，构建完成于
2026-10-19T03:13:17.800Z）。本文记录的是直接从 Apify 公开 API 读到的内容，以及仍未验证的部分。它是本仓库
客户端代码的证据基础。

## 证据来源

| 来源 | 确认了什么 |
| --- | --- |
| `GET /v2/acts/apple_yang~facebook-transcript-scraper-api` | Actor ID `qoPsXcbeGbncRrc4N`、tagged `latest` 为 build 0.0.18、默认运行参数（4096 MB、3600 s）、计费事件 |
| `GET /v2/actor-builds/fZIlpYENof2jYqIJc` | 逐字读取的 `inputSchema`、`actorDefinition.output`、`actorDefinition.storages.dataset.fields` |
| `GET /v2/actors/qoPsXcbeGbncRrc4N/builds/fZIlpYENof2jYqIJc/openapi.json` | Run 接口路径、`token` 查询参数、build id 请求头 |
| `https://apify.com/apple_yang/facebook-transcript-scraper-api.md` | README 层面的行为：仅公开视频、免费 5 分钟限制、输出字段说明 |
| 本次审计未执行任何线上 Run | 下文涉及运行时行为的结论，凡适用处均标注为未验证 |

## 输入契约

```json
{
  "videoUrl": "https://www.facebook.com/61567530334836/videos/1115932820735409/"
}
```

该 build 声明 `required: ["videoUrl"]`，且只声明了一个属性。**没有** `bulkUrls`，**没有** `usernames`，
**没有** `sessionid`，**没有** `enhancedcrawl`。这是与 Instagram 姊妹 Actor 最大的差异，也直接决定了本仓库
的形态：批量处理是客户端编排器，一个链接创建一个 Run，而不是 Actor 的一种模式。

`prefill` 是表单预填，不是运行时默认值。这个字段是真正的必填项。

## 输出契约

Actor 声明的输出是一个 `results` 字符串，模板指向默认 Dataset 条目地址——不是内联数组。调用方必须去读
Dataset。

锁定 build 声明的 Dataset 字段（共 17 个）：

`url`、`title`、`videoUrl`、`audioUrl`、`createTime`、`playCount`、`commentCount`、`reactionCount`、
`likesCount`、`shareCount`、`duration`、`nickname`、`avatarUri`、`text`、`segments[]`、`errMsg`、
`timestamp`

### 解析前值得知道的几处不一致

1. **README 的输出表里没有 `likesCount` 与 `shareCount`**，但 Dataset schema 声明了它们。两者都没有与
   `reactionCount` 区分开的文档说明。请原样保留，不要臆造语义。
2. **`videoUrl` 是媒体/CDN 链接**，不是页面链接。绝不要把它当作 `videoUrl` 输入回传。
3. **Dataset 定义里所有字段都标为 `required`**，包括 `text` 和 `segments`。这只是 schema 声明，不能证明
   每个条目都带这些字段。请逐条目校验，把缺字段当正常情况处理。
4. **`errMsg` 是条目级业务错误。** Run 状态 `SUCCEEDED` 但 `errMsg` 非空，对这条数据就是失败。
5. `duration` 的单位应为秒（README 写的是“video duration (seconds)”）；`createTime` 是 10 位整数，样本
   与 Unix 秒一致。两者除文档外仍未经运行验证。

## 2026-10-28 采集的价格

| 事件 | 价格 | 说明 |
| --- | --- | --- |
| `apify-default-dataset-item` | $0.001 / 条 | 主事件；Store 页的 “$1.00 / 1,000 results” 指的就是它 |
| `speech2text` | $0.0045 / 分钟（FREE）→ $0.0035（BRONZE）→ $0.003（SILVER）→ $0.002（GOLD+） | 按分钟计费；不足 1 分钟按 1 分钟计 |

Store 页的标题价对于任何超过几秒的视频都低估了真实成本，因为它漏掉了转写事件。一条 10 分钟的视频在 FREE
档约 **$0.046**，GOLD 档约 **$0.021**。`../cost-and-limits.md` 与本仓库的 `scripts/estimate_cost.py` 实现了这个
模型。

价格在服务端是有版本的。`pricingInfos` 里还存在一份更早的、已被取代的价目（2026-03-06：每条结果 $0.0006
+ 每分钟 $0.001）。不要把旧数字写死。

## 限制

- 仅公开视频。私密、仅好友可见、已删除或地区锁定的内容可能失败。
- 免费套餐：视频不超过 5 分钟。付费套餐：文档说明时长不限。
- 仅音频：画面上的文字不会被转写。
- 转写质量取决于音轨质量。

## 本仓库假设了什么、拒绝假设什么

假设（保守，且写入代码）：

- 提交一个链接产生一个 Dataset 条目。客户端额外容忍零条或多条，并报告 `empty` 或聚合状态，而不是猜测。
- `text` 才是转写文本；`title` 是配文，永远不当转写用。
- `errMsg` 非空即判定该条目无效，即使 `text` 也有内容。

不假设：

- `text` 缺失就一定代表视频没有说话（也可能是转写失败）。
- `segments` 一定格式良好。每个元素都会校验 `start`/`end` 为有限数值且 `start <= end`；非法元素会从归一化
  视图中剔除，但保留在原始条目里。
- 短链与分享链接一定可用。客户端校验器接受它们，但 Actor 侧尚未验证。

## 复现这次审计

```bash
curl -s "https://api.apify.com/v2/acts/apple_yang~facebook-transcript-scraper-api" | jq '.data.taggedBuilds.latest'
curl -s "https://api.apify.com/v2/actor-builds/fZIlpYENof2jYqIJc" | jq -r '.data.inputSchema'
curl -s "https://api.apify.com/v2/actor-builds/fZIlpYENof2jYqIJc" | jq '.data.actorDefinition.storages.dataset.fields'
```

如果 tagged build 发生变化，请重跑这次审计并更新契约 JSON，然后再改动客户端里的 `APPROVED_BUILD_NUMBER`。
