# 输入与输出字段

[English](../input-output-fields.md)

本文档描述 Apify Actor `apple_yang/facebook-transcript-scraper-api`。

Actor 页面：<https://apify.com/apple_yang/facebook-transcript-scraper-api>

**证据来源。** 字段与类型信息来自锁定的 Build `0.0.18`（Build ID `fZIlpYENof2jYqIJc`，构建完成于
2026-10-19T03:13:17.800Z），通过 Apify 的 build API 读取，记录在
[actor_audit_20261028.md](audit/actor_audit_20261028.md)，随后归一化为
[contracts/facebook-transcript-scraper-api-0.0.18.json](../audit/contracts/facebook-transcript-scraper-api-0.0.18.json)。
凡标注为**未验证**的内容，在你依赖它之前，都需要用自己的受控 Run 实测一次。

## 输入

小驼峰命名，只有一个字段：

```json
{
  "videoUrl": "https://www.facebook.com/61567530334836/videos/1115932820735409/"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `videoUrl` | string | **是** | 公开的 Facebook 视频页面链接。schema 中的 `prefill` 只是表单示例，不是运行时默认值 |

没有 `bulkUrls`，没有 `usernames`，没有 `sessionid`，也没有 `enhancedcrawl`。要处理多个视频，就创建多个
Run，见[批量处理](batch-processing-guide.md)。

<a id="accepted-url-forms"></a>

### 可接受的链接形态

同一个视频在 Facebook 上会以多种链接形态出现。客户端接受下列形态，并在提交前改写为规范形式：

| 形态 | 输入示例 | 规范化结果 |
| --- | --- | --- |
| 观看页 | `https://www.facebook.com/watch/?v=1234567890` | 原样，保留 `?v=` |
| 主页视频 | `https://www.facebook.com/SomePage/videos/987654321/` | 原样，保留路径大小写 |
| videos 路径 | `https://www.facebook.com/videos/1234567890` | `.../videos/1234567890/` |
| Reel | `https://www.facebook.com/reel/1234567890/` | 原样 |
| 旧版入口 | `https://www.facebook.com/video.php?v=1234567890` | 原样 |
| 分享链接 | `https://www.facebook.com/share/v/AbCdEf123/` | 原样 |
| 短链 | `https://fb.watch/AbCdEf123/` | 原样 |

客户端执行的规范化规则：

- host 只允许 `facebook.com`、`www.`、`m.`、`web.`、`fb.watch`、`www.fb.watch`。`m.` 与 `web.` 会被改写为
  `www.facebook.com`。
- 只接受 `https`；`http` 链接直接报错，不会静默升级。
- 跟踪参数（`mibextid`、`rdid`、`ref`、`sfnsn` 等）会被丢弃。`watch` 与 `video.php` 要求恰好一个数字型
  `v`，并且必须保留；其他形态靠路径定位视频，因此 query 会被整体丢弃。
- 拒绝 fragment、内嵌 userinfo，以及非默认端口。
- 长度超过 2048 字符的链接会被拒绝。

明确拒绝：`/login`、`/groups/...`、`/stories/...`、`/photo/...`、`/share/x/...`、被 Markdown 包裹的链接，
以及任何不符合上表的路径。如果 Facebook 推出了新的分享形态，请更新校验器，而不是放宽成“什么都收”。

> **未验证：** Actor 自身能否解析 `fb.watch` 与 `/share/{v,r}/` 链接。客户端会把它们原样传下去；解析失败
> 会以 `actor_error` 的形式暴露。

## 输出

Actor 声明的输出是一个 `results` 字符串，内容指向 Dataset 条目的 URL——不是内联数组。必须去读 Dataset。

