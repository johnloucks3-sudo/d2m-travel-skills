#!/usr/bin/env python3
"""
goose_mcp_proxy.py — stdio ↔ streamable-HTTP MCP proxy
=======================================================
Speaks stdio MCP protocol to Goose, forwards all calls to the
persistent HTTP MCP server at localhost:8767.

Why: Goose's stdio extensions break on gateway restart (dead pipe).
This proxy is cheap to respawn — the real server stays alive.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HTTP_SERVER = "http://127.0.0.1:8767/mcp"


async def run_proxy():
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.server.fastmcp import FastMCP
    from mcp import ClientSession

    # Connect to the persistent HTTP server
    async with streamablehttp_client(HTTP_SERVER) as (read, write, _):
        async with ClientSession(read, write) as http_session:
            await http_session.initialize()

            # Fetch all tools from the HTTP server
            tools_result = await http_session.list_tools()
            tools = tools_result.tools

            # Build a FastMCP stdio server that proxies each tool
            proxy = FastMCP("D2M Proxy")

            for tool in tools:
                tool_name = tool.name
                tool_desc = tool.description or ""

                # Closure to capture tool_name per iteration
                def make_handler(name):
                    async def handler(**kwargs):
                        result = await http_session.call_tool(name, kwargs)
                        # Extract text content from result
                        if result.content:
                            parts = []
                            for c in result.content:
                                if hasattr(c, "text"):
                                    parts.append(c.text)
                                else:
                                    parts.append(str(c))
                            return "\n".join(parts)
                        return ""
                    handler.__name__ = name
                    return handler

                proxy.add_tool(
                    make_handler(tool_name),
                    name=tool_name,
                    description=tool_desc,
                )

            # Serve via stdio
            await proxy.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(run_proxy())
