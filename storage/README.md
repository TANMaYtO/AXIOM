# storage/

Tenant-scoped message store and audit log.

## Responsibility

- Persist every intercepted MCP frame with full parameters, context, and timestamps
- Enforce tenant-level isolation at the schema level (not query-time filtering)
- Support two backends: ClickHouse (production) and SQLite (local/dev)
- Structure logs for direct SIEM ingestion
- Encrypt secrets at rest, scoped per tenant

## Design constraints

- Every table carries tenant ID as part of its primary lookup path
- Secrets are encrypted with per-tenant keys (AES-256-GCM, following the Cronus pattern)
- No "trusted internal" bypass that skips tenant scoping
- Query-time filtering alone is NOT considered isolation

## Related skills

- [multi-tenant-docker-isolation](../.agents/skills/multi-tenant-docker-isolation/SKILL.md) — isolation rules and testing expectations
