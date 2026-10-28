# Use Facebook Transcript Scraper API with Go

Go 1.22+, standard library only. No module downloads, no build tags, no code
generation: `go build ./...` works offline on a clean machine.

[Quick start](../../docs/quickstart.md)

## Files

| File | Purpose |
| --- | --- |
| `transcript/reliable_actor.go` | Staged runner: transport, classification, retry policy, JSONL journal, sanitization |
| `transcript/client.go` | `GetTranscript()` plus result and error types |
| `transcript/url.go` | URL allow-list, canonicalization, Build and charge-cap validation |
| `transcript/cost.go` | Two-event pricing model and the one-minute billing floor |
| `cmd/single-url` | CLI with `.env` loading, `--json`, `--output`, `--resume`, journaling |
| `cmd/batch-csv` | One Run per CSV row; plan-only unless `--execute` |
| `cmd/quickstart` | Minimal CLI, no journal |

The module lives in `examples/go`, so run commands from that directory.

## Setup

```bash
cd examples/go
go build ./...
export APIFY_TOKEN='your_apify_token_here'
go run ./cmd/quickstart 'https://www.facebook.com/watch/?v=1234567890'
```

## Reusable API

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

`Result` fields: `Status`, `Text`, `HasText`, `Segments`, `Items`, `RunID`,
`DatasetID`, `SourceURL`, `CanonicalURL`, `URLForm`, `Error`, `DatasetComplete`,
`Title`, `Nickname`, `Duration`, `HasDuration`. Method `Succeeded()` is true only
for `success`; `ExitCode()` maps the status to the documented process exit code.

Errors: `ConfigurationError`, `ProtocolError` (with `RunID`), `TransportError`,
and `CreationUnknownError`. Business outcomes are returned, never thrown.

Options: `Token`, `ActorID`, `Build`, `Timeout`, `MaxTotalChargeUSD`,
`RequireChargeCap`, `DatasetLimit`, `RunID`, `RowID`, `Transport`, `Journal`,
plus `Sleep` and `MaxAttempts` as test seams.

## CLI

```bash
go run ./cmd/single-url 'https://www.facebook.com/watch/?v=1234567890'
go run ./cmd/single-url 'https://www.facebook.com/reel/1234567890/' --json
go run ./cmd/single-url 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
go run ./cmd/single-url 'https://www.facebook.com/watch/?v=1234567890' \
  --require-charge-cap --max-total-charge-usd 0.10
```

`go run` reports an exit status of 1 for any non-zero program exit. Build the
binary (`go build -o bin/single-url ./cmd/single-url`) when you need the real
codes: `0` success, `4` actor_error, `5` empty, `6` no_transcript, `7` unknown,
`8` transport_error, `9` run_failed, `10` creation_unknown, `2` configuration,
`3` protocol.

The CLI loads `.env` from the working directory, reading only `APIFY_*` keys and
never overriding an existing environment variable. Its journal is
`sample-output/generated/go-run-journal.jsonl`.

## Batch

```bash
go run ./cmd/batch-csv ../../sample-data/facebook-video-urls.csv            # plan only
go run ./cmd/batch-csv ../../sample-data/facebook-video-urls.csv --execute  # one Run per row
go run ./cmd/batch-csv file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

CSV columns: `videoUrl` (or `url`) required, `durationSeconds` optional. Line
numbers become `rowId`. The result file defaults to
`facebook-batch-results-<UTC>.json` beside the CSV; the journal is
`go-run-journal.jsonl` in the same directory. Exit `0` when every row succeeded,
`1` when at least one did not, `2` for a CSV or configuration error.

## Tests

```bash
cd examples/go
go vet ./...
go test ./...
```

All tests use fake transports and temporary journals. No token, no network, no
`.env`.
