# Use Facebook Transcript Scraper API with Python

Python 3.10+ using only the standard library. No Apify SDK, no `requests`, no `.env` dependency.
Run creation, polling, and Dataset reads are separate REST calls because each stage has a different
retry rule.

## Files

| File | Purpose |
| --- | --- |
| `reliable_actor.py` | Staged runner: transport, classification, retry policy, JSONL journal, sanitization |
| `client.py` | `get_transcript()` plus URL validation and the `TranscriptResult` type |
| `single_url.py` | CLI with `.env` loading, `--json`, `--output`, `--resume`, journaling |
| `batch_csv.py` | One Run per CSV row; plan-only unless `--execute` |
| `quickstart_single.py` | Minimal CLI, no journal, no `.env` |
| `cost.py` | Pricing model used by `scripts/estimate_cost.py` and the batch planner |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r examples/python/requirements.txt   # no packages; keeps the step reproducible
export APIFY_TOKEN='your_apify_token_here'
```

## Reusable API

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

`TranscriptResult` fields: `status`, `text`, `segments`, `items`, `run_id`, `dataset_id`,
`source_url`, `canonical_url`, `url_form`, `error`, `dataset_complete`, `title`, `duration`,
`nickname`, and the `succeeded` / `item` properties.

Configuration problems raise `ConfigurationError`; malformed responses raise `ProtocolError`
(with `run_id`); retrieval failures raise `TranscriptTransportError`; an ambiguous create raises
`CreationUnknownError`. Business outcomes (`actor_error`, `empty`, `no_transcript`, `run_failed`)
are returned as statuses, not exceptions.

Copy `client.py` and `reliable_actor.py` together into your project if you prefer a single-folder
integration. The import does not read credentials or create files.

Options:

```python
get_transcript(
    url,
    token=None,                 # overrides APIFY_TOKEN
    build='0.0.18',
    timeout=900,
    max_total_charge_usd='0.10',
    require_charge_cap=False,
    dataset_limit=100,
    run_id=None,                # GET-only resume
    transport=None,             # injection seam for tests
    journal=None,               # in-memory by default
)
```

## CLI

```bash
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890'
python examples/python/single_url.py 'https://www.facebook.com/reel/1234567890/' --json
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
python examples/python/single_url.py 'https://www.facebook.com/watch/?v=1234567890' --require-charge-cap --max-total-charge-usd 0.10
```

The CLI loads `.env` from the current directory if present, reading only `APIFY_*` keys and never
overriding an existing environment variable. Its journal is
`sample-output/generated/python-run-journal.jsonl`.

Exit codes: `0` success, `4` actor_error, `5` empty, `6` no_transcript, `7` unknown, `8`
transport_error, `9` run_failed, `10` creation_unknown, `2` configuration, `3` protocol.

## Batch

```bash
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv            # plan only
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv --execute  # one Run per row
python examples/python/batch_csv.py file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

CSV columns: `videoUrl` (or `url`) required, `durationSeconds` optional. Row line numbers become
`rowId`. The default result file is `facebook-batch-results-<UTC>.json` beside the CSV; the journal
is `python-run-journal.jsonl` in the same directory.

## Tests

```bash
python -m unittest discover -s tests/python -v
```

All tests use synthetic fixtures and a fake transport. No token or network is required.
