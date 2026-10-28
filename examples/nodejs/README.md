# Use Facebook Transcript Scraper API with Node.js

[简体中文](README.zh-CN.md)

Node.js 18+ using built-in `fetch`. No dependencies, no lockfile, no build step.

## Files

| File | Purpose |
| --- | --- |
| `reliable-actor.mjs` | Staged runner: transport, classification, retry policy, JSONL journal, sanitization |
| `client.mjs` | `getTranscript()` plus URL validation |
| `single-url.mjs` | CLI with `.env` loading, `--json`, `--output`, `--resume`, journaling |
| `batch-csv.mjs` | One Run per CSV row; plan-only unless `--execute` |
| `quickstart-single.mjs` | Minimal CLI, no journal |
| `cost.mjs` | Pricing model used by the batch planner |

## Setup

```bash
export APIFY_TOKEN='your_apify_token_here'
node examples/nodejs/quickstart-single.mjs 'https://www.facebook.com/watch/?v=1234567890'
```

`npm install` is not required. If you copy these files into a project, keep them together; imports
are relative.

## Reusable API

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

Result fields: `status`, `text`, `segments`, `items`, `runId`, `datasetId`, `sourceUrl`,
`canonicalUrl`, `urlForm`, `error`, `datasetComplete`, `title`, `duration`, `nickname`,
`succeeded`.

Errors: `ConfigurationError`, `ProtocolError` (with `runId`), `TransportError`, and
`CreationUnknownError`. Business outcomes are returned, not thrown.

Options: `token`, `actorId`, `build`, `timeout`, `maxTotalChargeUsd`, `requireChargeCap`,
`datasetLimit`, `runId`, `rowId`, `transport`, `journal`.

## CLI

```bash
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890'
node examples/nodejs/single-url.mjs 'https://www.facebook.com/reel/1234567890/' --json
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
node examples/nodejs/single-url.mjs 'https://www.facebook.com/watch/?v=1234567890' \
  --require-charge-cap --max-total-charge-usd 0.10
```

The CLI loads `.env` from the current directory, reading only `APIFY_*` keys. Its journal is
`sample-output/generated/nodejs-run-journal.jsonl`.

Exit codes match the Python CLI: `0/4/5/6/7/8/9/10` for business statuses, `2` configuration,
`3` protocol.

## Batch

```bash
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv --execute
node examples/nodejs/batch-csv.mjs file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

The CSV parser supports quoted fields on a single line, a BOM, `videoUrl` or `url` headers, and an
optional `durationSeconds` column. Embedded newlines inside quoted fields are not supported.

Result file: `facebook-batch-results-<UTC>.json` beside the CSV. Journal:
`nodejs-run-journal.jsonl` in the same directory.

## Tests

```bash
node scripts/run_node_ci_tests.mjs   # from the repository root
```

Five test files, all offline, no token required.
