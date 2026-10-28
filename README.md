[![Apify runs](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.apify.com%2Fv2%2Facts%2Fapple_yang~facebook-transcript-scraper-api&query=%24.data.stats.totalRuns&label=Apify%20runs&color=brightgreen)](https://apify.com/apple_yang/facebook-transcript-scraper-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# Facebook Transcript Scraper API

Use the Apify Actor `apple_yang/facebook-transcript-scraper-api` as a Facebook transcript API:
submit one public Facebook video URL and get transcript text, timestamped segments, and video
metadata as structured JSON.

This repository is the integration kit around that Actor — a reusable client, CLIs, a CSV batch
runner, cost estimation, an audited contract, and offline tests. It is **not** the Actor source and
it does not host a service.

**[Try on Apify](https://apify.com/apple_yang/facebook-transcript-scraper-api)** ·
**[Pricing](https://apify.com/apple_yang/facebook-transcript-scraper-api/pricing)** ·
**[Quick start](docs/quickstart.md)**

## What this Actor does — and does not

| | |
| --- | --- |
| Input | Exactly **one** field: `videoUrl` |
| Modes | Single video only. There is **no** `bulkUrls` and **no** profile mode |
| Output | Dataset items with `text`, `segments`, media URLs, engagement counts, `errMsg` |
| Batch | Client-side only: this repository creates **one Run per CSV row** |
| Login | None. Public videos only; no `sessionid`, no cookies |
| Free plan | Videos up to **5 minutes** |
| Billing | Per dataset item **plus** per minute of transcription — see [cost](docs/cost-and-limits.md) |

A common misreading of the Store headline: "$1.00 / 1,000 results" covers only the dataset-item
event. Transcription is charged separately, so a 10-minute video costs roughly **$0.046** on the
free tier, not $0.001.

## Example output

Illustrative shape only — this is not a recorded response.

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
  "text": "<transcript text, when available>",
  "segments": [{ "start": 0, "end": 0.68, "text": " Hello, Dr." }],
  "errMsg": "",
  "timestamp": "2026-10-28T00:00:00.000Z"
}
```

`text` and `segments` depend on the returned item. A `SUCCEEDED` Run does not guarantee a usable
transcript: check `errMsg` and the item fields. `likesCount` and `shareCount` are declared by the
Actor's Dataset schema but are missing from its README; treat them as optional.

## Use it from code

| Language | Guide | Status |
| --- | --- | --- |
| Python 3.10+ | [examples/python](examples/python/README.md) | Implemented, offline-tested |
| Node.js 18+ | [examples/nodejs](examples/nodejs/README.md) | Implemented, offline-tested |
| Go 1.22+ | [examples/go](examples/go/README.md) | Implemented, offline-tested |
| Java 17+ | [examples/java](examples/java/README.md) | Implemented, offline-tested |
| cURL | [examples/curl](examples/curl/README.md) | Implemented |
| Rust | — | Not implemented (see [compatibility](docs/compatibility.md)) |

Python stdlib only:

```bash
export APIFY_TOKEN='your_apify_token_here'
export APIFY_MAX_TOTAL_CHARGE_USD=0.10
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890'
```

Node 18+, no dependencies:

```bash
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890'
```

Each command creates one potentially billable Run. The clients pin Build `0.0.18`, verify its Build
ID, send `restartOnError=false`, and never retry Run creation.

## Batch processing

```bash
# Plan only: validates the CSV and prints a cost estimate. No Run, no token read.
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv

# Execute: one Run per non-empty row, at most 3 in flight.
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv --execute
```

Node equivalent: `node examples/nodejs/batch-csv.mjs <file.csv> [--execute]`.

Every row keeps its CSV line number as `rowId`, so duplicate URLs stay traceable. Failures do not
stop other rows. Results are written to a unique JSON file; the append-only journal records each
Run ID before polling, so a failed read can be resumed without creating a second Run. See
[batch processing](docs/batch-processing-guide.md).

## Use with AI agents and MCP

The Actor is reachable through Apify MCP. This repository documents the setup; it does not host an
MCP server.

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

Guides: [Apify MCP](docs/use-with-apify-mcp.md) · [ChatGPT](docs/use-with-chatgpt-mcp.md) ·
[Claude](docs/use-with-claude-mcp.md) · [Gemini CLI](docs/use-with-gemini-cli-mcp.md) ·
[Cursor / VS Code](docs/use-with-cursor-vscode-mcp.md).

## Why this repository exists

- One documented, pinned contract instead of guessing at fields; see the
  [audit](docs/audit/actor_audit_20261028.md) and
  [contract JSON](docs/audit/contracts/facebook-transcript-scraper-api-0.0.18.json).
- Conservative URL validation for the Facebook forms that actually appear in the wild, with
  tracking parameters stripped before the URL reaches the Actor.
- Honest statuses: `actor_error` is not counted as success, `no_transcript` is distinct from
  `empty`, and an ambiguous create is never retried.
- Cost awareness built in, because the Store headline omits the transcription event.
- Offline test suite: no token, no network, no `.env` required.

## Important limitations

- Public videos only. Private, friends-only, deleted, or region-locked videos may fail.
- Transcription is audio-only; on-screen text is not extracted.
- Free plans are limited to videos of 5 minutes or less.
- `fb.watch` short links are accepted by the clients but remain unverified against the Actor;
  `/share/r/<code>/`, `/watch/?v=`, `/<page>/videos/<id>/`, and `/reel/<id>/` were all confirmed in
  the recorded live Runs.
- `/video.php?v=` and bare `/videos/<id>/` are accepted by the validators but do not resolve at
  Facebook for the IDs tested; prefer `/watch/?v=` or the page-scoped form.
- A completed Run with a non-empty `errMsg` is a failure for that item, but `errMsg: 'no audio url
  found'` is also what a transient Facebook-side failure looks like — one manual retry on a new Run
  is reasonable for a URL shape that already worked.
- This repository does not summarize, translate, or analyze transcripts; feed them to your own
  downstream model.

## Documentation

| Topic | Guide |
| --- | --- |
| First Run and setup | [Quick start](docs/quickstart.md) |
| Fields and accepted URL forms | [Input and output fields](docs/input-output-fields.md) |
| Real cost of a Run | [Cost and limits](docs/cost-and-limits.md) |
| CSV batches and recovery | [Batch processing](docs/batch-processing-guide.md) |
| Statuses, exit codes, retry rules | [Error handling and retries](docs/error-handling-and-retries.md) |
| What is implemented vs verified | [Compatibility](docs/compatibility.md) |
| Production checklist | [Production integration](docs/production-integration-checklist.md) |
| First-call questions | [FAQ](docs/faq.md) |
| AI workflows | [Agent use cases](docs/ai-agent-use-cases.md) · [Prompt recipes](docs/prompt-recipes-for-facebook-video-analysis.md) |
| Evidence | [Actor audit](docs/audit/actor_audit_20261028.md) · [Live run record](docs/audit/live_run_20261028.md) |

## Development

```bash
python -m unittest discover -s tests/python -v     # 89 offline tests
node scripts/run_node_ci_tests.mjs                 # 5 offline test files
(cd examples/go && go vet ./... && go test ./...)  # Go package tests
(cd examples/java && ./run_tests.sh)               # Java assertions (JDK 17+)
python -m compileall -q examples/python tests/python scripts
python scripts/estimate_cost.py --videos 3 --minutes 8 --tier FREE
```

No test requires `APIFY_TOKEN`, a `.env` file, or network access. The suites and CI set
`APIFY_SKIP_DOTENV=1`, so a local `.env` cannot turn a test into a billable Run.

## License

MIT — see [LICENSE](LICENSE) for the full text. Copyright (c) 2026 APISmith.

In short: you may use, copy, modify, merge, publish, distribute, sublicense, and sell copies of
this code, including commercially, as long as the copyright notice and this permission notice are
kept in all copies or substantial portions. The software is provided "as is", without warranty of
any kind.

This license covers the code and documentation in this repository. It does **not** cover the Apify
Actor `apple_yang/facebook-transcript-scraper-api` itself, which is a separate commercial service
governed by Apify's [terms](https://apify.com/terms) and the Actor's own pricing — running it
always costs money regardless of this license.
