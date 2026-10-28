# Use Facebook Transcript Scraper API with cURL

[简体中文](README.zh-CN.md)

One script, no SDK: create a Run, poll the same Run, read its Dataset.

## Requirements

`bash`, `curl`, `jq`.

## Run

```bash
export APIFY_TOKEN='your_apify_token_here'
chmod +x examples/curl/single-url-sync.sh
./examples/curl/single-url-sync.sh 'https://www.facebook.com/watch/?v=1234567890'
```

Optional per-Run cap:

```bash
export APIFY_MAX_TOTAL_CHARGE_USD=0.10
```

## What it prints

```
Run ID: <id>
Status: success
Segments: 42
Transcript:
<text>
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Transcript printed |
| 2 | Missing URL argument |
| 6 | Dataset empty, `errMsg` set, or no text |
| 8 | Create or retrieval failure |
| 9 | Run ended `FAILED`, `ABORTED`, or `TIMED-OUT` |
| 10 | Create response had no Run ID |

## Rules the script enforces

- Exactly one create `POST`; no retry on ambiguity.
- Polling uses `GET` on the returned Run only.
- Build pinned to `0.0.18`, `restartOnError=false`.
- Token only in the `Authorization` header.

For batch work use the Python or Node.js CSV runner; the cURL script handles one URL only.

See [quick start](../../docs/quickstart.md) for the Python and Node.js equivalents.
