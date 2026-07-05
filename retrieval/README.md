# retrieval/

FAISS-backed semantic search and drift-detection layer.

## Responsibility

- Generate embeddings (via sentence-transformers) for tool schemas, call patterns, and session context
- Maintain a local FAISS index — no hosted vector DB dependency
- Support cosine/L2 similarity queries for drift detection, anomaly flagging, and audit lookups
- Re-embed and re-index on schema change (integrated with rug-pull hash-check flow)

## What gets indexed

- **Tool schema embeddings** — every `tools/list` entry, keyed by server identity
- **Historical call patterns** — argument shapes and frequency per tool
- **Session context summaries** — for the debugging suite to answer "show me sessions similar to this one"

## Design constraints

- Keep embedding + query on the hot path fast — queue and process async if it would block frame forwarding
- Never index raw secrets or unredacted tool arguments (MCP01 applies here too)
- Keep everything local/self-hosted — no external vector DB without a real reason

## Related skills

- [faiss-tool-schema-indexing](../.agents/skills/faiss-tool-schema-indexing/SKILL.md) — indexing rules and PRISM heritage
