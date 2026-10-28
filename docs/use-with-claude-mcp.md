# Use with Claude (MCP connector)

Claude supports remote MCP connectors in its desktop and web apps on eligible plans, and local
stdio servers in Claude Desktop. Either path can reach this Actor.

## Remote connector

1. Open **Settings → Connectors → Add custom connector**.
2. Enter the URL:

   ```
   https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api
   ```

3. Complete the Apify OAuth sign-in.
4. Start a chat and enable the connector.

## Claude Desktop (stdio)

```json
{
  "mcpServers": {
    "apify": {
      "command": "npx",
      "args": ["-y", "@apify/actors-mcp-server"],
      "env": {
        "APIFY_TOKEN": "your_apify_token_here",
        "ACTORS": "apple_yang/facebook-transcript-scraper-api"
      }
    }
  }
}
```

Restart Claude Desktop after editing the config. Keep the token in the desktop environment rather
than in a synced file when possible.

## First request

```
Transcribe this public Facebook video with the Apify tool:
https://www.facebook.com/watch/?v=1234567890

Show: status, transcript text, segment count, duration.
If the item has a non-empty errMsg, quote it and do not retry the call.
```

## Notes on model behaviour

- Claude may summarize instead of quoting. Ask for verbatim text if you need the transcript exactly.
- Dataset items include CDN media URLs; they expire. Do not treat them as permanent.
- If the model proposes a second call after a timeout, refuse it — the first Run may already exist.

## Verify a Run without creating another

If a call times out, ask for the `runId`, then inspect it read-only:

```bash
export APIFY_TOKEN='...'
python scripts/check_apify_run.py RUN_ID
```

See also: [Apify MCP](use-with-apify-mcp.md) · [Error handling](error-handling-and-retries.md).
