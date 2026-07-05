---
name: faiss-tool-schema-indexing
description: Builds and queries the FAISS-backed semantic retrieval layer that indexes MCP tool schema embeddings, historical call patterns, and session context for drift detection and rapid auditing. Use when working on the retrieval directory, embedding generation, or any feature that needs to answer "has this tool's behavior changed" or "have we seen a call pattern like this before" as a semantic query.
---

# FAISS Tool-Schema Indexing

## When this applies
Any task in `/retrieval`; anything involving embedding generation for tool schemas or call history; any feature framed as "find similar past X" where X is a tool description, a call pattern, or a session.

## Reuse the proven pattern — don't reinvent it
This is a direct continuation of the AST-plus-FAISS retrieval architecture already shipped and benchmarked in PRISM (32.74% precision / 47.72% recall / 33.22% F1 across 19 real PRs). The core pattern that already works:

1. Generate embeddings via sentence-transformers over the structured object being indexed (in PRISM: function signatures and call edges; here: tool schemas, call argument patterns, session summaries).
2. Store in a local FAISS index — no need for a hosted vector DB at this stage; local FAISS is what kept PRISM's retrieval "under 5 seconds, zero LLM extraction overhead," and the same constraint applies here.
3. Query via cosine/L2 similarity search, not via an LLM call — the entire value of this layer is that it's deterministic and fast, not that it's "smart." If a query needs an LLM to interpret the result, that's a downstream step, not part of this skill.

## What gets indexed here specifically
- **Tool schema embeddings** — every `tools/list` entry seen, embedded and indexed by server identity. This is what lets `mcp-frame-inspector`'s hash-based rug-pull check be supplemented with a semantic one: "this new description is suspiciously similar to a known-malicious pattern we've indexed before," not just "the hash changed."
- **Historical call patterns** — argument shapes and frequency per tool, so a call that's semantically unlike anything seen before for that tool can be flagged as anomalous even if it isn't a hash mismatch.
- **Session context summaries** — for the audit/debugging suite (`postman-for-mcp-devex`) to answer "show me sessions similar to this one" quickly.

## Rules
- Keep embedding generation and FAISS querying in the hot path fast — this layer exists to make the security engine and the debugging suite feel instant, not to become its own bottleneck. If an embedding call would block the proxy's frame-forwarding path, move it off the critical path (queue it, process async) rather than slowing down live traffic.
- Re-embed and re-index on schema change (tie this into the rug-pull hash-check flow) — don't let the index silently go stale relative to what `mcp-frame-inspector` has already detected as changed.
- Keep the index local/self-hosted by default, consistent with AXIOM's "runs entirely in your infrastructure" positioning against hosted competitors — don't introduce an external vector DB dependency without a real, discussed reason.

## What NOT to do
- Don't use an LLM call to do what a similarity search can do — that reintroduces the latency and cost overhead this architecture is specifically designed to avoid.
- Don't index raw secrets or unredacted tool arguments — this index is subject to the same MCP01 (secret exposure) rule as everything else; redact before embedding, not after.
