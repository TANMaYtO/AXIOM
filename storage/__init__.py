"""AXIOM Storage — Tenant-scoped message store and audit log.

ClickHouse for production scale, SQLite for local/dev mode.
Every table is tenant-scoped at the schema level — isolation is
a build-time property, not a runtime check.
"""
