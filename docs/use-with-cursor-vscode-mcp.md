# Use with Cursor and VS Code

Both editors support MCP servers through a project or user configuration file.

## Cursor

`.cursor/mcp.json` in the project, or the global MCP settings:

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

Cursor supports remote servers with OAuth; complete the browser sign-in when prompted.

## VS Code

`.vscode/mcp.json`:

```json
{
  "servers": {
    "apify": {
      "type": "http",
      "url": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

Use **MCP: List Servers** from the command palette to start the server and inspect its tools. Some
VS Code versions require an `inputs` entry for secrets; keep tokens in the editor's secret storage
rather than in the committed file.

## Local stdio alternative

When remote MCP is blocked by policy:

```json
{
  "mcpServers": {
    "apify": {
      "command": "npx",
      "args": ["-y", "@apify/actors-mcp-server"],
      "env": {
        "APIFY_TOKEN": "${env:APIFY_TOKEN}",
        "ACTORS": "apple_yang/facebook-transcript-scraper-api"
      }
    }
  }
}
```

## Agent prompt

```
Use the Apify Facebook Transcript tool exactly once for:
https://www.facebook.com/watch/?v=1234567890

Then:
- if errMsg is non-empty, report the failure and stop;
- otherwise print text verbatim and the segment count.
Never retry a timed-out call; the first Run may already exist.
```

## Repo hygiene

- `.vscode/` and `.cursor/` are git-ignored in this repository; commit an example config without
  secrets if your team needs one.
- Do not let an agent write a token into `.cursor/mcp.json`.

See also: [Apify MCP](use-with-apify-mcp.md) · [Production checklist](production-integration-checklist.md).
