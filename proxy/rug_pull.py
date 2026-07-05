"""Tool Schema Hashing and Rug-Pull Attack Detector (OWASP MCP03)."""

import asyncio
import hashlib
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("axiom.proxy.rug_pull")


def normalize_and_hash(tools: List[Dict[str, Any]]) -> str:
    """Normalize tool list key ordering and compute a stable SHA-256 hash.

    Args:
        tools: List of tool dictionaries from a tools/list response.

    Returns:
        Hexadecimal SHA-256 hash string of the normalized tool list.
    """
    # Sort tools by name to prevent reordering false positives
    sorted_tools = sorted(tools, key=lambda t: str(t.get("name", "")))
    dumped = json.dumps(sorted_tools, sort_keys=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def compute_schema_diff(
    old_tools: List[Dict[str, Any]], new_tools: List[Dict[str, Any]]
) -> List[str]:
    """Compute human-readable differences between old and new tool schemas.

    Args:
        old_tools: Baseline list of tool dictionaries.
        new_tools: Newly received list of tool dictionaries.

    Returns:
        List of difference description strings.
    """
    old_map = {str(t.get("name", "")): t for t in old_tools}
    new_map = {str(t.get("name", "")): t for t in new_tools}
    diffs: List[str] = []

    for name in old_map:
        if name not in new_map:
            diffs.append(f"Tool '{name}' was removed.")

    for name in new_map:
        if name not in old_map:
            diffs.append(f"Tool '{name}' was added.")
        else:
            old_desc = old_map[name].get("description", "")
            new_desc = new_map[name].get("description", "")
            if old_desc != new_desc:
                diffs.append(
                    f"Tool '{name}' description changed: '{old_desc}' -> '{new_desc}'"
                )

            old_schema = json.dumps(old_map[name].get("inputSchema", {}), sort_keys=True)
            new_schema = json.dumps(new_map[name].get("inputSchema", {}), sort_keys=True)
            if old_schema != new_schema:
                diffs.append(f"Tool '{name}' inputSchema changed.")

    return diffs


class RugPullDetector:
    """Detects tool schema tampering and rug-pull attacks across MCP sessions."""

    def __init__(self, storage_path: str = ".axiom/baselines.json") -> None:
        """Initialize the RugPullDetector.

        Args:
            storage_path: Path to the flat file storing baseline tool schemas.
        """
        self.storage_path = storage_path
        self.locked_servers: Set[str] = set()
        self._lock = asyncio.Lock()

    async def _read_baselines(self) -> Dict[str, Any]:
        """Read baseline schemas asynchronously from disk.

        Returns:
            Dictionary mapping server identities to schema baseline data.
        """
        if not os.path.exists(self.storage_path):
            return {}

        def read_file() -> Dict[str, Any]:
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    return {}
            except Exception as exc:
                logger.error(f"Failed to read baselines from {self.storage_path}: {exc}")
                return {}

        return await asyncio.to_thread(read_file)

    async def _write_baselines(self, baselines: Dict[str, Any]) -> None:
        """Write baseline schemas asynchronously to disk.

        Args:
            baselines: Dictionary mapping server identities to schema baseline data.
        """
        directory = os.path.dirname(self.storage_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        def write_file() -> None:
            try:
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(baselines, f, indent=2, sort_keys=True)
            except Exception as exc:
                logger.error(f"Failed to write baselines to {self.storage_path}: {exc}")

        await asyncio.to_thread(write_file)

    async def evaluate_tools_list(
        self, server_identity: str, tools_list_response: Dict[str, Any]
    ) -> bool:
        """Evaluate a tools/list response against recorded baselines.

        # MCP03 — Tool Poisoning & Rug-Pull Attack check

        Args:
            server_identity: Unique identifier for the target MCP server.
            tools_list_response: The parsed JSON-RPC response dictionary.

        Returns:
            True if schema is valid or newly recorded, False if a rug-pull is detected.
        """
        tools: List[Dict[str, Any]] = (
            tools_list_response.get("result", {}).get("tools", [])
        )
        schema_hash = normalize_and_hash(tools)

        async with self._lock:
            baselines = await self._read_baselines()

            if server_identity not in baselines:
                # First connection: record baseline schema
                baselines[server_identity] = {
                    "hash": schema_hash,
                    "tools": tools,
                }
                await self._write_baselines(baselines)
                sys.stderr.write(
                    f"[AXIOM SECURITY] Recorded baseline schema for '{server_identity}' "
                    f"(hash: {schema_hash[:8]})\n"
                )
                sys.stderr.flush()
                return True

            old_hash = baselines[server_identity].get("hash")
            if schema_hash == old_hash:
                return True

            # Rug-Pull detected! # MCP03 — Rug-Pull Attack check
            old_tools = baselines[server_identity].get("tools", [])
            diffs = compute_schema_diff(old_tools, tools)
            diff_str = "\n    - ".join(diffs) if diffs else "Unknown schema change."

            alert_msg = (
                f"\n[AXIOM SECURITY ALERT] # MCP03 — Tool Poisoning / Rug-Pull Attack Detected!\n"
                f"Server identity '{server_identity}' changed tool schema since initial verification!\n"
                f"Differences detected:\n    - {diff_str}\n"
                f"Why it might be a false positive: The server developer may have legitimately "
                f"upgraded tool definitions without updating the recorded baseline.\n"
                f"Action: Subsequent tools/call requests to this server will be blocked.\n\n"
            )
            sys.stderr.write(alert_msg)
            sys.stderr.flush()

            self.locked_servers.add(server_identity)
            return False

    def is_call_blocked(self, server_identity: str) -> bool:
        """Check if tool calls to the specified server identity are blocked.

        # MCP03 — Rug-Pull Attack check

        Args:
            server_identity: Unique identifier for the target MCP server.

        Returns:
            True if calls are blocked due to rug-pull detection, else False.
        """
        return server_identity in self.locked_servers
