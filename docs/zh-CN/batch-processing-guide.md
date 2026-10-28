# 批量处理

[English](../batch-processing-guide.md)

这个 Actor 每次 Run 只接受一个 `videoUrl`。它没有原生批量模式，所以批量是客户端的责任：**一行 = 一个独立
Run**。下文命令均以仓库根目录为当前目录。

由此带来几个必须说清楚的后果：

- 成本随行数线性增长，没有批量折扣，也不会共享转写结果。
- 并发越高，撞上速率限制的机会越多，同时在跑的计费 Run 也越多。
- 行的身份很重要。每条结果都带着 CSV 行号作为 `rowId`。

## CSV 格式

```csv
videoUrl,durationSeconds
https://www.facebook.com/watch/?v=1234567890,600
https://www.facebook.com/reel/987654321/,
https://www.facebook.com/SomePage/videos/5555555555/,43.5
```

- 表头必须包含 `videoUrl` 或 `url`（不区分大小写）。两者都没有的文件会被拒绝。
- `durationSeconds` 可选，只用于执行前的成本估算。
- UTF-8，带不带 BOM 均可。一行一条记录；不支持引号字段内的换行。
- 链接为空的行会被跳过。出现一个非空但非法的链接，会在**任何 Run 之前**整个文件被拒绝。
- 重复链接**不会**去重。两行相同就会创建两个 Run，靠 `rowId` 区分。不想付两次钱，就在上游先去重。

## 先计划，再执行

两个执行器默认都只做计划。计划阶段会校验每一行并打印估算，不读取 token，也不创建 Run。

```bash
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv
```

执行：

```bash
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv --execute
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv --execute
```

常用参数：

| 参数 | 含义 |
| --- | --- |
| `--limit N` | 只处理前 N 行 |
| `--max-concurrency N` | 并发 Run 数（默认 3） |
| `--output PATH` | 结果 JSON 路径；默认与 CSV 同目录 |
| `--tier FREE\|BRONZE\|SILVER\|GOLD\|PLATINUM\|DIAMOND` | 估算所用的套餐档位 |
| `--max-total-charge-usd 0.10` | 单 Run 费用上限 |
| `--require-charge-cap` | 未提供上限时，在任何 Run 之前就失败 |
| `--timeout 900` | 单个 Run 的超时秒数 |

## 输出文件

| 文件 | 内容 |
| --- | --- |
| `facebook-batch-results-<UTC>.json` | 每行状态、Run/Dataset ID、转写文本、分段、原始条目、错误、汇总计数 |
| `python-run-journal.jsonl` 或 `nodejs-run-journal.jsonl` | 同目录下追加写入的阶段记录 |

两个文件的权限都是 `0600`。结果文件名唯一，先前的批次不会被覆盖（必要时追加 `-1`、`-2` 后缀）。

由于各行并发执行，**结果文件**可能等全部行结束后才写入，而 journal 是随进度追加的。两种实现的结果数组都
保持输入顺序。

## 每行状态

每行恰好得到 `success`、`actor_error`、`empty`、`no_transcript`、`unknown`、`transport_error`、
`run_failed`、`creation_unknown` 中的一个。只有 `success` 代表真的产出了转写文本。详见
[错误处理](error-handling-and-retries.md)。

汇总计数包含 `processed` 与 `failed`（即 `processed - success`）。

## 恢复边界

- 每一行的 Run **最多创建一次**。
- Run ID 在创建成功后、开始轮询之前就写入 journal。若之后轮询或读取 Dataset 失败，该行记为
  `transport_error`，Run ID 会出现在结果与 journal 中。
- 创建结果不明确时，该行记为 `creation_unknown`，不重试。
- 批量执行器**不提供**断点续跑。重跑同一份 CSV 会为每一行重新创建 Run，包括之前已经成功的行。为了避免重复
  计费，请先把 CSV 过滤到确实要重提的行。
- 单链接恢复请用 `--resume RUN_ID`，它只发 GET。

## 大文件的成本控制

1. 先跑计划阶段，看清估算。
2. 用 `--limit 5` 小规模执行，检查结果文件。
3. 确认成功率和耗时之后，再提高并发。
4. 每一批都保留 `--max-total-charge-usd`。

对于没有 `durationSeconds` 的行，估算按一分钟的最低计费时长处理，所以不带时长的计划结果只是下限，不是
预测值。
