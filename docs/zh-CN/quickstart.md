# 快速开始

[English](../quickstart.md)

用一个公开的 Facebook 视频链接跑通 Actor，并打印转写文本。执行 Actor 会产生 Apify 费用——大规模任务之前
请先读[成本与限制](cost-and-limits.md)。

下文命令均以仓库根目录为当前目录。

文中的示例都锁定 Build `0.0.18`（Build ID `fZIlpYENof2jYqIJc`），发送 `restartOnError=false`，并可选地为
单次 Run 设置费用上限。这个上限是 Run 的保护性选项，不是最终账单的绝对保证。

请把 `APIFY_TOKEN` 放在 shell 环境或密钥管理服务里。token 只通过 `Authorization: Bearer` 请求头传递，
绝不出现在 URL、源码文件或日志里。

## cURL

需要 `curl` 与 `jq`。流程是：一次创建 `POST`，随后对**同一个** Run 做 `GET` 轮询，最后读取 Dataset。
创建阶段出现错误、超时或响应不明确时，一律不重试。

```bash
: "${APIFY_TOKEN:?请先在环境中设置 APIFY_TOKEN}"
API='https://api.apify.com/v2'
ACTOR='apple_yang~facebook-transcript-scraper-api'
INPUT='{"videoUrl":"https://www.facebook.com/watch/?v=1234567890"}'

created=$(curl --fail --silent --show-error \
  -X POST "$API/acts/$ACTOR/runs?build=0.0.18&restartOnError=false&maxTotalChargeUsd=0.10" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H 'Content-Type: application/json' \
  --data "$INPUT") || { echo 'Run 创建失败或结果不明。请先在 Apify 中核对已有 Run，再决定是否重试。' >&2; exit 1; }

run_id=$(jq -er '.data.id | strings | select(length > 0)' <<<"$created") || { echo '创建响应不明确，请到 Apify 核对。' >&2; exit 1; }
dataset_id=$(jq -er '.data.defaultDatasetId | strings | select(length > 0)' <<<"$created") || { echo '创建响应不明确，请到 Apify 核对。' >&2; exit 1; }
printf 'Run ID: %s\n' "$run_id"

status=''
for _ in $(seq 1 300); do
  run=$(curl --fail --silent --show-error -H "Authorization: Bearer $APIFY_TOKEN" "$API/actor-runs/$run_id") || {
    echo "Run $run_id 轮询失败。请继续对这个 Run 发起 GET，不要另建。" >&2; exit 1; }
  status=$(jq -er '.data.status' <<<"$run")
  case "$status" in SUCCEEDED|FAILED|ABORTED|TIMED-OUT) break ;; esac
  sleep 1
done
[ "$status" = SUCCEEDED ] || { printf 'Run %s 以 %s 结束，不要创建替代 Run。\n' "$run_id" "$status" >&2; exit 1; }

items=$(curl --fail --silent --show-error -H "Authorization: Bearer $APIFY_TOKEN" "$API/datasets/$dataset_id/items?format=json")
jq -er '
  if length == 0 then error("Dataset 为空") else .[0] end
  | if ((.errMsg // "") != "") then error("条目返回了 errMsg")
    elif ((.text // "") | type) != "string" or (.text | length) == 0 then error("没有转写文本")
    else "转写文本：\n\(.text)" end
' <<<"$items"
```

## Python 3.10+

只用标准库，不需要安装任何包。

```bash
export APIFY_TOKEN='your_apify_token_here'
python examples/python/quickstart_single.py 'https://www.facebook.com/watch/?v=1234567890'
```

可复用的调用方式：

```python
from examples.python.client import get_transcript

result = get_transcript('https://www.facebook.com/watch/?v=1234567890')
if result.status == 'success':
    print(result.text)
    print(f'{len(result.segments)} 个分段，时长 {result.duration} 秒')
else:
    print(result.status, result.error)

raw = result.items[0] if result.items else {}
```

`get_transcript()` 只在被调用时才读取 `APIFY_TOKEN`。它还接受 `token=`、`build=`、`timeout=`、
`max_total_charge_usd=`、`require_charge_cap=`、`dataset_limit=`、`run_id=`、`transport=` 与 `journal=`，
供测试或进阶调用方使用。除非你传入 journal，否则它不会创建任何文件。

命令行版本额外提供 journal 记录、`.env` 加载、JSON 输出与断点恢复：

```bash
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890'
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --json --output result.json
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
```

## Node.js 18+

零依赖，使用内置 `fetch`。

```bash
export APIFY_TOKEN='your_apify_token_here'
node examples/nodejs/quickstart-single.mjs 'https://www.facebook.com/watch/?v=1234567890'
```

可复用的调用方式：

```javascript
import { getTranscript } from './examples/nodejs/client.mjs';

const result = await getTranscript('https://www.facebook.com/watch/?v=1234567890');
if (result.status === 'success') {
  console.log(result.text);
  console.log(`${result.segments.length} 个分段，时长 ${result.duration} 秒`);
} else {
  console.log(result.status, result.error);
}
```

## 请求层面发生了什么

| 阶段 | 请求 | 重试规则 |
| --- | --- | --- |
| 创建 | `POST /v2/acts/apple_yang~facebook-transcript-scraper-api/runs` | **绝不重试**。结果不明即记为 `creation_unknown` |
| 轮询 | `GET /v2/actor-runs/{runId}` | 遇 429 / 5xx / 网络错误可重试，最多 4 次 |
| 读取 | `GET /v2/datasets/{datasetId}/items?limit=100&offset=0` | 同样规则；读到空结果时在同一 Dataset 上复核两次 |

一旦创建响应给出了 Run ID，这次 Run 就被固定下来。之后再失败，含义是“恢复这个 Run”，而不是“再开一个”。

## 返回值怎么读

完成后的 Dataset 是一个 JSON 数组。与转写相关的字段是 `text`、`segments`、`errMsg`。`errMsg` 为空是正常的；
非空则代表这条数据在业务层失败，即使 `text` 也有内容。Run 状态 `SUCCEEDED` 但 Dataset 为空，属于 `empty`，
不是成功。

| 状态 | 含义 |
| --- | --- |
| `success` | 存在非空的转写字符串 |
| `actor_error` | 至少一个条目的 `errMsg` 非空 |
| `empty` | Dataset 里没有任何条目 |
| `no_transcript` | `text` 为 null、缺失或空字符串 |
| `unknown` | 字段类型不支持，或无法确认数据完整性 |
| `transport_error` | Run 已存在，但后续读取失败 |
| `run_failed` | Run 以 `FAILED`、`ABORTED` 或 `TIMED-OUT` 结束 |
| `creation_unknown` | 创建 POST 可能已产生 Run，重试前必须先核对 |

退出码与恢复细节见[错误处理](error-handling-and-retries.md)。

## 下一步

- [可接受的链接形态](input-output-fields.md#accepted-url-forms)
- [成本与限制](cost-and-limits.md)
- [批量处理](batch-processing-guide.md)
- [生产环境清单](production-integration-checklist.md)
