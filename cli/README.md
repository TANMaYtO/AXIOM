# cli/

AXIOM CLI — zero-config entry point.

## Responsibility

- Provide the primary user-facing entry point for the AXIOM proxy
- Auto-discover existing MCP server configurations across major clients
- Zero-friction install (targeting `npx axiom-mcp-proxy` or `pip install axiom`)
- Surface the debugging suite and control pane features via terminal UI

## Design goal

Match the adoption pattern that already worked for `mcp-scan`:
one command, zero configuration, auto-discovers your existing MCP setup.

## Related skills

- [postman-for-mcp-devex](../.agents/skills/postman-for-mcp-devex/SKILL.md) — DevEx conventions for CLI output
