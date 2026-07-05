---
name: mcp-frame-inspector
description: Parses and intercepts JSON-RPC 2.0 frames over MCP's stdio and Server-Sent Events (SSE) transports, and implements tool-schema hashing to detect rug-pull attacks. Use when building or modifying the AXIOM proxy layer, any code that reads/writes MCP protocol messages, or anything related to tool description verification between sessions.
---

# MCP Frame Inspector

## When this applies
Any task touching: the proxy's transport layer, parsing `tools/list` / `tools/call` / `initialize` messages, session state tracking, or verifying a tool hasn't changed since last seen.

## Core rules

### Transport handling
MCP servers communicate over two transports that must both be supported:
- **stdio** — the dominant transport for local-process MCP servers. Frames are newline-delimited JSON-RPC 2.0 objects over stdin/stdout.
- **SSE (Server-Sent Events)** — used by remote/hosted MCP servers. Frames arrive as `event:`/`data:` blocks over a long-lived HTTP connection.

Both transports carry the same JSON-RPC 2.0 message shape (`jsonrpc`, `id`, `method`, `params` / `result` / `error`). Write the frame parser once against the JSON-RPC shape, then adapt only the transport-level framing (newline-delimited vs. SSE event blocks) — do not duplicate parsing logic per transport.

### Tool-schema hashing (rug-pull defense)
This is the single most important behavior in this skill:

1. On first connection to any MCP server, capture the full `tools/list` response.
2. Compute a stable hash of that response (normalize key ordering before hashing — JSON key order is not guaranteed stable across servers/languages).
3. Store the hash keyed by server identity (not by session — the check must survive across sessions).
4. On every subsequent connection to that same server, re-fetch `tools/list`, recompute the hash, and compare.
5. If the hash differs: **do not silently accept the new schema.** Surface a rug-pull alert with a diff of what changed (which tool, which field — name, description, or input schema) before any tool call against that server proceeds.

Never skip step 5 "for now" or "to unblock testing" — this exact shortcut is how real rug-pull incidents happen in production MCP deployments.

### Session state machine
Track each agent-to-server conversation through its full lifecycle: connection → tool discovery → individual tool calls → teardown. Do not treat each frame as an isolated, stateless event — a huge share of the interesting security signal (e.g., a tool being called with arguments that don't match any prior pattern, or a session persisting far longer than its peers) only shows up when you look at the whole session, not one frame at a time.

## What NOT to do
- Don't write a transport-specific parser twice — factor out the shared JSON-RPC layer first.
- Don't hash `tools/list` responses without normalizing key order first, or you'll get false-positive rug-pull alerts from servers that just serialize JSON differently.
- Don't drop the pre-existing hash when a server goes offline and comes back — the hash must persist independent of connection state.
