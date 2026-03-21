"""
Thunderbird MCP Connector — Unified Proxy for All Backend MCP Servers
=====================================================================

Dreams2Memories Travel, LLC · Thunderbird OS

Problem: Chromebook connects to YOGA via Cloudflare tunnel and needs separate
MCP config for each backend server. This connector exposes a single unified
endpoint that proxies to all backend MCP servers.

Architecture:
  Chromebook → cloudflared → thunderbird_api.py (:8766)
                                └── /mcp/*  (this connector, mounted as router)
                                └── /mcp    (Streamable HTTP transport)
                                    ↓
                              ┌─────────────────────┐
                              │  MCP Connector       │
                              │  (tool registry +    │
                              │   session mgmt +     │
                              │   proxy routing)     │
                              └──────┬──────┬───────┘
                                     │      │
                     ┌───────────────┘      └───────────────┐
                     ▼                                      ▼
              travel_mcp_server.py              (future MCP servers)
              :8765 Streamable HTTP

Endpoints (REST — mounted under /mcp prefix in thunderbird_api.py):
  GET  /mcp/tools          — Combined tool list from all backends
  POST /mcp/call           — Route a tool call to the correct backend
  GET  /mcp/health         — Backend health status
  GET  /mcp/sessions       — Active session list

Endpoints (Streamable HTTP — MCP protocol):
  POST /mcp               — MCP JSON-RPC (initialize, tools/list, tools/call)

MCP Tools (registered on travel_mcp_server.py):
  mcp_connector_status     — Health/stats for all backends
  mcp_connector_tools_list — Full tool inventory across backends

Integration:
  from thunderbird_mcp_connector import get_connector_router
  app.include_router(get_connector_router())
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(__file__).parent

# ============================================================================
# CONFIGURATION
# ============================================================================

# Backend MCP servers — add new servers here
MCP_BACKENDS: List[Dict[str, Any]] = [
    {
        "name": "dreams2memories",
        "url": "http://127.0.0.1:8765",
        "transport": "streamable-http",
        "endpoint": "/mcp",
        "description": "Primary MCP server — 120+ travel automation tools",
        "priority": 1,
    },
    # Future backends:
    # {
    #     "name": "analytics",
    #     "url": "http://127.0.0.1:8767",
    #     "transport": "streamable-http",
    #     "endpoint": "/mcp",
    #     "description": "Analytics and reporting MCP server",
    #     "priority": 2,
    # },
]

# Discovery and session settings
TOOL_REFRESH_INTERVAL = 300  # 5 minutes
SESSION_TIMEOUT = 1800       # 30 minutes idle
SESSION_CLEANUP_INTERVAL = 60  # Check for expired sessions every 60s

# ============================================================================
# MODELS
# ============================================================================

class ToolCallRequest(BaseModel):
    """Request body for /mcp/call."""
    tool_name: str = Field(..., description="Name of the MCP tool to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    session_id: Optional[str] = Field(None, description="Session ID for context carryover")


class ToolInfo(BaseModel):
    """Metadata for a discovered tool."""
    name: str
    description: str = ""
    backend: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# BACKEND CLIENT
# ============================================================================

class MCPBackendClient:
    """HTTP client for a single MCP backend server."""

    def __init__(self, config: Dict[str, Any]):
        self.name = config["name"]
        self.base_url = config["url"]
        self.endpoint = config.get("endpoint", "/mcp")
        self.description = config.get("description", "")
        self.priority = config.get("priority", 99)
        self.healthy = False
        self.last_check: Optional[float] = None
        self.last_error: Optional[str] = None
        self.tools: Dict[str, ToolInfo] = {}
        self._jsonrpc_id = 0

    @property
    def mcp_url(self) -> str:
        return f"{self.base_url}{self.endpoint}"

    def _next_id(self) -> int:
        self._jsonrpc_id += 1
        return self._jsonrpc_id

    async def _rpc(self, method: str, params: Optional[Dict] = None,
                   timeout: float = 30.0) -> Dict[str, Any]:
        """Send a JSON-RPC request to this backend."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params:
            payload["params"] = params

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                self.mcp_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise RuntimeError(
                f"Backend {self.name} RPC error: {data['error']}"
            )
        return data.get("result", {})

    async def health_check(self) -> bool:
        """Ping the backend and update health status."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self.mcp_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": self._next_id(),
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {
                                "name": "thunderbird-mcp-connector",
                                "version": "1.0.0",
                            },
                        },
                    },
                    headers={"Content-Type": "application/json"},
                )
                self.healthy = resp.status_code == 200
                self.last_error = None if self.healthy else f"HTTP {resp.status_code}"
        except Exception as e:
            self.healthy = False
            self.last_error = str(e)

        self.last_check = time.time()
        return self.healthy

    async def discover_tools(self) -> Dict[str, ToolInfo]:
        """Fetch the tool list from this backend via tools/list."""
        try:
            result = await self._rpc("tools/list")
            tools = {}
            for t in result.get("tools", []):
                info = ToolInfo(
                    name=t["name"],
                    description=t.get("description", ""),
                    backend=self.name,
                    input_schema=t.get("inputSchema", {}),
                )
                tools[t["name"]] = info
            self.tools = tools
            self.healthy = True
            self.last_error = None
            logger.info(
                f"Discovered {len(tools)} tools from backend '{self.name}'"
            )
        except Exception as e:
            logger.warning(
                f"Tool discovery failed for '{self.name}': {e}"
            )
            self.healthy = False
            self.last_error = str(e)

        self.last_check = time.time()
        return self.tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any],
                        timeout: float = 120.0) -> Dict[str, Any]:
        """Invoke a tool on this backend via tools/call."""
        result = await self._rpc(
            "tools/call",
            params={"name": tool_name, "arguments": arguments},
            timeout=timeout,
        )
        return result


# ============================================================================
# SESSION MANAGER
# ============================================================================

class Session:
    """Tracks a client session with context carryover."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_active = time.time()
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []

    def touch(self):
        self.last_active = time.time()
        self.call_count += 1

    def record_call(self, tool_name: str, backend: str, success: bool,
                    duration_ms: float):
        self.call_history.append({
            "tool": tool_name,
            "backend": backend,
            "success": success,
            "duration_ms": round(duration_ms, 1),
            "timestamp": datetime.now().isoformat(),
        })
        # Keep last 50 calls per session
        if len(self.call_history) > 50:
            self.call_history = self.call_history[-50:]

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TIMEOUT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_active": datetime.fromtimestamp(self.last_active).isoformat(),
            "idle_seconds": round(time.time() - self.last_active),
            "call_count": self.call_count,
            "recent_calls": self.call_history[-5:],
        }


