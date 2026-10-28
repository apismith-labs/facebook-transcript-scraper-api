[![Facebook Transcript Scraper on Apify](https://apify.com/actor-badge?actor=apple_yang/facebook-transcript-scraper-api)](https://apify.com/apple_yang/facebook-transcript-scraper-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# Facebook Transcript Scraper API（中文）

**简体中文** · [English](README.md)

把 Apify Actor `apple_yang/facebook-transcript-scraper-api` 当作 Facebook 转写 API 使用：提交一个公开的
Facebook 视频链接，拿回转写文本、带时间戳的分段，以及视频元数据（结构化 JSON）。

本仓库是围绕这个 Actor 的**接入工具包**——可直接复用的客户端、命令行工具、CSV 批量执行器、成本估算、
经过审计的契约文档，以及一套完全离线的测试。它**不是** Actor 的源码，自身也不对外提供服务。

**[在 Apify 上试用](https://apify.com/apple_yang/facebook-transcript-scraper-api)** ·
**[价格](https://apify.com/apple_yang/facebook-transcript-scraper-api/pricing)** ·
**[快速开始](docs/zh-CN/quickstart.md)**

## 这个 Actor 能做什么、不能做什么

| 项目 | 说明 |
| --- | --- |
| 输入 | 只有一个字段：`videoUrl` |
| 模式 | 仅支持单条视频。**没有** `bulkUrls`，**没有**主页批量抓取模式 |
| 输出 | 数据集条目（dataset item），含 `text`、`segments`、媒体链接、互动数、`errMsg` |
| 批量 | 只能由客户端编排：本仓库对 **CSV 每一行创建一个独立 Run** |
| 登录态 | 不需要。只支持公开视频，没有 `sessionid`，也不需要 cookie |
| 免费套餐 | 视频时长上限 **5 分钟** |
| 计费 | 按数据集条目计费 **加上** 按转写分钟数计费，详见[成本说明](docs/zh-CN/cost-and-limits.md) |

Store 页上那句 “$1.00 / 1,000 results” 很容易被误读：它只覆盖“数据集条目”这一个计费事件。转写是按分钟
单独计费的，所以一条 10 分钟的视频在免费档大约要 **$0.046**，而不是 $0.001。

## 输出示例

下面只用于说明字段形态，不是真实抓取结果。

```json
{
  "url": "https://www.facebook.com/watch/?v=1115932820735409",
  "title": "Q & A about sleeping",
  "videoUrl": "https://video.example.invalid/clip.mp4",
  "audioUrl": "https://video.example.invalid/audio.mp4",
  "createTime": 1760410628,
  "playCount": 1374261,
  "commentCount": 502,
  "reactionCount": 75332,
  "likesCount": 75000,
  "shareCount": 1200,
  "duration": 43.5,
  "nickname": "Dr. Shu",
  "avatarUri": "https://scontent.example.invalid/avatar.jpg",
  "text": "<转写文本，若有>",
  "segments": [{ "start": 0, "end": 0.68, "text": " Hello, Dr." }],
  "errMsg": "",
  "timestamp": "2026-10-28T00:00:00.000Z"
}
```

`text` 和 `segments` 是否存在，取决于返回的条目本身。Run 状态是 `SUCCEEDED` **并不等于**一定拿到了可用
转写：务必同时检查 `errMsg` 与各字段。`likesCount` 和 `shareCount` 出现在 Actor 的 Dataset schema 里，
但 README 的输出说明中没有它们，请按可选字段处理。

## 在代码里调用

| 语言 | 指南 | 状态 |
| --- | --- | --- |
| Python 3.10+ | [examples/python](examples/python/README.zh-CN.md) | 已实现，离线测试通过 |
| Node.js 18+ | [examples/nodejs](examples/nodejs/README.zh-CN.md) | 已实现，离线测试通过 |
| Go 1.22+ | [examples/go](examples/go/README.zh-CN.md) | 已实现，离线测试通过 |
| Java 17+ | [examples/java](examples/java/README.zh-CN.md) | 已实现，离线测试通过 |
| cURL | [examples/curl](examples/curl/README.zh-CN.md) | 已实现 |
| Rust | — | 未实现，见[兼容性](docs/zh-CN/compatibility.md) |

Python（仅用标准库）：

```bash
export APIFY_TOKEN='your_apify_token_here'
export APIFY_MAX_TOTAL_CHARGE_USD=0.10
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890'
```

Node 18+（零依赖）：

```bash
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890'
```

每执行一次，都会创建一个**可能产生费用**的 Run。两个客户端都锁定 Build `0.0.18`，校验其 Build ID，
发送 `restartOnError=false`，并且**永不重试** Run 创建请求。

## 批量处理

```bash
# 仅计划：校验 CSV 并打印费用预估；不创建 Run，也不读取 token。
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv

# 执行：每个非空行一个 Run，最多 3 个并发。
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv --execute
```

Node 等价命令：`node examples/nodejs/batch-csv.mjs <file.csv> [--execute]`。

每行都以 CSV 行号作为 `rowId`，重复链接也能追溯。单行失败不会中断其他行。结果写入一个唯一命名的
JSON 文件；追加写入的 journal 会在轮询之前先记下 Run ID，因此读取失败时可以恢复，而不必再创建一个 Run。
详见[批量处理](docs/zh-CN/batch-processing-guide.md)。

## 配合 AI 智能体与 MCP 使用

这个 Actor 可以通过 Apify MCP 调用。本仓库只记录配置方法，不托管 MCP 服务器。

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

指南：[Apify MCP](docs/zh-CN/use-with-apify-mcp.md) · [ChatGPT](docs/zh-CN/use-with-chatgpt-mcp.md) ·
[Claude](docs/zh-CN/use-with-claude-mcp.md) · [Gemini CLI](docs/zh-CN/use-with-gemini-cli-mcp.md) ·
[Cursor / VS Code](docs/zh-CN/use-with-cursor-vscode-mcp.md)。

## 为什么要有这个仓库

- 契约是查证过的、版本是锁定的，不需要靠猜字段；见[审计报告](docs/zh-CN/audit/actor_audit_20261028.md)与
  [契约 JSON](docs/audit/contracts/facebook-transcript-scraper-api-0.0.18.json)。
- 针对真实场景中出现的 Facebook 链接形态做保守校验，并在提交给 Actor 之前剥离跟踪参数。
- 状态如实呈现：`actor_error` 不算成功，`no_transcript` 与 `empty` 区分开，创建结果不明时绝不重试。
- 内置成本意识，因为 Store 页的标题价漏掉了转写事件。
- 离线测试：不需要 token、不需要网络、不需要 `.env`。

## 重要限制

- 仅支持公开视频。私密、仅好友可见、已删除或地区锁定的视频可能失败。
- 只转写音轨，不读取画面上的文字。
- 免费套餐仅支持 5 分钟以内的视频。
- 客户端接受 `fb.watch` 短链与 `/share/v/<code>/` 链接，但 **Actor 侧是否支持尚未验证**——见审计报告的
  未验证清单。
- Run 成功但 `errMsg` 非空，对这条数据而言就是失败。
- 本仓库不做摘要、翻译或内容分析；请把转写结果交给你的下游模型。

## 文档

| 主题 | 文档 |
| --- | --- |
| 首次运行与配置 | [快速开始](docs/zh-CN/quickstart.md) |
| 字段与可接受的链接形态 | [输入输出字段](docs/zh-CN/input-output-fields.md) |
| 一次 Run 的真实成本 | [成本与限制](docs/zh-CN/cost-and-limits.md) |
| CSV 批量与恢复 | [批量处理](docs/zh-CN/batch-processing-guide.md) |
| 状态、退出码、重试规则 | [错误处理与重试](docs/zh-CN/error-handling-and-retries.md) |
| 哪些已实现、哪些已验证 | [兼容性](docs/zh-CN/compatibility.md) |
| 生产环境清单 | [生产接入](docs/zh-CN/production-integration-checklist.md) |
| 首次调用常见问题 | [FAQ](docs/zh-CN/faq.md) |
| AI 工作流 | [智能体用例](docs/zh-CN/ai-agent-use-cases.md) · [提示词配方](docs/zh-CN/prompt-recipes-for-facebook-video-analysis.md) |
| 证据 | [Actor 审计](docs/zh-CN/audit/actor_audit_20261028.md) |

## 开发

```bash
python -m unittest discover -s tests/python -v     # 89 个离线用例
node scripts/run_node_ci_tests.mjs                 # 5 个离线测试文件
(cd examples/go && go vet ./... && go test ./...)  # Go 包测试
(cd examples/java && ./run_tests.sh)               # Java 断言（JDK 17+）
python -m compileall -q examples/python tests/python scripts
python scripts/estimate_cost.py --videos 3 --minutes 8 --tier FREE
```

所有测试都不需要 `APIFY_TOKEN`、`.env` 文件或网络访问。

## 授权

MIT 授权，全文见 [LICENSE](LICENSE)。版权归 APISmith 所有，年份 2026。

简单说：你可以使用、复制、修改、合并、发布、分发、再授权和销售这份代码，商用也可以，只要在所有副本或
主要部分中保留版权声明与本授权声明。软件按“原样”提供，不附带任何形式的担保。

本授权覆盖本仓库的代码与文档，**不覆盖** Apify 上的 Actor `apple_yang/facebook-transcript-scraper-api`
本身——那是独立商业服务，受 Apify [服务条款](https://apify.com/terms)与该 Actor 自身定价约束；无论本仓库
采用何种授权，执行 Actor 都会产生费用。
