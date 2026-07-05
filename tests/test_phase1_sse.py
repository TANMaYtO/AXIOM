"""Tests for Phase 1 Server-Sent Events (SSE) transport proxy and rug-pull defense."""

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import pytest
from proxy.rug_pull import RugPullDetector
from proxy.sse import create_sse_proxy_app


def create_dummy_sse_server() -> FastAPI:
    """Create a dummy MCP SSE server for testing."""
    app = FastAPI(title="Dummy SSE Server")

    @app.get("/sse")
    async def dummy_sse(request: Request) -> StreamingResponse:
        """Stream simulated MCP server SSE events."""

        async def event_generator() -> AsyncGenerator[str, None]:
            yield "event: endpoint\ndata: /messages?session_id=test-sess-1\n\n"
            tools_resp: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tools": [
                        {
                            "name": "sse_echo",
                            "description": "Echoes over SSE",
                            "inputSchema": {"type": "object"},
                        }
                    ]
                },
            }
            yield f"event: message\ndata: {json.dumps(tools_resp)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/messages")
    async def dummy_messages(request: Request, session_id: str = "") -> Response:
        """Receive and respond to client JSON-RPC requests."""
        body = await request.body()
        data = json.loads(body)
        resp = {
            "jsonrpc": "2.0",
            "id": data.get("id"),
            "result": {"echoed": data.get("params")},
        }
        return Response(content=json.dumps(resp), media_type="application/json")

    return app


@pytest.mark.asyncio
async def test_sse_proxy_end_to_end_and_blocking(tmp_path: Path) -> None:
    """Test SSE stream proxying, endpoint rewriting, forwarding, and call blocking."""
    storage_file = str(tmp_path / "sse_baselines.json")
    detector = RugPullDetector(storage_path=storage_file)

    dummy_server = create_dummy_sse_server()
    dummy_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=dummy_server),
        base_url="http://dummy-server",
    )

    proxy_app = create_sse_proxy_app(
        target_url="http://dummy-server/sse",
        detector=detector,
        client=dummy_client,
    )
    proxy_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=proxy_app),
        base_url="http://proxy-server",
    )

    try:
        # 1. Connect to proxy /sse endpoint and verify event streaming & rewriting
        async with proxy_client.stream("GET", "/sse") as resp:
            assert resp.status_code == 200
            events = []
            async for line in resp.aiter_lines():
                if line:
                    events.append(line)
                if len(events) >= 4:
                    break

            assert "event: endpoint" in events[0]
            assert "data: /messages?session_id=test-sess-1" in events[1]
            assert "event: message" in events[2]
            assert "sse_echo" in events[3]

        # Verify baseline was recorded for SSE server identity
        server_id = "sse:http://dummy-server/sse"
        assert detector.is_call_blocked(server_id) is False

        # 2. Test forwarding a valid tools/call request over POST
        call_req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "sse_echo", "arguments": {"text": "hello"}},
            "id": 10,
        }
        post_resp = await proxy_client.post(
            "/messages?session_id=test-sess-1", json=call_req
        )
        assert post_resp.status_code == 200
        post_data = post_resp.json()
        assert post_data["result"]["echoed"] == call_req["params"]

        # 3. Simulate a Rug-Pull attack on the SSE server
        rug_pull_resp = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "sse_echo",
                        "description": "MALICIOUS TAMPERED DESCRIPTION",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
        }
        valid = await detector.evaluate_tools_list(server_id, rug_pull_resp)
        assert valid is False
        assert detector.is_call_blocked(server_id) is True

        # 4. Verify subsequent tools/call over SSE proxy is blocked with error -32000
        blocked_resp = await proxy_client.post(
            "/messages?session_id=test-sess-1", json=call_req
        )
        assert blocked_resp.status_code == 200
        blocked_data = blocked_resp.json()
        assert blocked_data["error"]["code"] == -32000
        assert "OWASP MCP03" in blocked_data["error"]["message"]
        assert "blocked due to schema tampering" in blocked_data["error"]["message"]

    finally:
        await proxy_client.aclose()
        await dummy_client.aclose()
