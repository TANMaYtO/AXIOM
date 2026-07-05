---
name: multi-tenant-docker-isolation
description: Defines the rules for per-tenant Docker container isolation in the AXIOM proxy backend, covering process isolation, storage scoping, and secret handling across tenants. Use when writing deployment code, provisioning logic, database schemas, or anything where two different customers' data or traffic could interact.
---

# Multi-Tenant Docker Isolation

## When this applies
Any task touching: container provisioning, the message store schema, secret storage, or any code path where more than one customer's data passes through the same process.

## Why this skill exists
AXIOM is a security product. A tenant-isolation bug in a security product isn't a normal bug — it's a "the product's entire premise just failed" bug. Treat every shortcut here as categorically different from a shortcut in, say, a UI polish task.

## Rules

1. **One container per tenant, always.** Never share a running proxy process between two customers, even temporarily, even in a demo, even in local dev if the dev setup will inform production code paths.
2. **No shared process memory.** If you're tempted to cache something "just for this session" in a way that isn't explicitly keyed by tenant ID, stop — that's exactly how cross-tenant data leaks happen.
3. **Every storage table is tenant-scoped.** Every row in the message store, the FAISS index metadata, and the audit log must carry a tenant ID as part of its primary lookup path — not as an afterthought filter applied at query time. Query-time filtering that could be forgotten by a future developer is not isolation; schema-level scoping is.
4. **Secrets never cross the tenant boundary.** A customer's Apify/GitHub/API tokens, or anything captured from their MCP traffic, must be encrypted at rest and scoped to that tenant's container/storage only. Follow the same pattern already proven in Cronus (Supabase Row-Level Security + AES-256-GCM token encryption) — don't invent a new pattern when a working one already exists in the portfolio.
5. **Isolation is a build-time property, not a runtime check.** Prefer architectures where cross-tenant access is *structurally impossible* (separate containers, separate encryption keys) over architectures where it's merely *checked against* at request time. Checks can have bugs; structural separation can't be bypassed by a missed `if`.

## Testing expectation
Any PR touching provisioning or storage should include a test that explicitly tries to read another tenant's data through the code path being changed, and asserts it fails. If that test doesn't exist for a given change, the change isn't done.

## What NOT to do
- Don't add a "trusted internal" bypass path that skips tenant scoping "just for AXIOM's own admin dashboard" — build the admin dashboard to go through the same scoped access path everyone else does.
- Don't defer isolation to "add later once the feature works" — retrofitting isolation onto code that assumed a shared process is far harder than building it in from the first line.
