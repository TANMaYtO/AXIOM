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

    sse_parser = subparsers.add_parser(
        "sse-proxy",
        help="Launch AXIOM as an SSE pass-through proxy in front of a remote MCP server.",
    )
    sse_parser.add_argument(
        "--target",
        required=True,
        help="Target remote MCP server SSE URL (e.g., http://localhost:8000/sse).",
    )
    sse_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Local port for AXIOM SSE proxy server to listen on (default: 8080).",
    )
    sse_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Local host interface to bind (default: 127.0.0.1).",
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
    elif parsed_args.command == "sse-proxy":
        import uvicorn
        from proxy.sse import create_sse_proxy_app

        app = create_sse_proxy_app(target_url=parsed_args.target)
        config = uvicorn.Config(
            app, host=parsed_args.host, port=parsed_args.port, log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        return 0
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
