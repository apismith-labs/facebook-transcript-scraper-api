# Use with Apify MCP

Apify hosts an MCP server that can expose this Actor to an MCP-compatible client. This repository
does not host an MCP server; it documents the path and the behaviour you should expect.

## Hosted server

```json
{
  "mcpServers": {
    "apify": {
      "type": "http",
      "url": "https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api"
    }
  }
}
```

The `tools=` query string selects the Actor. The hosted server signs you in with OAuth on first
connect, so no token belongs in this config. Clients without OAuth support can send
`Authorization: Bearer <APIFY_API_TOKEN>`.

## Local server (stdio)

Useful when the client does not support remote MCP, or when you want the token to stay in your own
environment:

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

## What the model can do

Depending on the server and client version, the exposed tools let the model:

- inspect the Actor's input schema and README;
- call the Actor with `{ "videoUrl": "..." }`;
- read the returned Dataset items.

Tool names and the exact call shape vary by server version. Ask the client to list its tools once
and use what it reports instead of hard-coding a name.

## A working prompt

```
Use the Apify Facebook Transcript Actor.
Call it once with videoUrl = "https://www.facebook.com/watch/?v=1234567890".
If the Run succeeds, print the transcript text and the number of segments.
If errMsg is non-empty, say the item failed and quote errMsg.
Do not call the Actor a second time if the first call times out; tell me to check Apify instead.
```

That last instruction matters: an MCP retry is still a new paid Run.

## Limits you should state in the prompt

- One `videoUrl` per call; there is no bulk input.
- Public videos only; no cookies or `sessionid`.
- Transcription is billed per started minute, not per result.
- A completed Run can still have no transcript.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Actor not in the tool list | `tools=` query missing, or the client filtered it out |
| 401/403 | OAuth not completed, or a missing/invalid bearer token |
| Two Runs for one URL | The client retried the call; reconcile in Apify |
| Empty transcript | The item has no `text`; inspect `errMsg` |

See also: [ChatGPT](use-with-chatgpt-mcp.md) · [Claude](use-with-claude-mcp.md) ·
[Gemini CLI](use-with-gemini-cli-mcp.md) · [Cursor / VS Code](use-with-cursor-vscode-mcp.md).
