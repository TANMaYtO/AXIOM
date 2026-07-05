---
name: postman-for-mcp-devex
description: Defines UX and functional conventions for AXIOM's Central Control Pane and Advanced Debugging Suite — the "Postman for MCP" developer experience, including message stream inspection, tool-call dependency trees, replay, and mock identity testing. Use when building CLI output, the dashboard, or any developer-facing debugging feature.
---

# Postman-for-MCP DevEx

## When this applies
Any task in `/cli` or `/dashboard`; anything framed as a developer-facing debugging or inspection feature, as opposed to a backend security/proxy feature.

## The core positioning to hold onto
AXIOM's DevEx should feel like opening Chrome DevTools' Network tab, not like reading a log file. The bar is: a developer should be able to answer "why did this agent call this tool with these arguments, and what happened downstream" in seconds, without grepping anything.

## Required capabilities (the Central Control Pane)
- **Real-time message stream** — every MCP message crossing the proxy, in order, as it happens. Not a delayed batch view.
- **Tool-call dependency trees** — when one tool call triggers another (multi-agent fan-out), show this as a tree/graph, not a flat chronological list. Flat lists are how you lose track of which call caused which downstream effect — exactly the "silent multi-agent chain failure" problem AXIOM exists to solve.
- **Latency and token-cost breakdown per call** — always attach cost/performance data to the message it belongs to, never as a separate disconnected report.
- **Compliance-log export** — formatted for direct ingestion into whatever audit tooling an enterprise customer already has; don't invent a proprietary export format when CSV/JSON-Lines will do.

## Required capabilities (the Advanced Debugging Suite — "Postman for MCP")
- **Mock agent identities** — let a developer simulate being a specific agent/user without needing a real credential for it.
- **Isolate one server's state** — a developer debugging server A shouldn't have to also reason about servers B and C's state at the same time.
- **Byte-for-byte replay** — a failed tool call must be reproducible exactly, not approximately. If replay changes even whitespace in the original request, it's not real replay.
- **Live schema testing** — let a developer test a schema change against real historical traffic (pulled from the FAISS-indexed history) before shipping it, not just against synthetic examples.

## Design rule
Every piece of information shown in the dashboard or CLI should be traceable back to a specific intercepted frame. If a feature can't point to "this came from this exact message at this exact timestamp," it's summarizing instead of showing — and summarizing is exactly the "silent failure" mode AXIOM is supposed to eliminate, not reproduce in its own UI.

## What NOT to do
- Don't build a "smart summary" view as the default — offer it as an optional layer on top of the raw, complete stream, never as a replacement for it.
- Don't let the dashboard silently drop or truncate large payloads without a clear affordance to expand/view the full content — a debugging tool that hides the thing you're debugging has failed at its one job.
