# Compatibility and verification

This matrix separates what is implemented from what has been recorded as verified. **Offline-tested**
means covered by local/CI tests with synthetic Dataset items and no network. **Live-verified** means
the path was exercised against the real Actor in a recorded paid Run.

Exactly one round of controlled live Runs has been executed so far — 19 Runs on 2026-10-28, $0.0595
in total, covering four URL forms, all four reference clients, and one batch execution. Two URL
forms turned out not to resolve at Facebook and one remains untested. Evidence:
[live run record](audit/live_run_20261028.md).

## Language status

| Integration | Single URL | CSV batch | Plan-only mode | GET-only resume | Cost estimate |
| --- | --- | --- | --- | --- | --- |
| Python 3.10+ | Implemented, offline-tested, **live-verified** (`share`, `watch`, `page_video`, `reel`) | Implemented, offline-tested, **live-verified** (2 rows) | Yes | Yes | Yes |
| Node.js 18+ | Implemented, offline-tested, **live-verified** (`watch`) | Implemented, offline-tested | Yes | Yes | Yes |
| Go 1.22+ | Implemented, offline-tested, **live-verified** (`watch`) | Implemented, offline-tested | Yes | Yes | Yes |
| Java 17+ | Implemented, offline-tested, **live-verified** (`watch`) | Implemented, offline-tested | Yes | Yes | Yes |
| cURL | Example only | Not implemented | Not applicable | Not implemented | No |
| Rust | Not implemented | — | — | — | — |
| Apify MCP | Documented client setup; not exercised end to end | Not a repository feature | — | — | — |

Rust is deliberately absent rather than shipped unverified: no client is published here unless its
tests run offline in CI. Adding it needs a working `cargo`/`rustc` toolchain plus the usual
`serde`/HTTP crates; the port is mechanical once those exist. Everything else in this repository
builds with the JDK, the Go toolchain, Node.js, or Python alone.

## Actor mode coverage

| Actor mode | Supported by the Actor | Client support |
| --- | --- | --- |
| Single video (`videoUrl`) | Yes | Python, Node.js, cURL |
| Native bulk (`bulkUrls`) | **No such field** | Not applicable |
| Profile posts (`usernames`) | **No such field** | Not applicable |
| CSV batch | Not an Actor mode | One Run per row, client-side |

## Verified by this repository

- Build `0.0.18` and Build ID `fZIlpYENof2jYqIJc` are pinned in both clients and verified at
  runtime from the create response or a Run read.
- Request shape: single `POST` with `{ "videoUrl": ... }`, `restartOnError=false`, `build=0.0.18`,
  optional `maxTotalChargeUsd`.
- Status classification precedence (`empty` → `errMsg` → `text` → `no_transcript` → `unknown`).
- URL validation and canonicalization for the seven accepted forms.
- Journal append/read/permissions and refusal to continue on a corrupt journal.
- Ambiguous create is never retried; 429 on create is never retried.
- Retry behaviour of GET polling and Dataset reads (429/5xx/network only).
- **Live Runs 2026-10-28** (19 Runs, $0.0595): the pinned build matched the service on every Run; the
  `share`, `watch`, `page_video`, and `reel` forms each returned the same 42.261 s video with a
  populated transcript; all 17 Dataset fields were present with the documented units; a successful
  Run cost $0.001 + $0.0045 = $0.0055 and a failing Run cost $0.001 with no `speech2text` event;
  every reference client completed a Run; a 2-row batch mapped `rowId` to CSV line numbers.

All of the above are covered by the offline suites: 90 Python tests, 5 Node.js test files, 70 Go test
cases under `examples/go` (`go test ./...`), and 98 Java assertions under `examples/java`
(`./run_tests.sh`).

## Not verified

- Behaviour for private, deleted, or region-locked videos.
- Whether `fb.watch` short links resolve inside the Actor. The form is accepted by every client and
  forwarded unchanged, but a short code can only be minted inside the Facebook apps, so it could not
  be exercised here.
- Whether `video.php?v=` or bare `/videos/<id>/` resolve for *any* video. Three attempts each were
  answered by Facebook itself with `Not Found` / a generic error page, while the page-scoped
  `/<page>/videos/<id>/` worked on the same ID in the same minute — so those two forms are treated as
  unsupported rather than proven broken for every ID.
- Whether a legacy (pre-reel) page upload behaves differently from the reel-sourced ID used in the
  matrix.
- Item cardinality per Run beyond the single-item case.
- Billing for silent or failed videos, including whether `speech2text` still fires.
- Rate-limit thresholds on Run creation at high concurrency.

## Release vs package publication

A GitHub Release versions this repository snapshot. It does **not** publish anything to PyPI, npm,
or any other registry. Python and Node.js examples are source files; copy them into your project or
import them relatively.

## Related

- [Quick start](quickstart.md)
- [Input and output fields](input-output-fields.md)
- [Cost and limits](cost-and-limits.md)
- [Actor audit](audit/actor_audit_20261028.md)
- [Live run record (2026-10-28)](audit/live_run_20261028.md)
