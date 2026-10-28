# AI agent use cases

The Actor returns text, timestamped segments, and metadata. It does not summarize, classify, or
analyze — that belongs to your model. This page describes patterns that work well with the
returned shape.

## Ingestion for retrieval (RAG)

1. Submit URLs through the batch runner; keep `rowId` as the stable document key.
2. Store each segment with `start`/`end` so citations can point at a timestamp.
3. Index chunks of roughly 30–60 seconds, overlapping by one segment.
4. Store `url`, `title`, `nickname`, and `duration` as filterable metadata.
5. Skip items whose status is not `success`; do not index empty strings.

Why segments instead of the full text: retrieval quality improves when a chunk maps to a spoken
passage, and citations like `[02:14]` are verifiable by a human.

## Content research and competitor analysis

- Compare hook structure in the first 15 seconds across creators.
- Measure speaking pace (`segment count / duration`) as a rough proxy.
- Cluster topics from transcripts, then join with `playCount`/`reactionCount` for performance
  context — while remembering these are point-in-time snapshots.

## Moderation and compliance review

- Screen transcripts for policy categories before republishing.
- Preserve raw items so a review decision can be audited later.
- Treat `no_transcript` as "needs human review", not "clean".

## Customer-support and FAQ mining

Q&A videos often contain repeated questions. Segment-level text makes it practical to extract
question/answer pairs, then route them to a knowledge base.

## Localization

Translate segment by segment to keep timing intact, then re-emit subtitles. This repository does
not generate SRT/VTT, but `segments` is enough to build them:

```
index
HH:MM:SS,mmm --> HH:MM:SS,mmm
text
```

## Agent workflow shape

```
URL list (CSV)
  -> batch runner (plan, then execute)
  -> result JSON (status, text, segments, raw items)
  -> filter status == success
  -> chunk + embed + metadata
  -> retrieval / summarization / moderation
```

## Guardrails worth wiring in

- Cap the number of URLs per job and the per-Run charge.
- Reject rows without a transcript instead of sending empty context to a model.
- Keep the transcript's `url` next to any generated claim so it can be traced back.
- Never let an agent create a replacement Run after an ambiguous create; give it a `resume` tool
  instead, or require human reconciliation.
- Rate-limit concurrency; higher values mean more simultaneous billable Runs and more 429 exposure.

## Related

- [Prompt recipes](prompt-recipes-for-facebook-video-analysis.md)
- [Batch processing](batch-processing-guide.md)
- [Cost and limits](cost-and-limits.md)
