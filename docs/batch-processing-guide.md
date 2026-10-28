# Batch processing

This Actor accepts one `videoUrl` per Run. There is no native bulk mode, so batching is a client
responsibility: **one row = one independent Run**.

That has consequences worth stating plainly:

- Cost scales linearly with rows; there is no bulk discount and no shared transcription.
- Concurrency increases rate-limit exposure and simultaneous billable Runs.
- Row identity matters. Every result carries the CSV line number as `rowId`.

## CSV format

```csv
videoUrl,durationSeconds
https://www.facebook.com/watch/?v=1234567890,600
https://www.facebook.com/reel/987654321/,
https://www.facebook.com/SomePage/videos/5555555555/,43.5
```

- Header must contain `videoUrl` or `url` (case-insensitive). A file without either is rejected.
- `durationSeconds` is optional and used only for the pre-run cost estimate.
- UTF-8 with or without BOM. One record per line; embedded newlines inside quoted fields are not
  supported.
- Blank URL rows are skipped. A non-empty invalid URL rejects the whole file **before** any Run.
- Duplicate URLs are **not** deduplicated. Two identical rows create two Runs; `rowId` keeps them
  apart. Remove duplicates upstream if you do not want to pay twice.

## Plan first, then execute

Both runners are plan-only by default. The plan phase validates every row and prints an estimate;
it reads no token and creates no Run.

```bash
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv
```

Execute:

```bash
python examples/python/batch_csv.py sample-data/facebook-video-urls.csv --execute
node examples/nodejs/batch-csv.mjs sample-data/facebook-video-urls.csv --execute
```

Useful flags:

| Flag | Meaning |
| --- | --- |
| `--limit N` | Process only the first N rows |
| `--max-concurrency N` | Concurrent Runs (default 3) |
| `--output PATH` | Result JSON path; default is beside the CSV |
| `--tier FREE\|BRONZE\|SILVER\|GOLD\|PLATINUM\|DIAMOND` | Tier used in the estimate |
| `--max-total-charge-usd 0.10` | Per-Run cap |
| `--require-charge-cap` | Fail before any Run when no cap is provided |
| `--timeout 900` | Per-Run deadline in seconds |

## Output files

| File | Contents |
| --- | --- |
| `facebook-batch-results-<UTC>.json` | Per-row status, Run/Dataset IDs, transcript, segments, raw items, error, aggregate counts |
| `python-run-journal.jsonl` or `nodejs-run-journal.jsonl` | Append-only stage records for the same directory |

Both files are created with mode `0600`. Result filenames are unique; an earlier batch is never
overwritten (`-1`, `-2`, … suffixes if needed).

Because rows run concurrently, the **result file** may be written after all rows finish while the
journal is appended as work progresses. Result arrays preserve input order in both implementations.

## Statuses per row

Every row gets exactly one of `success`, `actor_error`, `empty`, `no_transcript`, `unknown`,
`transport_error`, `run_failed`, or `creation_unknown`. Only `success` means a transcript was
produced. See [error handling](error-handling-and-retries.md).

Aggregate counts include `processed` and `failed` (`processed - success`).

## Recovery boundaries

- A Run is created **at most once per row**.
- The Run ID is journaled immediately after creation, before polling. If polling or the Dataset
  read fails afterwards, the row is `transport_error` and the Run ID is in the result and journal.
- An ambiguous create marks the row `creation_unknown` and does not retry.
- Batch runners do **not** implement checkpoint resume. Running the CSV again starts a new Run for
  each row, including rows that already succeeded. To avoid double billing, filter the CSV down to
  the rows you actually want to resubmit.
- For single-URL recovery, use `--resume RUN_ID`, which is GET-only.

## Cost control for large files

1. Run the plan phase and read the estimate.
2. Execute `--limit 5` first and inspect the result file.
3. Raise concurrency only after confirming success rate and latency.
4. Keep `--max-total-charge-usd` set for every batch.

The estimate assumes the one-minute billing floor for rows without `durationSeconds`, so a plan
without durations is a lower bound, not a forecast.
