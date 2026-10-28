# Cost and limits

[简体中文](zh-CN/cost-and-limits.md)

The Store page says **"from $1.00 / 1,000 results"**. That figure describes one of two billing
events. The real cost of a transcript is the sum of both.

## Two events per successful transcription

| Event | Price (captured 2026-10-28) | Unit |
| --- | --- | --- |
| `apify-default-dataset-item` | **$0.001** | per dataset item |
| `speech2text` | **$0.0045** (FREE) · $0.0035 (BRONZE) · $0.003 (SILVER) · $0.002 (GOLD, PLATINUM, DIAMOND) | per started minute |

Any duration under one minute is billed as one minute. A 30-second clip therefore costs the same
transcription fee as a 60-second clip.

Formula for one video:

```
cost = 0.001 + ceil(max(duration_seconds, 1) / 60) × tier_price_per_minute
```

| Video length | FREE tier | GOLD tier |
| --- | --- | --- |
| 30 s | $0.0055 | $0.0030 |
| 1 min | $0.0055 | $0.0030 |
| 10 min | $0.0460 | $0.0210 |
| 30 min | $0.1360 | $0.0610 |
| 60 min | $0.2710 | $0.1210 |

One thousand one-minute videos cost **$5.50** on FREE, not $1.00. The Store headline counts only
the dataset-item event.

Estimate before you run:

```bash
python scripts/estimate_cost.py --videos 1000 --minutes 1 --tier FREE
python scripts/estimate_cost.py --videos 20 --minutes 8 --tier GOLD --json
```

The batch runners print the same estimate during their plan phase, before any Run exists.

## Plan limits

- **Free plan:** videos up to **5 minutes**. Longer videos are documented as rejected.
- **Paid plans:** duration is documented as unlimited.
- Beyond duration, the practical limits are public accessibility of the video and the Actor's own
  success rate for that URL.

## What can make the actual bill differ

- The `speech2text` event may not fire for a silent video or a failed transcription. **Unverified.**
- A video reported as `no_transcript` may still have incurred the transcription charge.
- Apify plan discounts change the per-minute tier without changing the dataset-item price.
- Apify's own platform usage is documented as included in this Actor's pay-per-event pricing, but
  your account's plan and any proxy or storage usage remain your responsibility.
- Pricing is versioned server-side. The actor metadata already contains a superseded schedule
  (2026-03-06: $0.0006 per result + $0.001 per minute). Do not hard-code either schedule; re-read
  pricing when it matters.

## Controlling spend

| Control | Where |
| --- | --- |
| Per-Run charge cap | `--max-total-charge-usd 0.10`, or `APIFY_MAX_TOTAL_CHARGE_USD` |
| Refuse to run without a cap | `--require-charge-cap`, or `APIFY_REQUIRE_MAX_TOTAL_CHARGE_USD=1` |
| Batch plan-only mode | `batch_csv.py file.csv` (no `--execute`) |
| Row limit | `--limit 10` |
| Concurrency | `--max-concurrency 1` for tight budgets |
| Trim the input set | One URL per row; blank rows are skipped, duplicates are **not** removed |

A requested cap is a Run option, not a guaranteed final invoice. Apify may complete or abort a Run
according to its own accounting; treat the cap as a strong guardrail, not a hard ceiling.

## Limits of the data itself

- Transcripts are auto-generated speech-to-text; accuracy depends on audio quality, language, and
  speaker overlap.
- Only the audio track is transcribed. On-screen captions are not read.
- Engagement counts (`playCount`, `commentCount`, `reactionCount`, `likesCount`, `shareCount`) are
  point-in-time snapshots and may be missing.
- `videoUrl` and `audioUrl` are CDN links that can expire; do not store them as durable assets.
