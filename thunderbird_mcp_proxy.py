#!/usr/bin/env python3
"""
Thunderbird MCP Proxy — Wake-on-Call Subprocess Manager

Replaces 5 conditional MCP server entries in mcp.json with a single proxy.
Servers are started on first tool call and suspended after IDLE_TIMEOUT seconds.

Managed servers: apify, tomtom, calendly, signwell, firecrawl

Schema cache: config/proxy_schemas.json
  - Built automatically on first run (starts each server briefly to list tools)
  - Regenerate: python3 scripts/regenerate_proxy_schemas.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import mcp.types as types
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server import Server
from mcp.server.stdio import stdio_server

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
log = logging.getLogger("thunderbird-proxy")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROXY_DIR = Path(__file__).parent
SCHEMA_CACHE_PATH = PROXY_DIR / "config" / "proxy_schemas.json"
IDLE_TIMEOUT = 300  # seconds before idle server is suspended


def _env(key: str) -> str:
    return os.environ.get(key, "")


PROXY_SERVERS: dict[str, StdioServerParameters] = {
    "apify": StdioServerParameters(
        command="npx",
        args=["-y", "@apify/actors-mcp-server"],
        env={**os.environ, "APIFY_TOKEN": _env("APIFY_TOKEN")},
    ),
    "tomtom": StdioServerParameters(
        command="npx",
        args=["-y", "@tomtom-org/tomtom-mcp"],
        env={**os.environ, "TOMTOM_API_KEY": _env("TOMTOM_API_KEY")},
    ),
    "calendly": StdioServerParameters(
        command="npx",
        args=["-y", "calendly-mcp-server"],
        env={**os.environ, "CALENDLY_API_TOKEN": _env("CALENDLY_API_TOKEN")},
    ),
    "signwell": StdioServerParameters(
        command="npx",
        args=["-y", "@signwell/mcp"],
        env={**os.environ, "SIGNWELL_API_KEY": _env("SIGNWELL_API_KEY")},
    ),
    "firecrawl": StdioServerParameters(
        command="npx",
        args=["-y", "firecrawl-mcp"],
        env={**os.environ, "FIRECRAWL_API_KEY": _env("FIRECRAWL_API_KEY")},
    ),
}


# ---------------------------------------------------------------------------
# Suspended Server — lazy subprocess lifecycle manager
# ---------------------------------------------------------------------------

class SuspendedServer:
    """Manages one lazy MCP subprocess. Starts on first call, idles after timeout."""

    def __init__(self, name: str, params: StdioServerParameters):
        self.name = name
        self.params = params
        self._session: ClientSession | None = None
        self._cm = None
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()
        self._idle_task: asyncio.Task | None = None

    @property
    def is_awake(self) -> bool:
        return self._session is not None

    async def wake(self):
        async with self._lock:
            if self._session is not None:
                return
            log.info(f"[proxy] Waking {self.name}")
            self._cm = stdio_client(self.params)
            read, write = await self._cm.__aenter__()
            self._session = ClientSession(read, write)
            await self._session.__aenter__()
            await self._session.initialize()
            log.info(f"[proxy] {self.name} ready")
            if self._idle_task is None or self._idle_task.done():
                self._idle_task = asyncio.create_task(self._idle_watchdog())

    async def sleep(self):
        async with self._lock:
            if self._session is None:
                return
            log.info(f"[proxy] Suspending {self.name} (idle {IDLE_TIMEOUT}s)")
            try:
                await self._session.__aexit__(None, None, None)
                await self._cm.__aexit__(None, None, None)
            except Exception as e:
                log.warning(f"[proxy] Error suspending {self.name}: {e}")
            finally:
                self._session = None
                self._cm = None

    async def _idle_watchdog(self):
        loop = asyncio.get_event_loop()
        while True:
            await asyncio.sleep(60)
            if self._session is None:
                break
            idle = loop.time() - self._last_call
            if idle >= IDLE_TIMEOUT:
                await self.sleep()
                break

    async def list_tools(self) -> list[types.Tool]:
        await self.wake()
        self._last_call = asyncio.get_event_loop().time()
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict) -> list:
        await self.wake()
        self._last_call = asyncio.get_event_loop().time()
        result = await self._session.call_tool(name, arguments)
        return result.content


# ---------------------------------------------------------------------------
# Schema Cache
# ---------------------------------------------------------------------------

def load_schema_cache() -> dict[str, list[dict]]:
    if SCHEMA_CACHE_PATH.exists():
        return json.loads(SCHEMA_CACHE_PATH.read_text())
    return {}


def save_schema_cache(schemas: dict[str, list[dict]]):
    SCHEMA_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_CACHE_PATH.write_text(json.dumps(schemas, indent=2))
    log.info(f"[proxy] Schema cache saved: {SCHEMA_CACHE_PATH}")


async def build_schemas_for(names: list[str], suspended: dict[str, SuspendedServer]) -> dict[str, list[dict]]:
    """Start each server, capture tool list, suspend. Returns schema dict."""
    schemas: dict[str, list[dict]] = {}
    for name in names:
        try:
            print(f"[proxy] Fetching schema: {name}...", file=sys.stderr)
            tools = await suspended[name].list_tools()
            schemas[name] = [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": (
                        t.inputSchema.model_dump()
                        if hasattr(t.inputSchema, "model_dump")
                        else dict(t.inputSchema)
                    ),
                }
                for t in tools
            ]
            await suspended[name].sleep()
            print(f"[proxy] {name}: {len(tools)} tools", file=sys.stderr)
        except Exception as e:
            log.error(f"[proxy] Schema fetch failed for {name}: {e}")
            schemas[name] = []
    return schemas


# ---------------------------------------------------------------------------
# Main proxy runner
# ---------------------------------------------------------------------------

async def run_proxy():
    # Init suspended server objects
    suspended = {
        name: SuspendedServer(name, params)
        for name, params in PROXY_SERVERS.items()
    }

    # Load schema cache; build for any missing servers
    cache = load_schema_cache()
    missing = [n for n in PROXY_SERVERS if n not in cache]
    if missing:
        print(f"[proxy] Building schema cache for: {missing}", file=sys.stderr)
        new = await build_schemas_for(missing, suspended)
        cache.update(new)
        save_schema_cache(cache)

    # Build tool → server index and flat tool list
    tool_to_server: dict[str, str] = {}
    all_tools: list[types.Tool] = []
    for server_name, tool_defs in cache.items():
        for td in tool_defs:
            tool_to_server[td["name"]] = server_name
            all_tools.append(types.Tool(
                name=td["name"],
                description=td.get("description", ""),
                inputSchema=td.get("inputSchema", {"type": "object", "properties": {}}),
            ))

    print(f"[proxy] Ready — {len(all_tools)} tools across {len(cache)} servers", file=sys.stderr)

    # Build MCP server
    server = Server("thunderbird-proxy")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return all_tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        if name not in tool_to_server:
            return [types.TextContent(type="text", text=f"[proxy] Unknown tool: {name}")]
        srv_name = tool_to_server[name]
        try:
            return await suspended[srv_name].call_tool(name, arguments or {})
        except Exception as e:
            return [types.TextContent(type="text", text=f"[proxy] {srv_name}/{name} error: {e}")]

    # Run stdio transport
    async with stdio_server() as (read_stream, write_stream):
        init_opts = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_opts, raise_exceptions=False)


if __name__ == "__main__":
    asyncio.run(run_proxy())
