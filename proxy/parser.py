"""Shared JSON-RPC 2.0 frame parser and inspection utilities for AXIOM proxy."""

import json
import logging
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger("axiom.proxy.parser")


def parse_jsonrpc_frame(raw_str: str) -> Optional[Dict[str, Any]]:
    """Parse a raw text line into a JSON-RPC 2.0 frame dictionary if valid.

    Args:
        raw_str: The raw string read from transport.

    Returns:
        The parsed JSON dictionary if it is a valid JSON-RPC 2.0 message, else None.
    """
    stripped = raw_str.strip()
    if not stripped:
        return None
    try:
        data = json.loads(stripped)
        if isinstance(data, dict) and data.get("jsonrpc") == "2.0":
            return data
    except json.JSONDecodeError:
        pass
    return None


def inspect_and_log_frame(direction: str, raw_str: str) -> None:
    """Inspect an intercepted transport line and print formatted frame to stderr.

    Args:
        direction: Direction label (e.g., 'Client -> Server' or 'Server -> Client').
        raw_str: The raw text line intercepted on the transport.
    """
    stripped = raw_str.strip()
    if not stripped:
        return

    frame = parse_jsonrpc_frame(stripped)
    if frame is not None:
        # Extract summary details for cleaner debugging
        msg_id = frame.get("id")
        method = frame.get("method")
        if method:
            summary = f"method='{method}' id={msg_id}"
        elif "result" in frame:
            summary = f"result id={msg_id}"
        elif "error" in frame:
            summary = f"error id={msg_id}"
        else:
            summary = f"notification id={msg_id}"

        log_message = f"[AXIOM FRAME] {direction} ({summary}): {stripped}\n"
    else:
        log_message = f"[AXIOM RAW] {direction}: {stripped}\n"

    sys.stderr.write(log_message)
    sys.stderr.flush()


async def check_inbound_frame(
    raw_str: str, server_identity: str, detector: Any
) -> Optional[str]:
    """Inspect client->server frame and check if tools/call is blocked by rug-pull defense.

    # MCP03 — Rug-Pull Attack check

    Args:
        raw_str: The raw JSON-RPC string sent from client.
        server_identity: Unique identity string of the target server.
        detector: The RugPullDetector instance.

    Returns:
        JSON-RPC error response string if blocked, or None if allowed.
    """
    inspect_and_log_frame("Client -> Server", raw_str)
    frame = parse_jsonrpc_frame(raw_str)
    if frame is not None and frame.get("method") == "tools/call":
        if detector.is_call_blocked(server_identity):
            err_resp = {
                "jsonrpc": "2.0",
                "id": frame.get("id"),
                "error": {
                    "code": -32000,
                    "message": (
                        f"[AXIOM SECURITY ALERT] OWASP MCP03 (Rug-Pull Attack Detected): "
                        f"Tool calls to '{server_identity}' are blocked due to schema tampering!"
                    ),
                },
            }
            err_line = json.dumps(err_resp) + "\n"
            inspect_and_log_frame("Server -> Client [AXIOM BLOCKED]", err_line)
            return err_line
    return None


async def check_outbound_frame(
    raw_str: str, server_identity: str, detector: Any
) -> None:
    """Inspect server->client frame and evaluate tools/list responses for schema tampering.

    # MCP03 — Tool Poisoning / Rug-Pull Attack check

    Args:
        raw_str: The raw JSON-RPC string sent from server.
        server_identity: Unique identity string of the target server.
        detector: The RugPullDetector instance.
    """
    inspect_and_log_frame("Server -> Client", raw_str)
    frame = parse_jsonrpc_frame(raw_str)
    if frame is not None:
        result = frame.get("result")
        if isinstance(result, dict) and "tools" in result:
            await detector.evaluate_tools_list(server_identity, frame)

