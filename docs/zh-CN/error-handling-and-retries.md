# 错误处理与重试

[English](../error-handling-and-retries.md)

使用这个 Actor 最贵的一个错误，就是重试 Run 创建。一个超时的 `POST` 可能已经产生了计费 Run；再发一次，
就可能变成两个。

## 三个阶段，三条规则

| 阶段 | 请求 | 规则 |
| --- | --- | --- |
| 创建 | `POST /acts/{owner~name}/runs` | **严格一次。** 超时、连接中断、5xx、429 都不重试 |
| 轮询 | `GET /actor-runs/{runId}` | 遇 429、5xx 或网络错误重试；最多 4 次；遵守 `Retry-After` |
| 读取 | `GET /datasets/{datasetId}/items` | 同样的重试规则；读到空结果时在同一 Dataset 上复核两次 |

创建失败分为两类：

- **`creation_unknown`** —— 超时、连接丢失、响应无法解析、5xx 或 429。Run 可能已经存在。停止操作，去
  Apify 的 Run 历史里核对。
- **`transport_error`** —— 明确的拒绝（例如 HTTP 400）。没有创建任何 Run。

一旦拿到了 Run ID，之后所有失败都是“这次 Run 的读取问题”。恢复它，不要替换它。

## 业务状态

| 状态 | 含义 | 是否重试 |
| --- | --- | --- |
| `success` | 存在非空的转写字符串 | 否 |
| `actor_error` | 某条目的 `errMsg` 非空 | 否——是输入本身失败 |
| `empty` | Dataset 没有任何条目 | 否 |
| `no_transcript` | `text` 为 null、缺失或空 | 否——视频可能是静音的 |
| `unknown` | 类型不支持，或无法确认完整性 | 需排查 |
| `transport_error` | Run 已存在，但后续读取失败 | 恢复同一个 Run |
| `run_failed` | Run 以 `FAILED`、`ABORTED`、`TIMED-OUT` 结束 | 查看 Apify 日志 |
| `creation_unknown` | 创建结果不明确 | 先核对，绝不盲重试 |

`actor_error` 永远不算成功，即使 `text` 也有内容。`no_transcript` 也不算传输层意义上的错误：Run 正常完成
了，只是条目里没有可用的语音内容。

## 退出码

| 退出码 | 状态 |
| --- | --- |
| 0 | `success` |
| 4 | `actor_error` |
| 5 | `empty` |
| 6 | `no_transcript` |
| 7 | `unknown` |
| 8 | `transport_error` |
| 9 | `run_failed` |
| 10 | `creation_unknown` |

命令行还有两个附加码：`2` 表示在任何请求之前就发现的配置问题（链接非法、缺少 token、Build 或费用上限
不合法），`3` 表示协议错误（响应畸形、Build 不匹配）。

批量执行器只有在全部行成功时才退出 `0`；有任意一行失败退出 `1`；CSV 或配置错误在执行前退出 `2`。

## Build 校验

客户端请求 `build=0.0.18`，并从创建响应或后续的 `GET /actor-runs/{id}` 中同时核对 `buildNumber` 与
`buildId`（`fZIlpYENof2jYqIJc`）。不匹配会抛协议错误，并且**不会**再创建新的 Run。如果 Apify 发布了新的
build，请重跑审计，然后有意识地更新锁定的常量。

## 恢复语义

`--resume RUN_ID` 执行的是只读恢复：

1. 读取本地 journal 中该 Run 的记录（Python 与 Node 都支持）。
2. 校验 journal 中的 Actor ID 与源链接和本次调用一致。
3. 轮询已存在的 Run，读取它的 Dataset。

全程不发 `POST`。journal 缺失时 Python 命令行会拒绝执行；Node 命令行在 journal 文件存在但没有该记录时同样
拒绝。对于在工具之外创建的 Run，仍可用 `python scripts/check_apify_run.py RUN_ID` 做只读检查。

## 哪些不会替你重试

- Run 创建。
- Actor 层面的失败（`actor_error`、`run_failed`）。
- 批量中失败的行。重跑 CSV 会给每一行重新创建 Run，那不是断点续跑。请保留结果 JSON 与 journal，只重提
  你愿意再付一次钱的行。
- 超过配置上限的 Dataset 分页。触及分页上限时，客户端会报 `unknown`，而不是假装数据完整。

## 日志与密钥

Token 只通过 `Authorization` 请求头传递。写入 journal 或结果文件之前，错误字符串会做脱敏（`Bearer …`、
`token=…`、`authorization: …`、cookie/password 等模式）。journal 以 `0600` 权限创建。请勿把原始请求头或
响应体写进你自己的日志。
