# AGENT.md — AXIOM

## What this project is

AXIOM is the telemetry, proxy, and perimeter security layer for systems built on the Model Context Protocol (MCP). It sits transparently inside the standard MCP chain — User ↔ MCP Host ↔ MCP Client ↔ MCP Server(s) ↔ Tools/Data/APIs — intercepting every message in both directions without requiring the agent framework or the MCP server to know it's there.

The one-line pitch: **Datadog for MCP traffic, with a security engine mapped to the OWASP MCP Top 10 built in.**

## Why this project exists (don't lose this framing)

Traditional observability (Datadog, OpenTelemetry, Postman) was built for a world where the developer controls the schema and the API surface is fixed at compile time. MCP inverts that: the agent discovers tools at runtime, from any server it's been pointed at, and a third party — the server author, not the application developer — controls what context and instructions the model actually sees. That structural blindness is the whole reason AXIOM exists. Every architectural decision should trace back to closing that blindness, not to generic "add more logging" instincts.

## Non-negotiable rules

1. **Never log raw secrets.** Any credential, token, or key pattern detected in intercepted traffic gets redacted before it touches persistent storage — not after. This is MCP01 (Token Mismanagement & Secret Exposure) and it is the single most embarrassing bug this product could ship.
2. **Multi-tenant isolation is not optional, ever.** Every customer's proxy instance runs in its own isolated Docker container. Never share process memory, never share a message store table without a tenant-scoped key, never take a shortcut here even in a prototype — a security product with a tenant-isolation bug is a company-ending bug, not just a regular one.
3. **Hash `tools/list` responses at first connection, re-verify on every subsequent session.** This is the entire defense against rug-pull attacks (a tool description changing after a user already approved it). If you build a feature that touches tool schemas, it must integrate with this hash-verification path, not bypass it.
4. **Don't rebuild what `mcp-scan` already does well.** `mcp-scan` (Invariant Labs) is a good, free, static/install-time scanner. AXIOM's differentiation is continuous, runtime, proxy-level inspection — the layer *above* the static scanners, the same relationship Datadog has to raw log files. If a feature only re-implements static scanning, it's off-thesis.
5. **Every security check maps to a named category.** Reference the OWASP MCP Top 10 (`.agents/skills/owasp-mcp-scanner/SKILL.md`) explicitly in code comments and commit messages — e.g. `# MCP06 — Intent Flow Subversion check`. This keeps the security engine auditable and keeps marketing/docs honest about what's actually covered.

## Tech stack (do not deviate without a real reason)

- **Backend:** FastAPI, async-first — MCP's `stdio` and SSE transports are long-lived streaming connections; a synchronous framework will serialize what needs to stay concurrent.
- **Isolation:** Docker, one container per tenant.
- **Retrieval/audit layer:** FAISS + sentence-transformers, indexing tool schema embeddings and historical call patterns (direct continuation of the retrieval pattern already proven in PRISM).
- **Analytics/message store:** ClickHouse for scale, SQLite for local/dev mode.
- **Dashboard (later phase):** Next.js, matching the Cronus/PRISM frontend conventions already established.
- **Distribution:** open-source CLI (`npx axiom-mcp-proxy` style), zero-config install matching the adoption pattern that already worked for `mcp-scan`.

## Architecture summary

```
Agent Framework (LangGraph / CrewAI / AutoGen / direct)
        │
        ▼
   AXIOM Proxy  ──mirrors every frame──▶  Analysis + Storage (FAISS index, ClickHouse/SQLite)
        │                                          │
        ▼                                          ▼
  Real MCP Server(s)                    Security Engine (OWASP MCP Top 10 checks)
```

The proxy terminates the agent-facing connection, forwards/blocks/rewrites traffic to the real MCP server(s), and mirrors every frame to the analysis layer. Think API gateway / service-mesh sidecar, adapted for a protocol where the "requests" are JSON-RPC calls a model chose to make rather than calls a developer coded.

## Repo layout to use

```
/proxy            — FastAPI proxy, transport handling (stdio + SSE), frame interception
/security_engine  — OWASP MCP Top 10 detection rules, pattern library
/retrieval         — FAISS index, embedding generation, drift-detection queries
/storage           — ClickHouse/SQLite message store, tenant-scoped schema
/cli                — the npx-installable entry point
/dashboard         — Next.js control pane (later phase, not v1)
```

## Skills available in this project

Skills auto-load based on semantic match to your request — you shouldn't need to invoke them by name, but for reference:

- `mcp-frame-inspector` — JSON-RPC 2.0 parsing over stdio/SSE, tool-schema hashing/rug-pull detection
- `owasp-mcp-scanner` — the full OWASP MCP Top 10 mapping and detection heuristics
- `multi-tenant-docker-isolation` — container-per-tenant rules, what "isolated" actually means here
- `faiss-tool-schema-indexing` — the retrieval/audit layer, reusing PRISM's proven pattern
- `postman-for-mcp-devex` — the debugging suite / control pane UX conventions

## Definition of done for any feature

A feature isn't done until: (1) it works under multi-tenant isolation without exception, (2) any new security check is mapped to a named OWASP MCP category or explicitly flagged as a new, uncategorized risk, (3) nothing it does could be replaced by running `mcp-scan` once — if it could, it's not differentiated enough to ship.
