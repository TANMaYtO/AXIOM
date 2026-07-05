"""Command-line interface entry point for AXIOM."""

import argparse
import asyncio
import logging
import sys
from typing import List, Optional

from proxy.stdio import run_stdio_proxy


def setup_logging() -> None:
    """Configure basic logging for AXIOM CLI to stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argparse command-line parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="axiom",
        description="AXIOM — Telemetry, proxy, and perimeter security for MCP.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    dev_run_parser = subparsers.add_parser(
        "dev-run",
        help="Launch AXIOM as a pass-through proxy in front of a local MCP server.",
    )
    dev_run_parser.add_argument(
        "server_cmd",
        nargs=argparse.REMAINDER,
        help="Target server command and arguments (e.g., -- python -m my_server).",
    )
    return parser


async def async_main(args: Optional[List[str]] = None) -> int:
    """Async entry point for executing CLI commands.

    Args:
        args: Optional list of command-line arguments.

    Returns:
        Process exit code.
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if parsed_args.command == "dev-run":
        server_cmd = parsed_args.server_cmd or []
        if server_cmd and server_cmd[0] == "--":
            server_cmd = server_cmd[1:]
        if not server_cmd:
            sys.stderr.write(
                "[AXIOM ERROR] Please provide a server command: axiom dev-run -- <cmd>\n"
            )
            sys.stderr.flush()
            return 1
        return await run_stdio_proxy(server_cmd)
    else:
        parser.print_help(file=sys.stderr)
        return 1


def main() -> None:
    """Synchronous main entry point for CLI script invocation."""
    setup_logging()
    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.stderr.write("[AXIOM] Proxy terminated by user.\n")
        sys.stderr.flush()
        sys.exit(0)


if __name__ == "__main__":
    main()
