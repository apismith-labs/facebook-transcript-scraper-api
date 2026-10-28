# Use with ChatGPT (MCP connector)

ChatGPT can call remote MCP servers as connectors on plans that support them. Availability,
naming, and menu positions change; treat this as a shape, not a click-by-click script.

## Setup

1. In ChatGPT, open **Settings → Connectors** (or the Apps/Connectors section of your plan).
2. Add a custom connector with the MCP URL:

   ```
   https://mcp.apify.com/?tools=fetch-actor-details,apple_yang/facebook-transcript-scraper-api
   ```

3. Complete the Apify OAuth flow when prompted.
4. In a new chat, enable the connector for the conversation.

If your plan or workspace does not allow custom connectors, use the API directly or run the
examples locally instead.

## First request

```
Use the connected Apify tool to transcribe this public Facebook video:
https://www.facebook.com/watch/?v=1234567890

Return the transcript and the segment count. If errMsg is not empty, quote it and stop.
```

## Behaviour to expect

- One call transcribes one URL. There is no multi-URL parameter.
- The tool returns Dataset items, not a single transcript string; the model must read `text`.
- A `SUCCEEDED` Run with empty `text` is still a failure for your purpose.
- ChatGPT may retry a failed tool call. Each retry can create a new billable Run; state "do not
  retry" in the prompt and in the connector instructions.

## Guardrails for shared workspaces

- Use a dedicated Apify token with a spending limit.
- Keep the connector disabled by default in workspaces where users should not start paid Runs.
- Never paste a token into a chat message; use the OAuth connector or workspace secret storage.
- Log the `runId` the tool returns so spend can be reconciled.

## Limits

- Public videos only.
- Free Apify plans: videos up to 5 minutes.
- No profile or page-listing mode on this Actor.

See also: [Apify MCP](use-with-apify-mcp.md) · [FAQ](faq.md) · [Cost](cost-and-limits.md).
