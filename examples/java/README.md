# Use Facebook Transcript Scraper API with Java

Java 17+, JDK only. No Maven, no Gradle, no third-party libraries: HTTP goes through
`java.net.http`, and `Json.java` is a small reader/writer that covers what Apify returns.

[简体中文](README.zh-CN.md) · [Quick start](../../docs/quickstart.md)

## Files

| File | Purpose |
| --- | --- |
| `ReliableActor.java` | Staged runner: transport, classification, retry policy, JSONL journal, sanitization |
| `TranscriptClient.java` | `getTranscript()`, URL validation, result and exception types |
| `Json.java` | Minimal JSON parser and writer (no dependencies) |
| `Cost.java` | Two-event pricing model and the one-minute billing floor |
| `SingleUrl.java` | CLI with `.env` loading, `--json`, `--output`, `--resume`, journaling |
| `BatchCsv.java` | One Run per CSV row; plan-only unless `--execute` |
| `Quickstart.java` | Minimal CLI, no journal |
| `OfflineTests.java` | Dependency-free assertion runner |

## Build and run

```bash
cd examples/java
mkdir -p out
javac -encoding UTF-8 -d out $(find src/main/java -name '*.java')

export APIFY_TOKEN='your_apify_token_here'
java -cp out com.apismith.facebooktranscript.Quickstart 'https://www.facebook.com/watch/?v=1234567890'
```

## Reusable API

```java
import com.apismith.facebooktranscript.TranscriptClient;

TranscriptClient.Options options = new TranscriptClient.Options();
TranscriptClient.Result result = TranscriptClient.getTranscript(
        "https://www.facebook.com/watch/?v=1234567890", options);

if (result.succeeded()) {
    System.out.println(result.text());
    for (var segment : result.segments()) {
        System.out.println(segment.get("start") + " " + segment.get("text"));
    }
} else {
    System.out.println(result.status() + " " + result.error());
}
```

`Result` fields: `status`, `text`, `segments`, `items`, `runId`, `datasetId`, `sourceUrl`,
`canonicalUrl`, `urlForm`, `error`, `datasetComplete`, `title`, `nickname`, `duration`. Methods
`succeeded()` and `exitCode()` mirror the other clients.

Checked exceptions: `ConfigurationException`, `ProtocolException` (with `runId`), `TransportException`,
and `CreationUnknownException`. Business outcomes are returned, never thrown.

Options: `token`, `actorId`, `build`, `timeoutSeconds`, `maxTotalChargeUsd`, `requireChargeCap`,
`datasetLimit`, `runId`, `rowId`, `transport`, `journal`.

## CLI

```bash
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/watch/?v=1234567890'
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/reel/1234567890/' --json
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/watch/?v=1234567890' --resume RUN_ID
java -cp out com.apismith.facebooktranscript.SingleUrl 'https://www.facebook.com/watch/?v=1234567890' \
  --require-charge-cap --max-total-charge-usd 0.10
```

Exit codes match the Python and Node.js clients: `0` success, `4` actor_error, `5` empty,
`6` no_transcript, `7` unknown, `8` transport_error, `9` run_failed, `10` creation_unknown,
`2` configuration, `3` protocol.

The CLI loads `.env` from the working directory, reading only `APIFY_*` keys, and never overrides an
existing environment variable. Its journal is `sample-output/generated/java-run-journal.jsonl`.

## Batch

```bash
java -cp out com.apismith.facebooktranscript.BatchCsv ../../sample-data/facebook-video-urls.csv
java -cp out com.apismith.facebooktranscript.BatchCsv ../../sample-data/facebook-video-urls.csv --execute
java -cp out com.apismith.facebooktranscript.BatchCsv file.csv --limit 5 --max-concurrency 2 --output out.json --execute
```

CSV columns: `videoUrl` (or `url`) required, `durationSeconds` optional. Line numbers become
`rowId`. The result file defaults to `facebook-batch-results-<UTC>.json` beside the CSV; the journal
is `java-run-journal.jsonl` in the same directory. Exit `0` when every row succeeded, `1` when at
least one did not, `2` for a CSV or configuration error.

## Tests

```bash
cd examples/java
./run_tests.sh
```

The runner compiles everything into `out/` and executes 89 offline assertions with fake transports
and temporary journals. No token, no network, no `.env`.
