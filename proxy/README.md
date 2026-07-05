# proxy/

FastAPI-based MCP protocol proxy — the core of AXIOM.

## Responsibility

- Terminate agent-facing MCP connections (both `stdio` and SSE transports)
- Parse JSON-RPC 2.0 frames in real time
- Forward, block, or rewrite traffic to real MCP server(s)
- Mirror every frame to the analysis + storage layer
- Maintain session state machine (connection → discovery → calls → teardown)

## Key design decisions

- **Async-first** — MCP transports are long-lived streaming connections; synchronous handling would serialize what needs to stay concurrent across dozens of simultaneous sessions.
- **Single JSON-RPC parser, two transport adapters** — the frame parser is written once against the JSON-RPC shape; only the transport-level framing (newline-delimited for stdio, event blocks for SSE) is transport-specific.
- **Hash-on-connect** — every `tools/list` response is hashed at first connection and re-verified on every subsequent session for rug-pull defense.

## Related skills

- [mcp-frame-inspector](../.agents/skills/mcp-frame-inspector/SKILL.md) — frame parsing and rug-pull hashing rules
- [multi-tenant-docker-isolation](../.agents/skills/multi-tenant-docker-isolation/SKILL.md) — one container per tenant
