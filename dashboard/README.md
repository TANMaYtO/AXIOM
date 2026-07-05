# dashboard/

Next.js control pane — **later phase, not v1.**

## Responsibility (planned)

- **Central Control Pane** — real-time DevTools-style MCP message stream
- **Tool-call dependency trees** — visual graph of which calls triggered which downstream calls
- **Latency and token-cost breakdowns** per call
- **Compliance-log export** — CSV/JSON-Lines for enterprise audit tooling
- **Advanced Debugging Suite** — mock identities, server isolation, byte-for-byte replay, live schema testing

## Design principles

- Every piece of information must be traceable to a specific intercepted frame
- Raw message stream first, "smart summary" as an optional layer — never replace the real data
- Never silently drop or truncate large payloads without a clear expand affordance

## Related skills

- [postman-for-mcp-devex](../.agents/skills/postman-for-mcp-devex/SKILL.md) — full UX specification
