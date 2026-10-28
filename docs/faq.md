# FAQ

### Do I need an Apify account?

Yes. The Actor runs on Apify and is billed per event. Create a token in Apify Console under
**Settings → API & Integrations**, then export it as `APIFY_TOKEN`.

### Can I transcribe several videos in one call?

No. The Actor input has a single `videoUrl` field. Submitting an array is not part of the schema.
Use the CSV batch runner, which creates one Run per row.

### Can I get posts from a Facebook page or profile?

No. This Actor has no `usernames`/profile mode; it transcribes video URLs you already have. If you
need discovery, use a separate scraper and pass the resulting video URLs here.

### Why is my bill higher than "$1 per 1,000 results"?

Because that headline covers only the dataset-item event ($0.001/item). Transcription is billed per
started minute ($0.0045 on FREE down to $0.002 on GOLD+). A 10-minute video is about $0.046 on
FREE. See [cost and limits](cost-and-limits.md).

### The Run succeeded but `text` is empty. Is that a bug?

Not necessarily. `no_transcript` means the Dataset item carried no usable text: silent video,
music-only clip, failed speech recognition, or a field the Actor omitted. Check `errMsg`, `title`,
and `duration` before assuming a client bug.

### What does a non-empty `errMsg` mean?

It is a per-item business failure. The clients classify the result as `actor_error` even if `text`
is also present, and they never count it as a success. Typical causes: private video, deleted post,
region lock, or an unsupported URL shape.

### Which Facebook URL forms are accepted?

`/watch/?v=`, `/{page}/videos/{id}/`, `/videos/{id}/`, `/reel/{id}/`, `/video.php?v=`,
`/share/v/{code}/`, `/share/r/{code}/`, and `fb.watch/{code}/`. Tracking parameters are stripped.
See [accepted URL forms](input-output-fields.md#accepted-url-forms).

### My share link is rejected. Why?

Only the forms above are accepted. Markdown-wrapped links, `http://` links, fragments, and unknown
paths are rejected on purpose rather than guessed at. Open the link in a browser and copy the final
`facebook.com/...` URL.

### Can I use a private or friends-only video?

No. The Actor documents public videos only, and there is no cookie or `sessionid` input.

### Is there a length limit?

Free plans can transcribe videos up to 5 minutes. Paid plans are documented as unlimited by
duration. Very long videos also cost proportionally more.

### How do I avoid double billing on retries?

Never retry the create `POST`. The clients create at most once per input; an ambiguous response
becomes `creation_unknown` and stops. If a Run exists, resume it with `--resume RUN_ID` (GET-only).

### How do I know which Build produced a result?

The clients pin Build `0.0.18` and verify Build ID `fZIlpYENof2jYqIJc`. The journal records
`buildNumber`, `buildId`, and `buildVerification` for each Run.

### Does the client need third-party packages?

No. Python uses the standard library; Node.js uses built-in `fetch`. Tests also need nothing beyond
the runtime.

### Can I run the tests without a token?

Yes, and CI does exactly that. All tests use synthetic fixtures and a fake transport; none touches
the network.

### Where do result files go?

Single-URL CLIs write only when you pass `--output` or `--json`; the journal goes to
`sample-output/generated/`. Batch runners write a unique `facebook-batch-results-<UTC>.json` beside
the CSV (or at `--output`) plus a journal in the same directory.
