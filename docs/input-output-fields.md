# Input and output fields

[简体中文](zh-CN/input-output-fields.md)

This document describes the Apify Actor `apple_yang/facebook-transcript-scraper-api`.

Actor page: <https://apify.com/apple_yang/facebook-transcript-scraper-api>

**Evidence basis.** Field and type information comes from the pinned Build `0.0.18`
(Build ID `fZIlpYENof2jYqIJc`, finished 2026-10-19T03:13:17.800Z), read from Apify's build API and
recorded in [actor_audit_20261028.md](audit/actor_audit_20261028.md), then normalised into
[contracts/facebook-transcript-scraper-api-0.0.18.json](audit/contracts/facebook-transcript-scraper-api-0.0.18.json).
Anything marked *unverified* must be checked with your own controlled Run before you depend on it.

## Input

Camel-case, exactly one field:

```json
{
  "videoUrl": "https://www.facebook.com/61567530334836/videos/1115932820735409/"
}
```

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `videoUrl` | string | **Yes** | A public Facebook video page URL. `prefill` in the schema is a form example, not a runtime default |

There is no `bulkUrls`, no `usernames`, no `sessionid`, and no `enhancedcrawl`. If you need several
videos, create several Runs — see [batch processing](batch-processing-guide.md).

### Accepted URL forms

Facebook spreads the same video across several URL shapes. The clients accept these and rewrite
them to a canonical form before submitting:

| Form | Example input | Canonical output |
| --- | --- | --- |
| Watch page | `https://www.facebook.com/watch/?v=1234567890` | same, `?v=` preserved |
| Page video | `https://www.facebook.com/SomePage/videos/987654321/` | same, slug case preserved |
| Videos path | `https://www.facebook.com/videos/1234567890` | `.../videos/1234567890/` |
| Reel | `https://www.facebook.com/reel/1234567890/` | same |
| Legacy entry | `https://www.facebook.com/video.php?v=1234567890` | same |
| Share link | `https://www.facebook.com/share/v/AbCdEf123/` | same |
| Short link | `https://fb.watch/AbCdEf123/` | same |

Normalization rules applied by the clients:

- Host must be `facebook.com`, `www.`, `m.`, `web.`, `fb.watch`, or `www.fb.watch`. `m.` and `web.`
  are rewritten to `www.facebook.com`.
- `https` only; `http` links are rejected with a clear error rather than silently upgraded.
- Tracking parameters (`mibextid`, `rdid`, `ref`, `sfnsn`, …) are dropped. For `watch` and
  `video.php`, exactly one numeric `v` is required and preserved; other forms identify the video by
  path, so their query strings are discarded.
- Fragments, embedded userinfo, and non-default ports are rejected.
- URLs longer than 2048 characters are rejected.

Rejected on purpose: `/login`, `/groups/...`, `/stories/...`, `/photo/...`, `/share/x/...`,
Markdown-wrapped links, and any path that does not match the table above. If Facebook introduces a
new share shape, update the validator rather than loosening it to "accept anything".

> **Unverified:** whether the Actor itself resolves `fb.watch` and `/share/{v,r}/` links. The
> clients pass them through; a resolution failure would surface as `actor_error`.

## Output

The Actor's declared output is a single `results` string that links to the Dataset items URL — not
an inline array. Read the Dataset.

### Dataset fields

| Field | Type | Notes |
| --- | --- | --- |
| `url` | string | Facebook video URL; may differ from the URL you submitted |
| `title` | string | Caption/title. **Not** the transcript |
| `videoUrl` | string | Media/CDN link. Never feed it back as `videoUrl` input |
| `audioUrl` | string | Media link; may be empty or absent |
| `createTime` | integer | 10-digit value, consistent with Unix seconds; unit **unverified** |
| `playCount` | integer | Plays, when available |
| `commentCount` | integer | Comment count |
| `reactionCount` | integer | Reactions |
| `likesCount` | integer | Declared by the schema but absent from the README; semantics **unverified** |
| `shareCount` | integer | Declared by the schema but absent from the README; semantics **unverified** |
| `duration` | number | Believed seconds (README says seconds) |
| `nickname` | string | Creator display name |
| `avatarUri` | string | Creator avatar; may be a temporary link |
| `text` | string | **The transcript.** The field your application consumes |
| `segments` | array | Objects with `start`, `end`, `text`; seconds assumed |
| `errMsg` | string | Per-item business error. Non-empty means the item failed |
| `timestamp` | string | Response timestamp, ISO 8601 in examples |

The Dataset schema marks all 17 fields as `required`. That is a schema declaration, not evidence
that every item carries them. Validate per item; never treat a missing key as a crash.

### Parsing rules

Apply in order — the Python and Node.js clients do exactly this:

1. **Empty Dataset** → `empty`.
2. **Any item with a non-empty `errMsg`** → `actor_error`. Do not count it as success even if
   `text` is present.
3. **At least one non-empty string `text`** → `success`.
4. **No usable text** — `text` null, missing, empty, or a non-string — → `no_transcript` for
   null/missing/empty, `unknown` for an unsupported type.

Additional guidance:

- Preserve unknown extra fields instead of failing the item; the Actor may add fields.
- Keep the raw item next to any normalized record you build.
- `segments` entries are validated: finite numeric `start`/`end`, `start >= 0`, `end >= start`,
  and a string `text`. Invalid entries are dropped from the client's normalized `segments` list but
  stay in the raw item.
- A missing `text` does not prove the video has no speech; it can also mean transcription failed.

## Client result shape

Python `TranscriptResult` and the Node.js result object expose the same information:

| Client field (Python / Node) | Meaning |
| --- | --- |
| `status` | One of the eight statuses in [error handling](error-handling-and-retries.md) |
| `text` | Transcript string or `None` |
| `segments` | Normalized segment list |
| `items` | Raw Dataset items, including fields unknown to the client |
| `run_id` / `runId` | Run identifier |
| `dataset_id` / `datasetId` | Default Dataset identifier |
| `canonical_url` / `canonicalUrl` | URL actually submitted to the Actor |
| `url_form` / `urlForm` | `watch`, `page_video`, `video`, `reel`, `video_php`, `share`, `short_link` |
| `title`, `duration`, `nickname` | Convenience metadata from the transcript item |
| `error` | Business or transport detail, credential-redacted |
| `dataset_complete` / `datasetComplete` | `false` when the configured page limit may have truncated the Dataset |

## Still unverified

Confirmed against schemas and documentation only:

- Real item cardinality: whether one URL can ever yield zero or multiple items.
- Real failure shape for private, deleted, or region-locked videos.
- Whether `errMsg` and a non-empty `text` coexist, and which one is authoritative.
- `fb.watch` and `/share/` resolution.
- Whether the returned `url` echoes or rewrites the submitted form.
- Whether `likesCount`/`shareCount` are populated consistently, or how they differ from
  `reactionCount`.
- Whether the transcription event is billed for silent or failed videos.

Re-run the audit and update the contract JSON when the tagged Build changes.
