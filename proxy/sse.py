"""Async Server-Sent Events (SSE) transport proxy for AXIOM."""

import asyncio
from contextlib import asynccontextmanager
import json
import logging
import sys
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import parse_qs, urljoin, urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
import httpx

from proxy.parser import check_inbound_frame, check_outbound_frame
from proxy.rug_pull import RugPullDetector

logger = logging.getLogger("axiom.proxy.sse")


def create_sse_proxy_app(
    target_url: str,
    detector: Optional[RugPullDetector] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> FastAPI:
    """Create a FastAPI application acting as an MCP SSE pass-through proxy.

    # MCP03 — Tool Poisoning / Rug-Pull Attack check

    Args:
        target_url: Target MCP server SSE endpoint URL.
        detector: Optional RugPullDetector instance for schema verification.
        client: Optional HTTPX AsyncClient for custom transport or in-memory testing.

    Returns:
        FastAPI application instance configured for SSE proxying.
    """
    if detector is None:
        detector = RugPullDetector()

    server_identity = f"sse:{target_url}"
    session_map: Dict[str, str] = {}
    if client is None:
        client = httpx.AsyncClient(timeout=None)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage application lifecycle and HTTPX client cleanup."""
        yield
        await client.aclose()

    app = FastAPI(title="AXIOM SSE Proxy", lifespan=lifespan)


    @app.get("/sse")
    async def sse_endpoint(request: Request) -> StreamingResponse:
        """Proxy SSE stream from target MCP server to client."""

        async def event_generator() -> AsyncGenerator[str, None]:
            """Stream events from target server, inspecting frames and rewriting endpoints."""
            try:
                async with client.stream(
                    "GET", target_url, headers={"Accept": "text/event-stream"}
                ) as resp:
                    buffer = ""
                    async for chunk in resp.aiter_text():
                        if await request.is_disconnected():
                            break
                        buffer += chunk
                        while "\n\n" in buffer:
                            event_block, buffer = buffer.split("\n\n", 1)
                            lines = event_block.split("\n")
                            event_type = "message"
                            data_lines = []
                            for line in lines:
                                if line.startswith("event: "):
                                    event_type = line[7:].strip()
                                elif line.startswith("data: "):
                                    data_lines.append(line[6:])

                            data_str = "\n".join(data_lines)
                            if event_type == "endpoint":
                                # Resolve target post URL and rewrite for client
                                real_post_url = urljoin(target_url, data_str)
                                parsed = urlparse(real_post_url)
                                qs = parse_qs(parsed.query)
                                session_id = qs.get("session_id", ["default"])[0]
                                session_map[session_id] = real_post_url

                                # Rewrite endpoint to point to AXIOM /messages
                                proxy_endpoint = f"/messages?session_id={session_id}"
                                yield f"event: endpoint\ndata: {proxy_endpoint}\n\n"
                            elif event_type == "message":
                                await check_outbound_frame(
                                    data_str, server_identity, detector
                                )
                                yield f"event: message\ndata: {data_str}\n\n"
                            else:
                                yield f"event: {event_type}\ndata: {data_str}\n\n"
            except Exception as exc:
                logger.error(f"Error proxying SSE stream: {exc}")
                err_resp = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"SSE proxy error: {exc}"},
                }
                yield f"event: message\ndata: {json.dumps(err_resp)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.post("/messages")
    async def messages_endpoint(
        request: Request, session_id: Optional[str] = None
    ) -> Response:
        """Proxy JSON-RPC messages from client to target MCP server."""
        if not session_id or session_id not in session_map:
            raise HTTPException(status_code=400, detail="Invalid or missing session_id")

        real_post_url = session_map[session_id]
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8", errors="replace")

        err_line = await check_inbound_frame(body_str, server_identity, detector)
        if err_line is not None:
            # Return blocked JSON-RPC error directly to client
            return Response(
                content=err_line, media_type="application/json", status_code=200
            )

        try:
            resp = await client.post(
                real_post_url,
                content=body_bytes,
                headers={"Content-Type": "application/json"},
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
            )
        except Exception as exc:
            logger.error(f"Error forwarding message: {exc}")
            raise HTTPException(status_code=502, detail=f"Target server error: {exc}")

    return app
