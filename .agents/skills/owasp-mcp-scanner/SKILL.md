---
name: owasp-mcp-scanner
description: Implements security detection rules mapped to the OWASP MCP Top 10 framework, including token mismanagement, tool poisoning, supply chain risks, intent flow subversion, insufficient authentication, shadow servers, and confused deputy patterns. Use when writing or reviewing any code in the security_engine directory, or any task involving detecting malicious or risky MCP behavior.
---

# OWASP MCP Scanner

## When this applies
Any task that adds, modifies, or reviews a security detection rule; anything in `/security_engine`; any request that mentions vulnerabilities, malicious tools, prompt injection, or MCP-specific attack patterns.

## The mapping (use these exact category names — this is what makes the engine auditable)

| Category | What to detect | How |
|---|---|---|
| **MCP01 — Token Mismanagement & Secret Exposure** | Hardcoded credentials, long-lived tokens, secrets surfacing in logs or model context | Pattern-scan every intercepted frame for credential-shaped strings (API key formats, JWT structure, connection strings) before anything is persisted. Redact, don't just flag. |
| **MCP03 — Tool Poisoning** | Hidden instructions embedded in tool names, descriptions, or input schemas | Real-time content inspection of every `tools/list` response against a maintained pattern library of injection/jailbreak phrasing (e.g., instructions embedded in a description telling the model to read unrelated files). Run this at the proxy layer on every connection, not only at install time. |
| **MCP04 — Software Supply Chain & Dependency Tampering** | Compromised or typosquatted MCP server packages | Version pinning, checksum verification, package-name similarity checks (edit-distance against known-good registry names) before trusting a new server. |
| **MCP06 — Intent Flow Subversion** | Prompt injection arriving via a tool description, a tool response, or a fetched document that hijacks the agent's reasoning mid-chain | Content inspection at *every* context-entry point — not just the initial tool list. This is the highest-frequency real-world attack vector; do not treat it as covered just because MCP03's tool-list scan exists. A tool's *response* content needs the same scrutiny as its description. |
| **MCP07 — Insufficient Authentication & Authorization** | Servers/tools that don't verify identity or enforce access boundaries properly | OAuth 2.1 scope auditing — flag any token requesting broader access than its declared task requires. |
| **Audit & Logging Gaps** | Tool invocations that go unrecorded | Full-parameter, full-context, timestamped logging of every call, structured for direct SIEM ingestion. This is what makes every other category's detections *provable* after the fact. |

## Named risks beyond the numbered categories — still required
- **Shadow MCP server discovery** — surface unsanctioned servers running inside an org's network (the MCP-era equivalent of Shadow IT / shadow SaaS discovery).
- **Confused deputy pattern** — flag when a server acts with its own broad privileges instead of the requesting user's actual scope.
- **Tool-shadowing / cross-origin escalation** — flag when one server's tool description references or attempts to modify another server's tools (this exploits the fact that all connected servers share one flat model context).
- **Sandbox-escape containment** — for local servers, recommend Landlock + seccomp + network namespace isolation on Linux, `sandbox-exec` on macOS. This engine doesn't sandbox by itself, but it must flag servers running without any sandboxing present.

## Rule of thumb for new detections
If you're adding a new check and it doesn't fit one of the categories above, don't force it into one — flag it explicitly as "uncategorized, proposed new risk" in both the code comment and any user-facing docs. Silently inventing a parallel taxonomy instead of extending the real OWASP one is what makes a security product's claims impossible to audit — see the AGENT.md non-negotiable rule #5.

## What NOT to do
- Don't claim MCP06 coverage if you've only scanned tool *descriptions* — tool *responses* are a separate, equally real injection surface.
- Don't build a check that duplicates what `mcp-scan` already does statically (see AGENT.md rule #4) — every check here should assume it's running continuously against live traffic, not once at install time.
- Don't skip the "why it might be a false positive" note in a detection's output — a security tool that cries wolf constantly gets its alerts ignored, which defeats the entire point.
