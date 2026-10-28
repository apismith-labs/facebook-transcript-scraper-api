# Prompt recipes for Facebook video transcripts

These prompts assume you already have a `success` result with `text`, `segments`, `title`,
`nickname`, and `url`. They are starting points, not guarantees.

## 1. Timestamped summary

```
You are given a video transcript as timestamped segments.
Write a summary of at most 8 bullets.
Every bullet must end with the timestamp of the segment that supports it, in [MM:SS] form.
Do not add facts that are not in the transcript.
If the transcript is incoherent, say so instead of guessing.
```

## 2. Hook and structure analysis

```
Analyze only the first 30 seconds of this transcript.
Return JSON:
{
  "hook_type": "question|claim|story|demo|other",
  "first_sentence": "...",
  "promise": "...",
  "payoff_timestamp": "MM:SS or null",
  "notes": "..."
}
```

## 3. Claim extraction with evidence

```
Extract every factual claim the speaker makes.
For each claim return:
- claim text
- supporting quote (verbatim, <= 25 words)
- timestamp
- confidence: high|medium|low, based only on how clearly the transcript supports it
Do not include opinions or rhetorical questions.
```

## 4. Segment-preserving translation

```
Translate each segment's text into {target_language}.
Keep the segment count and order identical. Do not merge or split segments.
Preserve names, numbers, and product terms.
Return JSON: [{"start": number, "end": number, "text": "translated"}]
```

## 5. Content repurposing

```
Using only this transcript, draft:
1. a 120-word LinkedIn post
2. five short X posts
3. a 6-line newsletter section
Keep the speaker's point of view. Do not invent statistics or quotes.
Mark any place where the transcript is unclear with [unclear].
```

## 6. Moderation pre-screen

```
Classify the transcript against these categories: harassment, medical advice, financial advice,
explicit content, none.
Return JSON with category, severity (none|low|medium|high), and a short quoted justification with
timestamp. If the transcript is empty, return category "unknown".
```

## 7. Q&A extraction

```
Identify question/answer pairs in this transcript.
Return JSON: [{"question": "...", "answer": "...", "timestamp": "MM:SS"}]
Only include pairs where the question is actually asked and answered in the video.
```

## 8. Metadata hygiene

```
Given the title and transcript, propose:
- a 60-character descriptive title
- 5 topical tags
- a one-sentence description
Do not use clickbait. Do not claim anything not supported by the transcript.
```

## Practical notes

- Feed segments, not just the full text, when timestamps matter.
- Tell the model the transcript is auto-generated and may contain recognition errors.
- Ask for JSON when the output feeds another step; validate before storing.
- Never send a transcript whose status is `no_transcript` or `actor_error`.
