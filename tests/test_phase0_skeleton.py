"""Pytest verification suite for AXIOM Phase 0 Walking Skeleton."""

import asyncio
import json
import sys
from typing import Any, Dict

import pytest


async def send_and_receive(
    proc: asyncio.subprocess.Process, req: Dict[str, Any]
) -> Dict[str, Any]:
    """Send a JSON-RPC request to the proxy process and await the response.

    Args:
        proc: The running proxy subprocess.
        req: The JSON-RPC request dictionary to send.

    Returns:
        The parsed JSON-RPC response dictionary received from stdout.
    """
    assert proc.stdin is not None
    assert proc.stdout is not None

    req_str = json.dumps(req) + "\n"
    proc.stdin.write(req_str.encode("utf-8"))
    await proc.stdin.drain()

    resp_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
    resp_str = resp_bytes.decode("utf-8", errors="replace").strip()
    return json.loads(resp_str)  # type: ignore[no-any-return]


@pytest.mark.asyncio
async def test_phase0_walking_skeleton() -> None:
    """Verify that AXIOM transparently proxies MCP stdio traffic and logs frames."""
    cmd = [
        sys.executable,
        "-m",
        "cli.main",
        "dev-run",
        "--",
        sys.executable,
        "-m",
        "tests.dummy_server",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        # 1. Test initialize
        init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp1 = await send_and_receive(proc, init_req)
        assert resp1["id"] == 1
        assert resp1["result"]["serverInfo"]["name"] == "dummy-test-server"

        # 2. Test tools/list
        list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp2 = await send_and_receive(proc, list_req)
        assert resp2["id"] == 2
        assert len(resp2["result"]["tools"]) == 1
        assert resp2["result"]["tools"][0]["name"] == "echo"

        # 3. Test tools/call
        call_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "Hello AXIOM Phase 0!"},
            },
        }
        resp3 = await send_and_receive(proc, call_req)
        assert resp3["id"] == 3
        assert resp3["result"]["content"][0]["text"] == "Echo: Hello AXIOM Phase 0!"

    finally:
        if proc.stdin is not None:
            proc.stdin.close()

    exit_code = await asyncio.wait_for(proc.wait(), timeout=5.0)
    assert exit_code == 0

    assert proc.stderr is not None
    stderr_bytes = await proc.stderr.read()
    stderr_text = stderr_bytes.decode("utf-8", errors="replace")

    # Verify frame inspection logs appeared on stderr
    assert "[AXIOM FRAME] Client -> Server" in stderr_text
    assert "[AXIOM FRAME] Server -> Client" in stderr_text
    assert "method='initialize' id=1" in stderr_text
    assert "method='tools/list' id=2" in stderr_text
    assert "method='tools/call' id=3" in stderr_text
    assert "Hello AXIOM Phase 0!" in stderr_text
