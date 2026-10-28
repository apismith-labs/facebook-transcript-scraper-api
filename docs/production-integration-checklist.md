# Production integration checklist

[简体中文](zh-CN/production-integration-checklist.md)

Use this before pointing a real workload at the Actor.

## Credentials

- [ ] `APIFY_TOKEN` comes from a secret manager, not a committed file.
- [ ] `.env` is git-ignored; `.env.example` contains placeholders only.
- [ ] Tokens are rotated on a schedule and immediately on suspected exposure.
- [ ] The token is never placed in a URL, a query string, or a log line.

## Cost

- [ ] You computed an estimate with the real duration distribution, not the Store headline.
- [ ] Every call site sets `maxTotalChargeUsd`; batch jobs also use `--require-charge-cap`.
- [ ] Free-plan jobs are filtered to videos of 5 minutes or less.
- [ ] A monthly budget alert exists in Apify Console.
- [ ] Batch jobs start with `--limit` and a small concurrency.

## Idempotency

- [ ] You never retry a create `POST`; ambiguity is treated as `creation_unknown`.
- [ ] You persist `runId`, `datasetId`, and `rowId` before polling.
- [ ] Recovery reads the existing Run; it never creates a replacement.
- [ ] Duplicate input URLs are removed upstream if you do not want duplicate charges.

## Build stability

- [ ] Clients pin `build=0.0.18` and verify `buildId=fZIlpYENof2jYqIJc`.
- [ ] You have a procedure for re-auditing when the Actor's tagged build changes.
- [ ] A Build mismatch fails loudly instead of silently accepting new fields.

## Failure handling

- [ ] `actor_error`, `no_transcript`, `empty`, and `run_failed` are handled as distinct outcomes.
- [ ] Retries apply only to GET polling and Dataset reads (429/5xx/network).
- [ ] Alerting is driven by business statuses, not process exit code alone.
- [ ] A permanent failure is not retried in a loop that creates new Runs.

## Data handling

- [ ] Raw items are stored alongside normalized text so upstream changes stay auditable.
- [ ] `videoUrl`/`audioUrl` are treated as expiring CDN links, not durable assets.
- [ ] Transcript storage follows your retention and privacy policy.
- [ ] Engagement counts are timestamped and treated as snapshots.
- [ ] Journals and result files keep mode `0600` and live on encrypted storage.

## Observability

- [ ] Each Run is logged with `runId`, `datasetId`, status, build number, and duration.
- [ ] Cost per successful transcript is tracked, not just total spend.
- [ ] The success/failure ratio is monitored per URL form (watch, reel, share, short link).
- [ ] Journal corruption would fail the job rather than silently dropping history.

## Compliance

- [ ] You have the right to process the content you submit.
- [ ] You respect Facebook's terms and applicable local law.
- [ ] Downstream use (training, publishing, moderation) is cleared for the content type.
