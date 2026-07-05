"""Async bidirectional stdio pass-through proxy for AXIOM."""

import asyncio
import logging
import sys
import threading
from typing import List

from proxy.parser import inspect_and_log_frame

logger = logging.getLogger("axiom.proxy.stdio")


async def run_stdio_proxy(server_cmd: List[str]) -> int:
    """Run an asynchronous stdio pass-through proxy in front of a target MCP server.

    Args:
        server_cmd: Command list to execute the target MCP server subprocess.

    Returns:
        The exit code of the target MCP server subprocess.
    """
    if not server_cmd:
        sys.stderr.write("[AXIOM ERROR] No server command provided to proxy.\n")
        sys.stderr.flush()
        return 1

    try:
        proc = await asyncio.create_subprocess_exec(
            *server_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr,
        )
    except Exception as exc:
        sys.stderr.write(
            f"[AXIOM ERROR] Failed to launch server command '{' '.join(server_cmd)}': {exc}\n"
        )
        sys.stderr.flush()
        return 1

    in_queue: asyncio.Queue[str] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def read_stdin_thread() -> None:
        """Read lines from sys.stdin in a daemon thread for OS compatibility."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    loop.call_soon_threadsafe(in_queue.put_nowait, "")
                    break
                loop.call_soon_threadsafe(in_queue.put_nowait, line)
            except Exception as exc:
                logger.error(f"Error reading sys.stdin: {exc}")
                loop.call_soon_threadsafe(in_queue.put_nowait, "")
                break

    async def forward_inbound() -> None:
        """Read from client stdin queue, inspect frame, and write to server stdin."""
        while True:
            line = await in_queue.get()
            if not line:
                if proc.stdin is not None:
                    proc.stdin.close()
                break
            inspect_and_log_frame("Client -> Server", line)
            if proc.stdin is not None:
                proc.stdin.write(line.encode("utf-8"))
                await proc.stdin.drain()

    async def forward_outbound() -> None:
        """Read from server stdout, inspect frame, and write to client stdout."""
        if proc.stdout is None:
            return
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace")
            inspect_and_log_frame("Server -> Client", line)
            sys.stdout.write(line)
            sys.stdout.flush()

    inbound_task = asyncio.create_task(forward_inbound())
    outbound_task = asyncio.create_task(forward_outbound())

    thread = threading.Thread(target=read_stdin_thread, daemon=True)
    thread.start()

    await outbound_task
    inbound_task.cancel()

    exit_code = await proc.wait()
    return exit_code
