# Quick start

Run one public Facebook video URL through the Actor and print its transcript. Running the Actor may
incur Apify charges — read [cost and limits](cost-and-limits.md) before a large job.

The examples pin Build `0.0.18` (Build ID `fZIlpYENof2jYqIJc`), send `restartOnError=false`, and
optionally request a per-Run charge cap. A requested cap is a protective Run option, not an
absolute final-bill guarantee.

Set `APIFY_TOKEN` in your shell environment or secret manager. The token travels only in an
`Authorization: Bearer` header — never in a URL, a source file, or a log line.

## cURL

Requires `curl` and `jq`. One create `POST`, then `GET` polling of the **same** Run, then a Dataset
read. A create error, timeout, or ambiguous response is never retried.

```bash
: "${APIFY_TOKEN:?Set APIFY_TOKEN in your environment first}"
API='https://api.apify.com/v2'
ACTOR='apple_yang~facebook-transcript-scraper-api'
INPUT='{"videoUrl":"https://www.facebook.com/watch/?v=1234567890"}'

created=$(curl --fail --silent --show-error \
  -X POST "$API/acts/$ACTOR/runs?build=0.0.18&restartOnError=false&maxTotalChargeUsd=0.10" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H 'Content-Type: application/json' \
  --data "$INPUT") || { echo 'Run creation failed or is uncertain. Reconcile the existing Run in Apify before retrying.' >&2; exit 1; }

run_id=$(jq -er '.data.id | strings | select(length > 0)' <<<"$created") || { echo 'Ambiguous create response; reconcile in Apify.' >&2; exit 1; }
dataset_id=$(jq -er '.data.defaultDatasetId | strings | select(length > 0)' <<<"$created") || { echo 'Ambiguous create response; reconcile in Apify.' >&2; exit 1; }
printf 'Run ID: %s\n' "$run_id"

status=''
for _ in $(seq 1 300); do
  run=$(curl --fail --silent --show-error -H "Authorization: Bearer $APIFY_TOKEN" "$API/actor-runs/$run_id") || {
    echo "Run $run_id could not be polled. Continue with GET for this same Run; do not create another." >&2; exit 1; }
  status=$(jq -er '.data.status' <<<"$run")
  case "$status" in SUCCEEDED|FAILED|ABORTED|TIMED-OUT) break ;; esac
  sleep 1
done
[ "$status" = SUCCEEDED ] || { printf 'Run %s ended with %s; do not create a replacement Run.\n' "$run_id" "$status" >&2; exit 1; }

items=$(curl --fail --silent --show-error -H "Authorization: Bearer $APIFY_TOKEN" "$API/datasets/$dataset_id/items?format=json")
jq -er '
  if length == 0 then error("Dataset is empty") else .[0] end
  | if ((.errMsg // "") != "") then error("Actor item reported errMsg")
    elif ((.text // "") | type) != "string" or (.text | length) == 0 then error("No transcript text")
    else "Transcript:\n\(.text)" end
' <<<"$items"
```

## Python 3.10+

Standard library only, no packages to install.

```bash
export APIFY_TOKEN='your_apify_token_here'
python examples/python/quickstart_single.py 'https://www.facebook.com/watch/?v=1234567890'
```

The reusable interface:

```python
from examples.python.client import get_transcript

result = get_transcript('https://www.facebook.com/watch/?v=1234567890')
if result.status == 'success':
    print(result.text)
    print(f'{len(result.segments)} segments, {result.duration}s')
else:
    print(result.status, result.error)

raw = result.items[0] if result.items else {}
```

`get_transcript()` reads `APIFY_TOKEN` only when called. It accepts `token=`, `build=`,
`timeout=`, `max_total_charge_usd=`, `require_charge_cap=`, `dataset_limit=`, `run_id=`,
`transport=`, and `journal=` for tests or advanced callers. It creates no files unless you pass a
journal.

The CLI variant adds journaling, `.env` loading, JSON output, and resume:

`APIFY_SKIP_DOTENV=1` disables `.env` loading in every CLI (Python, Node.js, Go, Java). Use it in
tests and one-off scripts: the offline suites and CI set it, so a local `.env` can never turn a test
into a billable Run.

```bash
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890'
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --json --output result.json
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
```

## Node.js 18+

No dependencies; uses the built-in `fetch`.

```bash
export APIFY_TOKEN='your_apify_token_here'
node examples/nodejs/quickstart-single.mjs 'https://www.facebook.com/watch/?v=1234567890'
```

Reusable interface:

```javascript
import { getTranscript } from './examples/nodejs/client.mjs';

const result = await getTranscript('https://www.facebook.com/watch/?v=1234567890');
if (result.status === 'success') {
  console.log(result.text);
  console.log(`${result.segments.length} segments, ${result.duration}s`);
} else {
  console.log(result.status, result.error);
}
```

## What happens on the wire

| Stage | Request | Retry rule |
| --- | --- | --- |
| Create | `POST /v2/acts/apple_yang~facebook-transcript-scraper-api/runs` | **Never retried.** Ambiguity → `creation_unknown` |
| Poll | `GET /v2/actor-runs/{runId}` | Retried on 429/5xx/network, up to 4 attempts |
| Read | `GET /v2/datasets/{datasetId}/items?limit=100&offset=0` | Same retry rule; empty reads rechecked twice on the same Dataset |

The referenced Run is fixed as soon as the create response yields an ID. A later failure means
"resume that Run", never "start another one".

## What the response means

A completed Dataset is a JSON array of items. Transcript fields are `text`, `segments`, and
`errMsg`. An empty `errMsg` is normal; a non-empty one is an item-level failure even when `text` is
also present. A `SUCCEEDED` Run with an empty Dataset is `empty`, not success.

| Status | Meaning |
| --- | --- |
| `success` | A non-empty transcript string exists |
| `actor_error` | At least one item has a non-empty `errMsg` |
| `empty` | The Dataset has no items |
| `no_transcript` | `text` is null, missing, or empty |
| `unknown` | Unsupported field type, or completeness could not be established |
| `transport_error` | Retrieval failed after the Run existed |
| `run_failed` | The Run ended `FAILED`, `ABORTED`, or `TIMED-OUT` |
| `creation_unknown` | The create POST may have produced a Run; reconcile before retrying |

Exit codes and recovery details: [error handling](error-handling-and-retries.md).

## Next steps

- [Accepted URL forms](input-output-fields.md#accepted-url-forms)
- [Cost and limits](cost-and-limits.md)
- [Batch processing](batch-processing-guide.md)
- [Production checklist](production-integration-checklist.md)
