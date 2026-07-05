"""Minimal local MCP test server over stdio for verifying AXIOM Phase 0."""

import json
import sys
from typing import Any, Dict, Optional


def handle_request(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process an inbound JSON-RPC request and return an appropriate response.

    Args:
        message: The parsed JSON-RPC request dictionary.

    Returns:
        A JSON-RPC response dictionary, or None if the message is a notification.
    """
    msg_id = message.get("id")
    method = message.get("method", "")
    params = message.get("params", {})

    sys.stderr.write(f"[DUMMY SERVER] Handling method='{method}' id={msg_id}\n")
    sys.stderr.flush()

    if msg_id is None:
        # It's a notification (e.g., notifications/initialized)
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "dummy-test-server", "version": "0.1.0"},
            },
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echoes back the input message.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}},
                            "required": ["message"],
                        },
                    }
                ]
            },
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if tool_name == "echo":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Echo: {arguments.get('message', '')}",
                        }
                    ]
                },
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


def main() -> None:
    """Run the dummy MCP server loop reading stdin and writing stdout."""
    sys.stderr.write("[DUMMY SERVER] Starting stdio loop...\n")
    sys.stderr.flush()

    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            req = json.loads(stripped)
            if isinstance(req, dict):
                resp = handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
        except Exception as exc:
            sys.stderr.write(f"[DUMMY SERVER ERROR] {exc}\n")
            sys.stderr.flush()

    sys.stderr.write("[DUMMY SERVER] Exiting stdio loop.\n")
    sys.stderr.flush()


if __name__ == "__main__":
    main()
