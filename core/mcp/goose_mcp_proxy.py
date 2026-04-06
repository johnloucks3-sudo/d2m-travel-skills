#!/usr/bin/env python3
"""
goose_mcp_proxy.py — stdio ↔ streamable-HTTP MCP proxy
=======================================================
Speaks stdio MCP protocol to Goose, forwards all calls to the
persistent HTTP MCP server at localhost:8767.

Why: Goose's stdio extensions break on gateway restart (dead pipe).
This proxy is cheap to respawn — the real server stays alive.

Architecture — raw JSON-RPC stdio bridge:
  Does NOT use FastMCP as the stdio server (FastMCP Pydantic V2 rejects
  generic **kwargs handlers). Instead runs a direct JSON-RPC event loop:
  reads newline-delimited JSON from stdin, forwards tool calls via fresh
  HTTP sessions per call, writes JSON-RPC responses to stdout.

  Fresh-per-call: the HTTP backend is stateless (Terminating session: None
  on every response). Using a single startup connection causes stale
  "Transport closed" after idle periods. Fresh sessions match the server.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HTTP_SERVER = "http://127.0.0.1:8767/mcp"
PROTOCOL_VERSION = "2024-11-05"


def write_json(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


async def http_call_tool(name: str, arguments: dict) -> list[dict]:
    """Open a fresh HTTP session, call one tool, return content list."""
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    async with streamablehttp_client(HTTP_SERVER) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            return [
                {"type": "text", "text": getattr(c, "text", str(c))}
                for c in (result.content or [])
            ]


async def fetch_tools() -> tuple[list, list]:
    """One-time tool discovery at startup. Returns (tools_raw, tools_schema)."""
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    async with streamablehttp_client(HTTP_SERVER) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.list_tools()
            tools = result.tools
            schema = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
                }
                for t in tools
            ]
            return tools, schema


async def run_proxy():
    # Discover tools once at startup
    _raw_tools, tools_schema = await fetch_tools()

    # Set up async stdin reader
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    # JSON-RPC dispatch loop
    while True:
        line = await reader.readline()
        if not line:
            break

        try:
            req = json.loads(line.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params", {})

        # Notifications — no response needed
        if req_id is None:
            continue

        try:
            if method == "initialize":
                write_json({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "D2M Proxy", "version": "1.0"},
                    },
                })

            elif method == "tools/list":
                write_json({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"tools": tools_schema},
                })

            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                content = await http_call_tool(tool_name, arguments)
                write_json({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": content, "isError": False},
                })

            elif method in ("ping", "resources/list", "prompts/list"):
                # Minimal stubs — proxy only forwards tools
                write_json({
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {},
                })

            else:
                write_json({
                    "jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                })

        except Exception as exc:
            write_json({
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32000, "message": str(exc)},
            })


if __name__ == "__main__":
    asyncio.run(run_proxy())
