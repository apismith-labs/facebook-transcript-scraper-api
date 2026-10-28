# 用 Node.js 调用 Facebook Transcript Scraper API

[English](README.md)

Node.js 18+，使用内置 `fetch`。零依赖、没有 lockfile、没有构建步骤。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `reliable-actor.mjs` | 分阶段执行器：传输、状态判定、重试策略、JSONL journal、脱敏 |
| `client.mjs` | `getTranscript()`，外加链接校验 |
| `single-url.mjs` | 命令行工具：`.env` 加载、`--json`、`--output`、`--resume`、journal |
| `batch-csv.mjs` | CSV 一行一个 Run；不加 `--execute` 时只做计划 |
| `quickstart-single.mjs` | 最小命令行示例，无 journal |
| `cost.mjs` | 价格模型，供批量计划器使用 |

## 准备

```bash
export APIFY_TOKEN='your_apify_token_here'
node examples/nodejs/quickstart-single.mjs 'https://www.facebook.com/watch/?v=1234567890'
```

不需要 `npm install`。把这些文件复制进你的项目时，请保持在同一目录，导入用的是相对路径。

## 可复用的接口

```javascript
import { getTranscript } from './examples/nodejs/client.mjs';

const result = await getTranscript('https://www.facebook.com/watch/?v=1234567890');
if (result.succeeded) {
  console.log(result.text);
  for (const segment of result.segments) console.log(segment.start, segment.text);
} else {
  console.log(result.status, result.error);
}
```

结果字段：`status`、`text`、`segments`、`items`、`runId`、`datasetId`、`sourceUrl`、`canonicalUrl`、
`urlForm`、`error`、`datasetComplete`、`title`、`duration`、`nickname`、`succeeded`。

错误类型：`ConfigurationError`、`ProtocolError`（带 `runId`）、`TransportError`、`CreationUnknownError`。
业务结果以返回值形式给出，不抛异常。

可用参数：`token`、`actorId`、`build`、`timeout`、`maxTotalChargeUsd`、`requireChargeCap`、`datasetLimit`、
`runId`、`rowId`、`transport`、`journal`。

## 命令行

```bash
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890'
node examples/nodejs/single-url.mjs 'https://www.facebook.com/reel/1234567890/' --json
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890' \
  --require-charge-cap --max-total-charge-usd 0.10
```

命令会从当前目录加载 `.env`，只读取 `APIFY_*` 键。journal 位于
`sample-output/generated/nodejs-run-journal.jsonl`。

退出码与 Python 命令行一致：业务状态 `0/4/5/6/7/8/9/10`，配置问题 `2`，协议错误 `3`。

## 批量

```bash
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv --execute
node examples/nodejs/batch-csv.mjs file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

CSV 解析器支持单行内的引号字段、BOM、`videoUrl` 或 `url` 表头，以及可选的 `durationSeconds` 列。不支持
引号字段内嵌换行。

结果文件：与 CSV 同目录的 `facebook-batch-results-<UTC>.json`。journal：同目录下的
`nodejs-run-journal.jsonl`。

## 测试

```bash
node scripts/run_node_ci_tests.mjs   # 在仓库根目录执行
```

5 个测试文件，全部离线，不需要 token。

中文文档：[快速开始](../../docs/zh-CN/quickstart.md) · [批量处理](../../docs/zh-CN/batch-processing-guide.md)。
