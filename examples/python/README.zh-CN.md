# 用 Python 调用 Facebook Transcript Scraper API

[English](README.md)

Python 3.10+，只用标准库。不需要 Apify SDK，不需要 `requests`，也不依赖 `.env`。创建 Run、轮询、读取
Dataset 被拆成三个独立的 REST 调用，因为每个阶段的重试规则不同。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `reliable_actor.py` | 分阶段执行器：传输、状态判定、重试策略、JSONL journal、脱敏 |
| `client.py` | `get_transcript()`，外加链接校验与 `TranscriptResult` 类型 |
| `single_url.py` | 命令行工具：`.env` 加载、`--json`、`--output`、`--resume`、journal |
| `batch_csv.py` | CSV 一行一个 Run；不加 `--execute` 时只做计划 |
| `quickstart_single.py` | 最小命令行示例，无 journal、无 `.env` |
| `cost.py` | 价格模型，供 `scripts/estimate_cost.py` 与批量计划器使用 |

## 准备

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r examples/python/requirements.txt   # 没有包，只是让这一步可复现
export APIFY_TOKEN='your_apify_token_here'
```

## 可复用的接口

```python
from examples.python.client import get_transcript

result = get_transcript('https://www.facebook.com/watch/?v=1234567890')
if result.succeeded:
    print(result.text)
    for segment in result.segments:
        print(segment['start'], segment['text'])
else:
    print(result.status, result.error)
```

`TranscriptResult` 字段：`status`、`text`、`segments`、`items`、`run_id`、`dataset_id`、`source_url`、
`canonical_url`、`url_form`、`error`、`dataset_complete`、`title`、`duration`、`nickname`，以及
`succeeded` / `item` 两个属性。

配置问题抛 `ConfigurationError`；响应畸形抛 `ProtocolError`（带 `run_id`）；读取失败抛
`TranscriptTransportError`；创建结果不明确抛 `CreationUnknownError`。业务结果（`actor_error`、`empty`、
`no_transcript`、`run_failed`）以状态形式返回，不抛异常。

如果你想要单文件夹的集成方式，把 `client.py` 与 `reliable_actor.py` 一起复制进项目即可。这个导入不会读取
凭据，也不会创建文件。

可用参数：

```python
get_transcript(
    url,
    token=None,                 # 覆盖 APIFY_TOKEN
    build='0.0.18',
    timeout=900,
    max_total_charge_usd='0.10',
    require_charge_cap=False,
    dataset_limit=100,
    run_id=None,                # 只读恢复
    transport=None,             # 测试用的注入点
    journal=None,               # 默认仅内存
)
```

## 命令行

```bash
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890'
python examples/python/single_url.py 'https://www.facebook.com/reel/1234567890/' --json
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --require-charge-cap --max-total-charge-usd 0.10
```

命令会从当前目录加载 `.env`（如果存在），只读取 `APIFY_*` 键，且不会覆盖已存在的环境变量。journal 位于
`sample-output/generated/python-run-journal.jsonl`。

退出码：`0` 成功，`4` actor_error，`5` empty，`6` no_transcript，`7` unknown，`8` transport_error，
`9` run_failed，`10` creation_unknown，`2` 配置问题，`3` 协议错误。

## 批量

```bash
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv            # 仅计划
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv --execute  # 一行一个 Run
python examples/python/batch_csv.py file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

CSV 列：`videoUrl`（或 `url`）必填，`durationSeconds` 可选。行号会成为 `rowId`。默认结果文件是与 CSV 同
目录的 `facebook-batch-results-<UTC>.json`，journal 为同目录的 `python-run-journal.jsonl`。

## 测试

```bash
python -m unittest discover -s tests/python -v
```

所有测试都使用合成 fixture 与假 transport，不需要 token，也不需要网络。

中文文档：[快速开始](../../docs/zh-CN/quickstart.md) · [错误处理](../../docs/zh-CN/error-handling-and-retries.md)。