class SessionManager:
    """Manages client sessions with automatic cleanup."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def get_or_create(self, session_id: Optional[str] = None) -> Session:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if not session.is_expired:
                return session
            # Expired — remove and create fresh
            del self._sessions[session_id]

        new_id = session_id or str(uuid.uuid4())
        session = Session(new_id)
        self._sessions[new_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and session.is_expired:
            del self._sessions[session_id]
            return None
        return session

    def cleanup_expired(self):
        expired = [
            sid for sid, s in self._sessions.items() if s.is_expired
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if not s.is_expired)

    def list_sessions(self) -> List[Dict[str, Any]]:
        self.cleanup_expired()
        return [s.to_dict() for s in self._sessions.values()]

    async def start_cleanup_loop(self):
        """Background task to clean expired sessions."""
        while True:
            await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
            self.cleanup_expired()

    def start(self):
        self._cleanup_task = asyncio.ensure_future(self.start_cleanup_loop())

    def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()


# ============================================================================
# MCP CONNECTOR CORE
# ============================================================================

class MCPConnector:
    """
    Central connector that aggregates tools from all backend MCP servers,
    routes tool calls, manages sessions, and handles Streamable HTTP.
    """

    def __init__(self):
        self.backends: Dict[str, MCPBackendClient] = {}
        self.tool_registry: Dict[str, ToolInfo] = {}
        self.tool_to_backend: Dict[str, str] = {}
        self.sessions = SessionManager()
        self._refresh_task: Optional[asyncio.Task] = None
        self._started = False
        self._last_refresh: Optional[float] = None
        self._startup_time: Optional[float] = None

        # Initialize backends from config
        for cfg in MCP_BACKENDS:
            client = MCPBackendClient(cfg)
            self.backends[cfg["name"]] = client

    async def startup(self):
        """Initialize connector — discover tools from all backends."""
        if self._started:
            return
        self._startup_time = time.time()
        logger.info(
            f"MCP Connector starting — {len(self.backends)} backend(s) configured"
        )
        await self.refresh_tools()
        self.sessions.start()
        self._refresh_task = asyncio.ensure_future(self._refresh_loop())
        self._started = True
        logger.info(
            f"MCP Connector ready — {len(self.tool_registry)} tools across "
            f"{len(self.backends)} backend(s)"
        )

    async def shutdown(self):
        """Clean shutdown."""
        if self._refresh_task:
            self._refresh_task.cancel()
        self.sessions.stop()
        self._started = False

    async def _refresh_loop(self):
        """Periodically re-discover tools from all backends."""
        while True:
            await asyncio.sleep(TOOL_REFRESH_INTERVAL)
            try:
                await self.refresh_tools()
            except Exception as e:
                logger.error(f"Tool refresh failed: {e}")

    async def refresh_tools(self):
        """Discover tools from all backends and rebuild the unified registry."""
        all_tools: Dict[str, ToolInfo] = {}
        mapping: Dict[str, str] = {}

        # Discover in parallel
        tasks = {
            name: asyncio.create_task(client.discover_tools())
            for name, client in self.backends.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for (name, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                logger.warning(f"Discovery failed for '{name}': {result}")
                continue
            for tool_name, tool_info in result.items():
                # If duplicate tool name across backends, higher priority wins
                if tool_name in all_tools:
                    existing_backend = mapping[tool_name]
                    existing_priority = self.backends[existing_backend].priority
                    new_priority = self.backends[name].priority
                    if new_priority >= existing_priority:
                        continue  # Keep existing (lower number = higher priority)
                all_tools[tool_name] = tool_info
                mapping[tool_name] = name

        self.tool_registry = all_tools
        self.tool_to_backend = mapping
        self._last_refresh = time.time()
        logger.info(
            f"Tool registry refreshed: {len(all_tools)} tools from "
            f"{len(set(mapping.values()))} backend(s)"
        )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any],
                        session_id: Optional[str] = None) -> Dict[str, Any]:
        """Route a tool call to the correct backend."""
        backend_name = self.tool_to_backend.get(tool_name)
        if not backend_name:
            raise HTTPException(
                404,
                f"Tool '{tool_name}' not found. "
                f"Available: {len(self.tool_registry)} tools. "
                f"Use GET /mcp/tools to list them.",
            )

        backend = self.backends[backend_name]
        if not backend.healthy:
            # Retry health check once before failing
            await backend.health_check()
            if not backend.healthy:
                raise HTTPException(
                    503,
                    f"Backend '{backend_name}' is unhealthy: {backend.last_error}",
                )

        session = self.sessions.get_or_create(session_id)
        session.touch()

        start = time.time()
        try:
            result = await backend.call_tool(tool_name, arguments)
            duration_ms = (time.time() - start) * 1000
            session.record_call(tool_name, backend_name, True, duration_ms)
            logger.info(
                f"Tool call: {tool_name} → {backend_name} "
                f"({duration_ms:.0f}ms, session={session.session_id[:8]})"
            )
            return {
                "status": "success",
                "tool": tool_name,
                "backend": backend_name,
                "session_id": session.session_id,
                "duration_ms": round(duration_ms, 1),
                "result": result,
            }
        except HTTPException:
            raise
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            session.record_call(tool_name, backend_name, False, duration_ms)
            logger.error(f"Tool call failed: {tool_name} → {e}")
            raise HTTPException(500, f"Tool call failed: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """Full connector status report."""
        backend_status = {}
        for name, client in self.backends.items():
            backend_status[name] = {
                "url": client.base_url,
                "healthy": client.healthy,
                "tool_count": len(client.tools),
                "last_check": (
                    datetime.fromtimestamp(client.last_check).isoformat()
                    if client.last_check else None
                ),
                "last_error": client.last_error,
                "description": client.description,
            }

        return {
            "status": "operational" if any(
                c.healthy for c in self.backends.values()
            ) else "degraded",
            "total_tools": len(self.tool_registry),
            "backends": backend_status,
            "active_sessions": self.sessions.active_count,
            "uptime_seconds": (
                round(time.time() - self._startup_time)
                if self._startup_time else 0
            ),
            "last_refresh": (
                datetime.fromtimestamp(self._last_refresh).isoformat()
                if self._last_refresh else None
            ),
            "refresh_interval_sec": TOOL_REFRESH_INTERVAL,
            "session_timeout_sec": SESSION_TIMEOUT,
        }

    # ========================================================================
    # STREAMABLE HTTP — MCP Protocol Handler
    # ========================================================================

    async def handle_mcp_request(self, request: Request) -> Any:
        """
        Handle MCP Streamable HTTP transport.

        Supports the MCP JSON-RPC protocol:
          - initialize
          - initialized (notification)
          - tools/list
          - tools/call
          - ping
        """
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
                status_code=400,
            )

        # Handle batch requests
        if isinstance(body, list):
            responses = []
            for item in body:
                resp = await self._handle_single_rpc(item, request)
                if resp is not None:  # Skip notifications
                    responses.append(resp)
            return JSONResponse(responses) if responses else JSONResponse(
                content=None, status_code=204
            )

        result = await self._handle_single_rpc(body, request)
        if result is None:
            # Notification — no response
            return JSONResponse(content=None, status_code=204)

        # Session ID header for client tracking
        session_id = request.headers.get("mcp-session-id")
        if not session_id:
            session = self.sessions.get_or_create()
            session_id = session.session_id

        response = JSONResponse(result)
        response.headers["Mcp-Session-Id"] = session_id
        return response

    async def _handle_single_rpc(self, body: Dict[str, Any],
                                  request: Request) -> Optional[Dict[str, Any]]:
        """Process a single JSON-RPC request."""
        method = body.get("method", "")
        params = body.get("params", {})
        rpc_id = body.get("id")  # None for notifications

        # Notifications (no id) — don't return a response
        if rpc_id is None:
            return None

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {
                        "tools": {"listChanged": True},
                    },
                    "serverInfo": {
                        "name": "thunderbird-mcp-connector",
                        "version": "1.0.0",
                    },
                }

            elif method == "ping":
                result = {}

            elif method == "tools/list":
                tools_list = []
                for tool in self.tool_registry.values():
                    entry = {
                        "name": tool.name,
                        "description": tool.description,
                    }
                    if tool.input_schema:
                        entry["inputSchema"] = tool.input_schema
                    tools_list.append(entry)
                result = {"tools": tools_list}

            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                session_id = request.headers.get("mcp-session-id")

                backend_name = self.tool_to_backend.get(tool_name)
                if not backend_name:
                    return {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {
                            "code": -32601,
                            "message": f"Tool not found: {tool_name}",
                        },
                    }

                backend = self.backends[backend_name]
                raw_result = await backend.call_tool(tool_name, arguments)

                # Track in session
                session = self.sessions.get_or_create(session_id)
                session.touch()
                session.record_call(tool_name, backend_name, True, 0)

                result = raw_result

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

            return {"jsonrpc": "2.0", "id": rpc_id, "result": result}

        except Exception as e:
            logger.error(f"MCP RPC error ({method}): {e}")
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            }


# ============================================================================
# SINGLETON
# ============================================================================

_connector: Optional[MCPConnector] = None


def get_connector() -> MCPConnector:
    """Get or create the singleton connector instance."""
    global _connector
    if _connector is None:
        _connector = MCPConnector()
    return _connector


# ============================================================================
# FASTAPI ROUTER — Mount in thunderbird_api.py
# ============================================================================

def get_connector_router() -> APIRouter:
    """
    Create the FastAPI router for the MCP Connector.

    Usage in thunderbird_api.py:
        from thunderbird_mcp_connector import get_connector_router
        app.include_router(get_connector_router())
    """
    router = APIRouter(tags=["MCP Connector"])
    connector = get_connector()

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    @router.on_event("startup")
    async def _startup():
        await connector.startup()

    @router.on_event("shutdown")
    async def _shutdown():
        await connector.shutdown()

    # ------------------------------------------------------------------
    # Streamable HTTP — single MCP protocol endpoint
    # ------------------------------------------------------------------

    @router.post("/mcp")
    async def mcp_streamable_http(request: Request):
        """
        MCP Streamable HTTP transport endpoint.

        Accepts JSON-RPC requests per the MCP specification.
        Clients should include Mcp-Session-Id header for session continuity.
        """
        return await connector.handle_mcp_request(request)

    # ------------------------------------------------------------------
    # REST convenience endpoints
    # ------------------------------------------------------------------

    @router.get("/mcp/tools")
    async def list_tools():
        """List all available tools across all backend MCP servers."""
        tools = []
        for tool in connector.tool_registry.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "backend": tool.backend,
                "input_schema": tool.input_schema,
            })
        tools.sort(key=lambda t: t["name"])
        return {
            "status": "success",
            "count": len(tools),
            "backends": list(connector.backends.keys()),
            "tools": tools,
        }

    @router.post("/mcp/call")
    async def call_tool(req: ToolCallRequest):
        """
        Call an MCP tool by name, routed to the correct backend.

        The connector resolves which backend owns the tool and proxies the call.
        Include session_id for context carryover between calls.
        """
        return await connector.call_tool(
            req.tool_name, req.arguments, req.session_id
        )

    @router.get("/mcp/health")
    async def connector_health():
        """Health status of the MCP Connector and all backends."""
        return connector.get_status()

    @router.get("/mcp/sessions")
    async def list_sessions():
        """List active client sessions."""
        return {
            "active_sessions": connector.sessions.active_count,
            "sessions": connector.sessions.list_sessions(),
        }

    @router.post("/mcp/refresh")
    async def force_refresh():
        """Force re-discovery of tools from all backends."""
        await connector.refresh_tools()
        return {
            "status": "refreshed",
            "total_tools": len(connector.tool_registry),
            "backends": {
                name: {
                    "healthy": c.healthy,
                    "tool_count": len(c.tools),
                }
                for name, c in connector.backends.items()
            },
        }

    return router


# ============================================================================
# MCP TOOL REGISTRATION — For travel_mcp_server.py
# ============================================================================

def register_connector_tools(mcp_server):
    """
    Register connector MCP tools on the travel_mcp_server.py FastMCP instance.

    Usage in travel_mcp_server.py:
        from thunderbird_mcp_connector import register_connector_tools
        register_connector_tools(mcp)
    """

    @mcp_server.tool(
        name="mcp_connector_status",
        annotations={
            "title": "MCP Connector Status",
            "readOnlyHint": True,
        },
    )
    async def mcp_connector_status() -> str:
        """Get health and status of the MCP Connector and all backend servers.

        Returns backend health, tool counts, active sessions, uptime, and
        last refresh timestamp. Use this to diagnose connectivity issues
        between the Chromebook and YOGA MCP backends.
        """
        connector = get_connector()
        if not connector._started:
            return json.dumps({
                "status": "not_started",
                "message": "Connector has not been started. It initializes when "
                           "thunderbird_api.py includes the connector router.",
            }, indent=2)
        return json.dumps(connector.get_status(), indent=2)

    @mcp_server.tool(
        name="mcp_connector_tools_list",
        annotations={
            "title": "MCP Connector — Full Tool Inventory",
            "readOnlyHint": True,
        },
    )
    async def mcp_connector_tools_list(
        backend: Optional[str] = None,
        search: Optional[str] = None,
    ) -> str:
        """List all tools available through the MCP Connector.

        Args:
            backend: Filter to a specific backend name (e.g., 'dreams2memories')
            search: Filter tools by name substring (case-insensitive)

        Returns a JSON array of tool names, descriptions, and their backend.
        """
        connector = get_connector()
        tools = []
        for tool in connector.tool_registry.values():
            if backend and tool.backend != backend:
                continue
            if search and search.lower() not in tool.name.lower():
                continue
            tools.append({
                "name": tool.name,
                "description": tool.description[:120] if tool.description else "",
                "backend": tool.backend,
            })
        tools.sort(key=lambda t: t["name"])
        return json.dumps({
            "count": len(tools),
            "filter_backend": backend,
            "filter_search": search,
            "tools": tools,
        }, indent=2)
