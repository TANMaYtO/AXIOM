# AXIOM

<p align="center">
  <strong>Datadog for MCP traffic, with a security engine mapped to the OWASP MCP Top 10 built in.</strong>
</p>

<p align="center">
  <a href="#what-axiom-is">What</a> •
  <a href="#why-now">Why Now</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#security-engine">Security Engine</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#repo-structure">Repo Structure</a>
</p>

---

## What AXIOM Is

AXIOM is the telemetry, proxy, and perimeter security layer for systems built on the **Model Context Protocol (MCP)** — the protocol Anthropic introduced in November 2024 that standardizes how AI agents discover and call external tools, often described as "USB-C for AI."

AXIOM sits transparently inside the standard MCP chain:

```
User ↔ MCP Host ↔ MCP Client ↔ AXIOM Proxy ↔ MCP Server(s) ↔ Tools/Data/APIs
```

It intercepts every message in both directions **without requiring the agent framework or the MCP server to know it's there.**

## Why Now

MCP adoption is not a slow curve — FastMCP alone is downloaded over a million times a day. Every major agent client (Claude Desktop, Cursor, Claude Code, Gemini CLI, Windsurf, ChatGPT) now speaks it. And every one of those integrations inherits the same structural problem:

> Traditional observability tooling — Datadog, OpenTelemetry, Postman — was built for a world where the developer controls the schema and the API surface is fixed at compile time. MCP inverts that entirely.

Between January and February 2026, security researchers filed **30+ CVEs** against MCP infrastructure, 43% of them shell-injection-class. Palo Alto's Unit 42 measured a **78.3% attack success rate** on setups with just five connected MCP servers.

### Core Failure Modes AXIOM Closes

| Failure Mode | What Happens |
|---|---|
| **Tool Poisoning** | A tool named "add" with "Add two numbers" in its description secretly instructs the model to read `~/.ssh/id_rsa` |
| **Rug-Pull Attacks** | Tool descriptions change after user approval — nothing re-prompts for review |
| **Confused Deputy** | MCP servers execute with their own broad privileges instead of the requesting user's scope |
| **Shadow Servers** | Unsanctioned MCP instances spun up by developers, running with default credentials |
| **Silent Data Exfiltration** | Sensitive data encoded into ordinary-seeming tool calls (search queries, email subjects) |

## Architecture

```
Agent Framework (LangGraph / CrewAI / AutoGen / direct)
        │
        ▼
   AXIOM Proxy  ──mirrors every frame──▶  Analysis + Storage (FAISS index, ClickHouse/SQLite)
        │                                          │
        ▼                                          ▼
  Real MCP Server(s)                    Security Engine (OWASP MCP Top 10 checks)
```

- **Proxy:** FastAPI, async-first — MCP's `stdio` and SSE transports are long-lived streaming connections
- **Isolation:** Docker, one container per tenant — genuine security boundary, not shared-process
- **Retrieval:** FAISS + sentence-transformers for tool schema embeddings and call pattern indexing
- **Storage:** ClickHouse for production scale, SQLite for local/dev mode
- **Dashboard:** Next.js control pane (later phase)

## Security Engine

Mapped directly to the **OWASP MCP Top 10** (2025), category by category:

| OWASP Category | What AXIOM Detects |
|---|---|
| **MCP01** — Token Mismanagement | Hardcoded credentials, secrets in logs/model memory → auto-redacted before storage |
| **MCP03** — Tool Poisoning | Hidden instructions in tool names/descriptions/schemas → real-time pattern matching |
| **MCP04** — Supply Chain Tampering | Compromised/typosquatted MCP server packages → checksum + name-similarity checks |
| **MCP06** — Intent Flow Subversion | Prompt injection via tool responses and fetched documents → content inspection at every entry point |
| **MCP07** — Insufficient Auth | Over-scoped OAuth tokens → scope auditing |
| **Audit Gaps** | Unrecorded tool invocations → full-parameter timestamped SIEM-ready logging |

Plus: shadow server discovery, rug-pull/description-drift alerting, tool-shadowing detection, confused-deputy flagging, and sandbox-escape containment guidance.

## Getting Started

> 🚧 **AXIOM is under active development.** The sections below will be updated as components become functional.

```bash
# Clone the repo
git clone https://github.com/TANMaYtO/AXIOM.git
cd AXIOM

# (Coming soon) Install and run
# pip install -e .
# axiom-proxy --config axiom.yaml
```

## Repo Structure

```
proxy/            — FastAPI proxy, transport handling (stdio + SSE), frame interception
security_engine/  — OWASP MCP Top 10 detection rules, pattern library
retrieval/        — FAISS index, embedding generation, drift-detection queries
storage/          — ClickHouse/SQLite message store, tenant-scoped schema
cli/              — CLI entry point and distribution
dashboard/        — Next.js control pane (later phase, not v1)
.agents/          — Agent skills and project rules for AI-assisted development
```

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend | FastAPI (async) | MCP transports are long-lived streaming connections |
| Isolation | Docker | One container per tenant — security boundary, not convenience |
| Retrieval | FAISS + sentence-transformers | Sub-second semantic search, no hosted vector DB needed |
| Message Store | ClickHouse / SQLite | Scale vs. local dev, same interface |
| Dashboard | Next.js | Later phase |
| Distribution | CLI (`npx` / `pip`) | Zero-config install, matching `mcp-scan`'s proven adoption pattern |

## Competitive Positioning

AXIOM is **not** a better static scanner — it's the **continuous, runtime, proxy-level layer** sitting above the scanners. The same relationship Datadog has to a server's raw log files. A team can run `mcp-scan` once a week and still have zero visibility into what actually crossed the wire in production yesterday. That gap is AXIOM's entire business.

## License

MIT

---

<p align="center">
  <sub>Built to close the observability blindspot MCP created.</sub>
</p>
