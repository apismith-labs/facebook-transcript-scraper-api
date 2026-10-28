# Error handling and retries

[简体中文](zh-CN/error-handling-and-retries.md)

The single most expensive mistake with this Actor is retrying Run creation. A timed-out `POST` may
already have produced a billable Run; sending it again can produce two.

## Three stages, three rules

| Stage | Request | Rule |
| --- | --- | --- |
| Create | `POST /acts/{owner~name}/runs` | **Exactly once.** Never retried on timeout, dropped connection, 5xx, or 429 |
| Poll | `GET /actor-runs/{runId}` | Retried on 429, 5xx, or network error; up to 4 attempts; honours `Retry-After` |
| Read | `GET /datasets/{datasetId}/items` | Same retry rule; an empty read is rechecked twice on the same Dataset |

A create failure is classified as:

- **`creation_unknown`** — timeout, connection loss, unparsable response, 5xx, or 429. The Run may
  exist. Stop and reconcile against your Apify run history.
- **`transport_error`** — a definite rejection (for example HTTP 400). No Run was created.

After a Run ID exists, every failure is a retrieval problem attached to that Run. Resume it; do not
replace it.

## Business statuses

| Status | Meaning | Retry? |
| --- | --- | --- |
| `success` | A non-empty transcript string exists | No |
| `actor_error` | An item has a non-empty `errMsg` | No — the input failed |
| `empty` | The Dataset has no items | No |
| `no_transcript` | `text` is null, missing, or empty | No — the video may be silent |
| `unknown` | Unsupported type or unverifiable completeness | Investigate |
| `transport_error` | Retrieval failed after the Run existed | Resume the same Run |
| `run_failed` | Run ended `FAILED`, `ABORTED`, or `TIMED-OUT` | Inspect Apify logs |
| `creation_unknown` | Create outcome is ambiguous | Reconcile; never blind-retry |

`actor_error` is never a success, even when `text` is also present. `no_transcript` is not an error
in the transport sense: the Run worked, the item carries no usable speech.

## Exit codes

| Code | Status |
| --- | --- |
| 0 | `success` |
| 4 | `actor_error` |
| 5 | `empty` |
| 6 | `no_transcript` |
| 7 | `unknown` |
| 8 | `transport_error` |
| 9 | `run_failed` |
| 10 | `creation_unknown` |

Additional CLI codes: `2` for configuration problems detected before any request (bad URL, missing
token, invalid Build or cap) and `3` for protocol errors (malformed response, Build mismatch).

Batch runners exit `0` only when every row succeeded, `1` when at least one row did not, and `2`
for a CSV or configuration error before execution.

## Build verification

The clients request `build=0.0.18` and verify both `buildNumber` and `buildId`
(`fZIlpYENof2jYqIJc`) from the create response or a subsequent `GET /actor-runs/{id}`. A mismatch
raises a protocol error and **does not** create another Run. If Apify rolls a new build, re-run the
audit and update the pinned constants deliberately.

## Resume semantics

`--resume RUN_ID` performs GET-only recovery:

1. Read the local journal record for that Run (Python and Node).
2. Verify the journal's Actor ID and source URL match the current invocation.
3. Poll the existing Run; read its Dataset.

No `POST` is issued. If the journal is missing, the Python CLI refuses; the Node CLI also refuses
when a journal file exists but has no such record. A Run created outside these tools can still be
inspected read-only with `python scripts/check_apify_run.py RUN_ID`.

## What is not retried for you

- Run creation.
- Actor-level failures (`actor_error`, `run_failed`).
- Batch rows that failed. Re-running the CSV creates new Runs for every row; it is not a checkpoint
  resume. Keep the result JSON and journal, and resubmit only the rows you intend to pay for again.
- Dataset pagination beyond the configured limit. The client reports `unknown` when the page limit
  is reached rather than pretending the Dataset was complete.

## Logging and secrets

Tokens travel only in the `Authorization` header. Error strings are redacted (`Bearer …`,
`token=…`, `authorization: …`, cookie/password patterns) before being written to a journal or a
result file. Journals are created with mode `0600`. Do not add raw request headers or response
bodies to your own logs.
