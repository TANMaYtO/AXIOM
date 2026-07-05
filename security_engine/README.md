# security_engine/

OWASP MCP Top 10 detection rules and pattern library.

## Responsibility

- Implement runtime security checks mapped to each OWASP MCP Top 10 category
- Maintain a pattern library for injection/jailbreak phrase detection
- Run continuous content inspection on live traffic (not just install-time)
- Flag detections with exact OWASP category references for auditability

## Coverage matrix

| Category | Status |
|---|---|
| MCP01 — Token Mismanagement & Secret Exposure | 🔲 Planned |
| MCP03 — Tool Poisoning | 🔲 Planned |
| MCP04 — Supply Chain & Dependency Tampering | 🔲 Planned |
| MCP06 — Intent Flow Subversion | 🔲 Planned |
| MCP07 — Insufficient Authentication & Authorization | 🔲 Planned |
| Audit & Logging Gaps | 🔲 Planned |
| Shadow Server Discovery | 🔲 Planned |
| Confused Deputy Pattern | 🔲 Planned |
| Tool-Shadowing / Cross-Origin Escalation | 🔲 Planned |
| Sandbox-Escape Containment | 🔲 Planned |

## Related skills

- [owasp-mcp-scanner](../.agents/skills/owasp-mcp-scanner/SKILL.md) — full detection rule specifications
