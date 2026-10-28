# Actor audit — `apple_yang/facebook-transcript-scraper-api`

[简体中文](../zh-CN/audit/actor_audit_20261028.md)

Audit date: **2026-10-28**. Pinned build: **0.0.18** (`fZIlpYENof2jYqIJc`, finished
2026-10-19T03:13:17.800Z). This document records what was read directly from Apify's public API and
what remains unverified. It is the evidence base for the client code in this repository.

## Evidence sources

| Source | What it established |
| --- | --- |
| `GET /v2/acts/apple_yang~facebook-transcript-scraper-api` | Actor ID `qoPsXcbeGbncRrc4N`, tagged `latest` build 0.0.18, default run options (4096 MB, 3600 s), pricing events |
| `GET /v2/actor-builds/fZIlpYENof2jYqIJc` | Verbatim `inputSchema`, `actorDefinition.output`, `actorDefinition.storages.dataset.fields` |
| `GET /v2/actors/qoPsXcbeGbncRrc4N/builds/fZIlpYENof2jYqIJc/openapi.json` | Run endpoint path, `token` query parameter, build id header |
| `https://apify.com/apple_yang/facebook-transcript-scraper-api.md` | README-level behavior: public videos only, 5-minute free limit, output field prose |
| No live Run was executed for this audit | Runtime behavior below is marked unverified where applicable |

## Input contract

```json
{
  "videoUrl": "https://www.facebook.com/61567530334836/videos/1115932820735409/"
}
```

The fixed build declares `required: ["videoUrl"]` and exactly one property. There is **no**
`bulkUrls`, **no** `usernames`, **no** `sessionid`, and **no** `enhancedcrawl`. This is the single
largest difference from the Instagram sibling Actor and it dictates the repository layout: batch
processing is a client-side orchestrator that creates one Run per URL, not an Actor mode.

`prefill` is form pre-filling, not a runtime default. The field is genuinely required.

## Output contract

The Actor's declared output is a `results` string whose template points at the default Dataset
items URL — not an inline array. Consumers must read the Dataset.

Dataset fields from the pinned build (17 total):

`url`, `title`, `videoUrl`, `audioUrl`, `createTime`, `playCount`, `commentCount`,
`reactionCount`, `likesCount`, `shareCount`, `duration`, `nickname`, `avatarUri`, `text`,
`segments[]`, `errMsg`, `timestamp`

### Discrepancies worth knowing before parsing

1. **`likesCount` and `shareCount` are absent from the README output table** but are declared in
   the Dataset schema. Neither has a documented meaning distinct from `reactionCount`. Preserve
   them; do not invent semantics.
2. **`videoUrl` is a media/CDN link**, not a page URL. Never feed it back as `videoUrl` input.
3. **Every field is marked `required` in the Dataset definition**, including `text` and
   `segments`. That is a schema declaration, not evidence that every item carries them. Validate
   per item and treat missing keys as normal.
4. **`errMsg` is the per-item business error.** A `SUCCEEDED` Run with a non-empty `errMsg` is a
   failure for that item.
5. `duration` unit is believed to be seconds (README says "video duration (seconds)"); `createTime`
   is a 10-digit integer, consistent with Unix seconds for the sample. Both remain unverified
   beyond documentation.

## Pricing captured 2026-10-28

| Event | Price | Notes |
| --- | --- | --- |
| `apify-default-dataset-item` | $0.001 per item | Primary event; this is the "$1.00 / 1,000 results" on the Store page |
| `speech2text` | $0.0045 / min (FREE) → $0.0035 (BRONZE) → $0.003 (SILVER) → $0.002 (GOLD+) | Billed per minute; any duration under 1 minute is billed as 1 minute |

The Store headline understates real cost for anything longer than a few seconds, because it omits
the transcription event. A 10-minute video costs roughly **$0.046** on FREE or **$0.021** on GOLD.
`docs/cost-and-limits.md` and `scripts/estimate_cost.py` implement this model.

Pricing is versioned server-side. `pricingInfos` shows an earlier schedule (2026-03-06:
$0.0006 per result + $0.001 per minute) that is superseded; do not hard-code the old numbers.

## Limits

- Public videos only. Private, friends-only, deleted, or region-locked content may fail.
- Free plan: videos up to 5 minutes. Paid plans: documented as unlimited by duration.
- Audio only: on-screen text is not transcribed.
- Transcript quality depends on the audio track.

## What this repository assumes, and what it refuses to assume

Assumed (conservative, documented in code):

- One submitted URL produces one dataset item. The client additionally tolerates zero or multiple
  items and reports `empty` / aggregated status instead of guessing.
- `text` is the transcript; `title` is the caption and never treated as a transcript.
- A non-empty `errMsg` invalidates the item even if `text` is also present.

Not assumed:

- That a missing `text` means the video has no speech (it can also mean a failed transcription).
- That `segments` is well-formed. Every entry is checked for finite `start`/`end` with
  `start <= end`; malformed entries are dropped from the normalized view but preserved in the raw
  item.
- That short links and share links work. They are accepted by the client validator, but the Actor
  side is unverified.

## Reproduce this audit

```bash
curl -s "https://api.apify.com/v2/acts/apple_yang~facebook-transcript-scraper-api" | jq '.data.taggedBuilds.latest'
curl -s "https://api.apify.com/v2/actor-builds/fZIlpYENof2jYqIJc" | jq -r '.data.inputSchema'
curl -s "https://api.apify.com/v2/actor-builds/fZIlpYENof2jYqIJc" | jq '.data.actorDefinition.storages.dataset.fields'
```

If the tagged build changes, re-run this audit and update the contract JSON before changing
`APPROVED_BUILD_NUMBER` in the clients.
