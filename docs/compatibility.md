# Compatibility and verification

[简体中文](zh-CN/compatibility.md)

This matrix separates what is implemented from what has been recorded as verified. **Offline-tested**
means covered by local/CI tests with synthetic Dataset items and no network. **Live-unverified**
means the code path exists but no controlled paid Run was recorded for this repository.

No live paid Run was executed while building this repository. Field shapes in tests come from the
pinned build's schema, not from a recorded response.

## Language status

| Integration | Single URL | CSV batch | Plan-only mode | GET-only resume | Cost estimate |
| --- | --- | --- | --- | --- | --- |
| Python 3.10+ | Implemented, offline-tested, live-unverified | Implemented, offline-tested | Yes | Yes | Yes |
| Node.js 18+ | Implemented, offline-tested, live-unverified | Implemented, offline-tested | Yes | Yes | Yes |
| Go 1.22+ | Implemented, offline-tested, live-unverified | Implemented, offline-tested | Yes | Yes | Yes |
| Java 17+ | Implemented, offline-tested, live-unverified | Implemented, offline-tested | Yes | Yes | Yes |
| cURL | Example only | Not implemented | Not applicable | Not implemented | No |
| Rust | Not implemented | — | — | — | — |

Rust is deliberately absent rather than shipped unverified: no client is published here unless its
tests run offline in CI. Adding it needs a working `cargo`/`rustc` toolchain plus the usual
`serde`/HTTP crates; the port is mechanical once those exist. Everything else in this repository
builds with the JDK, the Go toolchain, Node.js, or Python alone.
| Apify MCP | Documented client setup; not exercised end to end | Not a repository feature | — | — | — |

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

All of the above are covered by the offline suites: 89 Python tests, 5 Node.js test files, 68 Go test
cases under `examples/go` (`go test ./...`), and 89 Java assertions under `examples/java`
(`./run_tests.sh`).

## Not verified

- Any real Actor response for a valid public video.
- Behaviour for private, deleted, or region-locked videos.
- Whether `fb.watch` and `/share/{v,r}/` links resolve inside the Actor.
- Item cardinality per Run; the clients tolerate zero or many but expect one.
- Actual billing, including whether `speech2text` fires for silent videos.
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
