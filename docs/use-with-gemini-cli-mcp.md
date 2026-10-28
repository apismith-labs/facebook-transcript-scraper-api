# Use with Gemini CLI

Gemini CLI reads MCP servers from its settings file (typically `~/.gemini/settings.json`). Remote
HTTP servers are supported directly.

## Configuration

```json
{
  "mcpServers": {
    "apify": {
      "httpUrl": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

If your Gemini CLI version expects a header instead of OAuth:

```json
{
  "mcpServers": {
    "apify": {
      "httpUrl": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api",
      "headers": {
        "Authorization": "Bearer ${APIFY_TOKEN}"
      }
    }
  }
}
```

Prefer the environment-variable form over pasting a literal token; shell history and dotfiles leak.

## Verify discovery

```bash
gemini
/mcp
```

The Apify server should appear with its tools listed. Tool names depend on the server version — use
what `/mcp` reports rather than a name from this page.

## First request

```
Use the Apify MCP tool to transcribe:
https://www.facebook.com/watch/?v=1234567890

Print the transcript, the segment count, and the run ID.
If the tool call fails or times out, do not retry — report the error instead.
```

## Non-interactive use

```bash
gemini -p "Transcribe https://www.facebook.com/watch/?v=1234567890 with the Apify tool and print only the transcript" \
  --allowed-mcp-server-names apify
```

Flag names vary by version; check `gemini --help` before scripting it.

## Cautions

- Each call can create a billable Run.
- One URL per call; no bulk parameter.
- Public videos only.

See also: [Apify MCP](use-with-apify-mcp.md) · [Cost](cost-and-limits.md).
