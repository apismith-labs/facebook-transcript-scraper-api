# 用 Go 调用 Facebook Transcript Scraper API

Go 1.22+，只用标准库。不下载任何模块，没有构建标签，也没有代码生成：干净机器上离线执行
`go build ./...` 就能通过。

[English](README.md) · [快速开始](../../docs/zh-CN/quickstart.md)

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `transcript/reliable_actor.go` | 分阶段执行器：传输、状态判定、重试策略、JSONL journal、脱敏 |
| `transcript/client.go` | `GetTranscript()`，以及结果与错误类型 |
| `transcript/url.go` | 链接白名单、规范化、Build 与费用上限校验 |
| `transcript/cost.go` | 双事件计费模型与“不足一分钟按一分钟”规则 |
| `cmd/single-url` | 命令行工具：`.env` 加载、`--json`、`--output`、`--resume`、journal |
| `cmd/batch-csv` | CSV 一行一个 Run；不加 `--execute` 时只做计划 |
| `cmd/quickstart` | 最小示例，无 journal |

模块根目录是 `examples/go`，因此命令都在该目录下执行。

## 准备

```bash
cd examples/go
go build ./...
export APIFY_TOKEN='your_apify_token_here'
go run ./cmd/quickstart 'https://www.facebook.com/watch/?v=1234567890'
```

## 可复用的接口

```go
package main

import (
	"context"
	"fmt"

	"github.com/apismith-labs/facebook-transcript-scraper-api/examples/go/transcript"
)

func main() {
	result, err := transcript.GetTranscript(context.Background(),
		"https://www.facebook.com/watch/?v=1234567890", transcript.Options{})
	if err != nil {
		panic(err)
	}
	if result.Succeeded() {
		fmt.Println(result.Text)
		for _, segment := range result.Segments {
			fmt.Println(segment["start"], segment["text"])
		}
		return
	}
	fmt.Println(result.Status, result.Error)
}
```

`Result` 字段：`Status`、`Text`、`HasText`、`Segments`、`Items`、`RunID`、`DatasetID`、`SourceURL`、
`CanonicalURL`、`URLForm`、`Error`、`DatasetComplete`、`Title`、`Nickname`、`Duration`、`HasDuration`。
`Succeeded()` 仅在 `success` 时为真；`ExitCode()` 把状态映射为文档约定的进程退出码。

错误类型：`ConfigurationError`、`ProtocolError`（带 `RunID`）、`TransportError`、`CreationUnknownError`。
业务结果以返回值形式给出，不抛异常。

可用参数：`Token`、`ActorID`、`Build`、`Timeout`、`MaxTotalChargeUSD`、`RequireChargeCap`、`DatasetLimit`、
`RunID`、`RowID`、`Transport`、`Journal`，另有 `Sleep` 与 `MaxAttempts` 作为测试注入点。

## 命令行

```bash
go run ./cmd/single-url 'https://www.facebook.com/watch/?v=1234567890'
go run ./cmd/single-url 'https://www.facebook.com/reel/1234567890/' --json
go run ./cmd/single-url 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
go run ./cmd/single-url 'https://www.facebook.com/watch/?v=1234567890' \
  --require-charge-cap --max-total-charge-usd 0.10
```

注意：`go run` 会把任何非零退出码统一报告为 1。需要真实退出码时请先编译二进制
（`go build -o bin/single-url ./cmd/single-url`）：`0` 成功，`4` actor_error，`5` empty，`6`
no_transcript，`7` unknown，`8` transport_error，`9` run_failed，`10` creation_unknown，`2` 配置问题，
`3` 协议错误。

命令会从工作目录加载 `.env`，只读取 `APIFY_*` 键，且不覆盖已存在的环境变量。journal 位于
`sample-output/generated/go-run-journal.jsonl`。

## 批量

```bash
go run ./cmd/batch-csv ../../sample-data/facebook-video-urls.csv            # 仅计划
go run ./cmd/batch-csv ../../sample-data/facebook-video-urls.csv --execute  # 一行一个 Run
go run ./cmd/batch-csv file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

CSV 列：`videoUrl`（或 `url`）必填，`durationSeconds` 可选。行号会成为 `rowId`。默认结果文件是与 CSV 同
目录的 `facebook-batch-results-<UTC>.json`；journal 为同目录下的 `go-run-journal.jsonl`。全部行成功退出
`0`，有失败退出 `1`，CSV 或配置错误退出 `2`。

## 测试

```bash
cd examples/go
go vet ./...
go test ./...
```

所有测试都用假 transport 与临时 journal，不需要 token、不需要网络，也不需要 `.env`。
