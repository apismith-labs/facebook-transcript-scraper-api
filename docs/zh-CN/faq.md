# 常见问题

[English](../faq.md)

### 需要 Apify 账号吗？

需要。Actor 运行在 Apify 上，按事件计费。请在 Apify Console 的 **Settings → API & Integrations** 里创建
token，然后导出为 `APIFY_TOKEN`。

### 一次调用能转写多条视频吗？

不能。Actor 输入只有一个 `videoUrl` 字段，提交数组不在 schema 里。请用 CSV 批量执行器，它为每一行创建
一个 Run。

### 能抓取某个主页或个人页的帖子吗？

不能。这个 Actor 没有 `usernames`/主页模式，它只转写你手上已有的视频链接。需要发现内容的话，请另找一个
抓取工具，再把拿到的视频链接交给这里。

### 为什么账单比“$1 每 1000 条结果”高？

因为那个标题价只覆盖数据集条目事件（$0.001/条）。转写是按满分钟计费的（FREE 档 $0.0045，GOLD 及以上
$0.002）。一条 10 分钟的视频在 FREE 档约 $0.046。详见[成本与限制](cost-and-limits.md)。

### Run 成功但 `text` 是空的，是 bug 吗？

不一定。`no_transcript` 表示该条目没有可用文本：可能是静音视频、纯音乐片段、语音识别失败，或者 Actor 没
输出这个字段。先看 `errMsg`、`title`、`duration`，再怀疑客户端。

### `errMsg` 非空代表什么？

这是条目级的业务失败。即使 `text` 也有内容，客户端也会判定为 `actor_error`，绝不计为成功。常见原因：私密
视频、已删除的帖子、地区限制，或不受支持的链接形态。

### 支持哪些 Facebook 链接形态？

`/watch/?v=`、`/{page}/videos/{id}/`、`/videos/{id}/`、`/reel/{id}/`、`/video.php?v=`、
`/share/v/{code}/`、`/share/r/{code}/`，以及 `fb.watch/{code}/`。跟踪参数会被剥离。详见
[可接受的链接形态](input-output-fields.md#accepted-url-forms)。

### 我的分享链接被拒绝了，为什么？

只接受上面列出的形态。被 Markdown 包裹的链接、`http://` 链接、带 fragment 的链接、未知路径，都会被有意
拒绝，而不是靠猜。请在浏览器里打开该链接，复制最终的 `facebook.com/...` 地址。

### 能用私密或仅好友可见的视频吗？

不能。Actor 只声明支持公开视频，也没有 cookie 或 `sessionid` 输入。

### 有时长限制吗？

免费套餐可转写 5 分钟以内的视频。付费套餐按文档不限时长。但视频越长，费用也按比例增加。

### 怎么避免重试导致重复计费？

永远不要重试创建 `POST`。客户端对同一输入最多创建一次；响应不明确时记为 `creation_unknown` 并停止。如果
Run 已经存在，用 `--resume RUN_ID` 恢复（只发 GET）。

### 怎么知道结果是哪个 Build 产出的？

客户端锁定 Build `0.0.18`，并校验 Build ID `fZIlpYENof2jYqIJc`。journal 会为每个 Run 记录 `buildNumber`、
`buildId` 与 `buildVerification`。

### 客户端需要第三方依赖吗？

不需要。Python 用标准库，Node.js 用内置 `fetch`。测试同样只需要运行时本身。

### 没有 token 能跑测试吗？

能，CI 就是这么做的。所有测试都用合成 fixture 与假 transport，不碰网络。

### 结果文件写到哪里？

单链接命令行只有在你传 `--output` 或 `--json` 时才写文件；journal 落在 `sample-output/generated/`。批量
执行器会在 CSV 同目录（或 `--output` 指定处）写入唯一的 `facebook-batch-results-<UTC>.json`，并在同目录
写一份 journal。