### Dataset 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `url` | string | Facebook 视频链接；可能与你提交的链接不同 |
| `title` | string | 标题/配文，**不是**转写文本 |
| `videoUrl` | string | 媒体/CDN 链接。绝不要把它当作 `videoUrl` 输入回传 |
| `audioUrl` | string | 媒体链接；可能为空或缺失 |
| `createTime` | integer | 10 位数值，与 Unix 秒一致；单位**未验证** |
| `playCount` | integer | 播放数（有数据时） |
| `commentCount` | integer | 评论数 |
| `reactionCount` | integer | 表情互动数 |
| `likesCount` | integer | schema 中有声明，但 README 未提及；语义**未验证** |
| `shareCount` | integer | schema 中有声明，但 README 未提及；语义**未验证** |
| `duration` | number | 应为秒（README 写的是秒） |
| `nickname` | string | 创作者显示名 |
| `avatarUri` | string | 创作者头像；可能是临时链接 |
| `text` | string | **转写文本本身的字段，应用程序真正消费的内容** |
| `segments` | array | 元素含 `start`、`end`、`text`；按秒理解 |
| `errMsg` | string | 条目级业务错误。非空即代表该条目失败 |
| `timestamp` | string | 响应时间戳，示例中为 ISO 8601 |

Dataset schema 把 17 个字段全部标为 `required`。这只是 schema 的声明，**不能**当作“每个条目都一定带这些
字段”的证据。请逐条目校验，永远不要把缺字段当成崩溃。

### 解析规则

按顺序判断——Python 与 Node.js 客户端就是这么实现的：

1. **Dataset 为空** → `empty`。
2. **任一条目的 `errMsg` 非空** → `actor_error`。即使 `text` 有内容，也不算成功。
3. **至少存在一个非空字符串 `text`** → `success`。
4. **没有可用文本**：`text` 为 null、缺失或空字符串 → `no_transcript`；类型不支持 → `unknown`。

补充建议：

- 保留未知的额外字段，不要因此判定条目失败；Actor 随时可能加字段。
- 无论你构建什么归一化记录，都把原始条目一并留存。
- `segments` 的每个元素都会校验：`start`/`end` 为有限数值、`start >= 0`、`end >= start`、`text` 为字符串。
  不合法元素会从归一化结果中剔除，但仍保留在原始条目里。
- `text` 缺失并不能证明视频没有语音，也可能是转写失败了。

## 客户端返回结构

Python 的 `TranscriptResult` 与 Node.js 的结果对象暴露同样的信息：

| 客户端字段（Python / Node） | 含义 |
| --- | --- |
| `status` | [错误处理](error-handling-and-retries.md)中的 8 个状态之一 |
| `text` | 转写字符串，或 `None` |
| `segments` | 归一化后的分段列表 |
| `items` | 原始 Dataset 条目，包含客户端不认识的字段 |
| `run_id` / `runId` | Run 标识 |
| `dataset_id` / `datasetId` | 默认 Dataset 标识 |
| `canonical_url` / `canonicalUrl` | 实际提交给 Actor 的链接 |
| `url_form` / `urlForm` | `watch`、`page_video`、`video`、`reel`、`video_php`、`share`、`short_link` |
| `title`、`duration`、`nickname` | 便于使用的元数据，取自转写条目 |
| `error` | 业务或传输层细节，凭据已脱敏 |
| `dataset_complete` / `datasetComplete` | 当配置的分页上限可能导致 Dataset 被截断时为 `false` |

## 仍未验证的部分

以下只与 schema 和文档核对过：

- 真实的条目数量关系：一个链接是否可能返回零个或多个条目。
- 私密、已删除、地区锁定视频的真实失败形态。
- `errMsg` 与非空 `text` 是否会同时出现，以及以哪个为准。
- `fb.watch` 与 `/share/` 链接能否被解析。
- 返回的 `url` 是原样回显，还是会被改写。
- `likesCount`/`shareCount` 是否稳定填充，以及它们与 `reactionCount` 有何区别。
- 静音或转写失败的视频是否仍会计费。

当 Actor 的 tagged build 变化时，请重跑审计并更新契约 JSON。
