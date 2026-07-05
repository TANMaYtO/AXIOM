"""AXIOM Proxy — MCP protocol interception and forwarding layer.

Terminates agent-facing connections, forwards/blocks/rewrites traffic
to real MCP server(s), and mirrors every frame to the analysis layer.
Supports both stdio and SSE transports.
"""
