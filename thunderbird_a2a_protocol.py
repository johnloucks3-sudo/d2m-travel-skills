"""
Thunderbird A2A Protocol — Google A2A Spec Compliance Layer
============================================================
Dreams2Memories Travel, LLC — Thunderbird OS

Implements the Google Agent-to-Agent (A2A) protocol so that Wing personas
are discoverable and callable by external agent systems (MAGOA/TESS, future
commercial partners, any A2A-compliant client).

Spec reference: https://google.github.io/A2A/

Components:
  1. Agent Card — /.well-known/agent.json  (system + per-persona cards)
  2. Task Lifecycle — submitted → working → input-required → completed/failed/canceled
  3. Message Exchange — role/parts/metadata mapping to persona calls
  4. SSE Streaming — /a2a/tasks/{task_id}/stream
  5. FastAPI Router — mountable on thunderbird_api.py
  6. Security — Bearer token auth, rate limiting
  7. MCP Tool Registration — a2a_create_task, a2a_task_status, a2a_list_tasks

Usage:
  # In thunderbird_api.py:
  from thunderbird_a2a_protocol import get_a2a_router
  app.include_router(get_a2a_router())

  # In travel_mcp_server.py:
  from thunderbird_a2a_protocol import register_a2a_tools
  register_a2a_tools(mcp)
"""

import json
import logging
import os
import secrets
import sqlite3
import threading
import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("thunderbird_a2a_protocol")

THUNDERBIRD_DIR = Path(__file__).parent
DB_PATH = THUNDERBIRD_DIR / "a2a_tasks.db"
BEARER_TOKEN_FILE = THUNDERBIRD_DIR / ".api_token"

# ============================================================================
# A2A TASK STATES
# ============================================================================

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


# ============================================================================
# PYDANTIC MODELS — A2A message format
# ============================================================================

class MessagePart(BaseModel):
    type: str = Field("text", description="Part type: text, file, data")
    text: Optional[str] = None
    file_uri: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    mime_type: Optional[str] = None


class A2AMessage(BaseModel):
    role: str = Field(..., description="Message role: user or agent")
    parts: List[MessagePart] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


class TaskCreateRequest(BaseModel):
    target_persona: str = Field("COS", description="Persona ID to handle the task (COS, A2, A3, etc.)")
    message: A2AMessage
    metadata: Optional[Dict[str, Any]] = None


class TaskMessageRequest(BaseModel):
    message: A2AMessage


# ============================================================================
# AGENT CARD DEFINITIONS
# ============================================================================

_PERSONA_CAPABILITIES = {
    "COS": {
        "name": "Col Victoria Hale — Chief of Staff",
        "description": "Orchestration, prioritization, staff coordination, synthesis, crisis management. Routes to specialist personas as needed.",
        "skills": ["orchestration", "task-routing", "synthesis", "crisis-management", "staff-coordination"],
        "accepts_external": True,
    },
    "EXEC": {
        "name": "Naia Solberg-Vega — Voice & Visual",
        "description": "Brand voice, client communications, visual design, proposals, copy editing. Commander's intent translation.",
        "skills": ["brand-voice", "client-communications", "visual-design", "proposals"],
        "accepts_external": False,
    },
    "A2": {
        "name": "Lt Col Marcus Dembe — Research & Intel",
        "description": "Destination research, travel advisories, competitor analysis, pricing intelligence, supplier intel.",
        "skills": ["destination-research", "travel-advisories", "competitor-analysis", "pricing-intel"],
        "accepts_external": True,
    },
    "A3": {
        "name": "Danielle Moreau — Luxury Travel Concierge",
        "description": "Client-facing concierge. Bookings, itineraries, excursions, dining, logistics. The sole voice clients interact with.",
        "skills": ["bookings", "itineraries", "excursions", "dining", "client-journey"],
        "accepts_external": True,
    },
    "A5": {
        "name": "Lt Col Ryan Castillo — Strategy & Growth",
        "description": "Business strategy, competitive positioning, pricing strategy, growth vectors, OODA-loop analysis.",
        "skills": ["strategy", "growth-planning", "competitive-positioning", "pricing-strategy"],
        "accepts_external": False,
    },
    "A9": {
        "name": "Victor Harlan — Finance & Process",
        "description": "Commission audits, cost analysis, ROI, budgeting, waste identification, financial modeling.",
        "skills": ["commission-audit", "cost-analysis", "roi", "budgeting"],
        "accepts_external": False,
    },
    "CH": {
        "name": "Col James Washington — Wisdom & Ethics",
        "description": "Ethics checks, morale, perspective, wisdom. Every word lands.",
        "skills": ["ethics", "morale", "perspective"],
        "accepts_external": False,
    },
    "A12": {
        "name": "ELON — Innovation & Disruption",
        "description": "Automation, first-principles redesign, process elimination. 'Why are we doing this at all?'",
        "skills": ["automation", "innovation", "first-principles"],
        "accepts_external": False,
    },
}


def build_agent_card() -> Dict[str, Any]:
    """Build the root agent card (/.well-known/agent.json) per A2A spec."""
    sub_agents = []
    for pid, cap in _PERSONA_CAPABILITIES.items():
        sub_agents.append({
            "id": pid,
            "name": cap["name"],
            "description": cap["description"],
            "skills": cap["skills"],
            "accepts_external_tasks": cap["accepts_external"],
        })

    return {
        "name": "Dreams2Memories Travel — Thunderbird OS",
        "description": (
            "AI-powered luxury travel agency operating as a full Wing staff. "
            "Handles destination research, booking operations, client concierge, "
            "financial analysis, and strategic planning for high-end travel."
        ),
        "url": "https://api.d2mluxury.quest",
        "version": "2.3.0",
        "protocol_version": "0.2",
        "capabilities": {
            "tasks": True,
            "streaming": True,
            "message_exchange": True,
            "push_notifications": False,
        },
        "supported_protocols": ["a2a/0.2", "mcp/1.0"],
        "authentication": {
            "type": "bearer",
            "description": "Authorization: Bearer <token>",
        },
        "default_agent": "COS",
        "sub_agents": sub_agents,
        "contact": "concierge@d2mluxury.quest",
        "organization": "Dreams2Memories Travel, LLC",
    }


# ============================================================================
# TASK STORE — SQLite persistence
# ============================================================================

_db_lock = threading.Lock()


def _init_db():
    """Initialize the SQLite database for task persistence."""
    with _db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS a2a_tasks (
                task_id TEXT PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'submitted',
                target_persona TEXT NOT NULL DEFAULT 'COS',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS a2a_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                role TEXT NOT NULL,
                parts TEXT NOT NULL DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES a2a_tasks(task_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_task
            ON a2a_messages(task_id)
        """)
        conn.commit()
        conn.close()


_init_db()


class TaskStore:
    """SQLite-backed task persistence for A2A protocol."""

    def __init__(self, db_path: str = str(DB_PATH)):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_task(self, target_persona: str = "COS",
                    metadata: Optional[Dict] = None) -> str:
        """Create a new task, return task_id."""
        task_id = f"a2a-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with _db_lock:
            conn = self._conn()
            conn.execute(
                "INSERT INTO a2a_tasks (task_id, state, target_persona, metadata, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, TaskState.SUBMITTED.value, target_persona,
                 json.dumps(metadata or {}), now, now),
            )
            conn.commit()
            conn.close()
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task by ID with all messages."""
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM a2a_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        if not row:
            conn.close()
            return None

        messages = conn.execute(
            "SELECT role, parts, metadata, created_at FROM a2a_messages "
            "WHERE task_id = ? ORDER BY id", (task_id,)
        ).fetchall()
        conn.close()

        return {
            "task_id": row["task_id"],
            "state": row["state"],
            "target_persona": row["target_persona"],
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "messages": [
                {
                    "role": m["role"],
                    "parts": json.loads(m["parts"]),
                    "metadata": json.loads(m["metadata"]),
                    "created_at": m["created_at"],
                }
                for m in messages
            ],
        }

    def update_state(self, task_id: str, state: TaskState):
        """Update task state."""
        now = datetime.now(timezone.utc).isoformat()
        with _db_lock:
            conn = self._conn()
            conn.execute(
                "UPDATE a2a_tasks SET state = ?, updated_at = ? WHERE task_id = ?",
                (state.value, now, task_id),
            )
            conn.commit()
            conn.close()

    def add_message(self, task_id: str, role: str, parts: List[Dict],
                    metadata: Optional[Dict] = None):
        """Append a message to a task."""
        now = datetime.now(timezone.utc).isoformat()
        with _db_lock:
            conn = self._conn()
            conn.execute(
                "INSERT INTO a2a_messages (task_id, role, parts, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (task_id, role, json.dumps(parts), json.dumps(metadata or {}), now),
            )
            # Also update the task timestamp
            conn.execute(
                "UPDATE a2a_tasks SET updated_at = ? WHERE task_id = ?", (now, task_id),
            )
            conn.commit()
            conn.close()

    def list_tasks(self, limit: int = 50, state: Optional[str] = None) -> List[Dict]:
        """List tasks, optionally filtered by state."""
        conn = self._conn()
        if state:
            rows = conn.execute(
                "SELECT task_id, state, target_persona, created_at, updated_at "
                "FROM a2a_tasks WHERE state = ? ORDER BY updated_at DESC LIMIT ?",
                (state, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT task_id, state, target_persona, created_at, updated_at "
                "FROM a2a_tasks ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if it is not already terminal."""
        task = self.get_task(task_id)
        if not task:
            return False
        if task["state"] in (TaskState.COMPLETED.value, TaskState.FAILED.value,
                             TaskState.CANCELED.value):
            return False
        self.update_state(task_id, TaskState.CANCELED)
        return True


# Singleton store
_store = TaskStore()

# SSE subscriber registry: task_id -> list of asyncio.Queue
_sse_subscribers: Dict[str, List[asyncio.Queue]] = {}
_sse_lock = threading.Lock()


def _notify_subscribers(task_id: str, event_type: str, data: Dict):
    """Push an SSE event to all subscribers of a task."""
    with _sse_lock:
        queues = _sse_subscribers.get(task_id, [])
        payload = {"event": event_type, "data": data}
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # Drop if subscriber is slow


# ============================================================================
# TASK EXECUTION — bridges A2A tasks to persona calls
# ============================================================================

def _extract_text(message: A2AMessage) -> str:
    """Extract the text content from an A2A message."""
    texts = []
    for part in message.parts:
        if part.type == "text" and part.text:
            texts.append(part.text)
        elif part.type == "data" and part.data:
            texts.append(json.dumps(part.data))
    return "\n".join(texts) if texts else ""


async def _execute_task(task_id: str, target_persona: str, query: str):
    """Execute a task by calling the target persona. Runs in background."""
    try:
        _store.update_state(task_id, TaskState.WORKING)
        _notify_subscribers(task_id, "state", {"state": "working"})

        # Import here to avoid circular imports at module load
        from thunderbird_personas import call_persona, resolve_id
        from thunderbird_a2a import AGENT_CARDS

        pid = resolve_id(target_persona)

        # Validate persona accepts external queries
        card = AGENT_CARDS.get(pid, {})
        accepts = card.get("accepts_from", ["all"])
        # External A2A callers are treated as "all" — if persona restricts, reject
        cap = _PERSONA_CAPABILITIES.get(pid, {})
        if not cap.get("accepts_external", False):
            # Internal-only persona — route through COS
            prefixed = f"[A2A External → {pid}] {query}"
            pid = "COS"
            query = prefixed

        # Run persona call (synchronous — runs in executor)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: call_persona(pid, f"[A2A Protocol] {query}", max_tokens=2000)
        )

        answer = result.get("answer", "")
        response_parts = [{"type": "text", "text": answer}]
        response_meta = {
            "persona": result.get("persona", pid),
            "persona_name": result.get("name", ""),
            "model": result.get("model", ""),
        }

        _store.add_message(task_id, "agent", response_parts, response_meta)
        _store.update_state(task_id, TaskState.COMPLETED)
        _notify_subscribers(task_id, "message", {
            "role": "agent", "parts": response_parts, "metadata": response_meta,
        })
        _notify_subscribers(task_id, "state", {"state": "completed"})

    except Exception as exc:
        logger.error(f"A2A task {task_id} failed: {exc}", exc_info=True)
        error_parts = [{"type": "text", "text": f"Task failed: {str(exc)}"}]
        _store.add_message(task_id, "agent", error_parts, {"error": True})
        _store.update_state(task_id, TaskState.FAILED)
        _notify_subscribers(task_id, "state", {"state": "failed", "error": str(exc)})


# ============================================================================
# SECURITY — Bearer token + rate limiting
# ============================================================================

def _load_bearer_token() -> str:
    """Load bearer token from .api_token file."""
    if BEARER_TOKEN_FILE.exists():
        return BEARER_TOKEN_FILE.read_text(encoding="utf-8").strip()
    raise RuntimeError(f"Bearer token file missing: {BEARER_TOKEN_FILE}")


# Simple in-memory rate limiter: IP -> (count, window_start)
_rate_limits: Dict[str, tuple] = {}
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 30  # requests per window


def _check_rate_limit(client_ip: str):
    """Raise 429 if client exceeds rate limit."""
    now = datetime.now(timezone.utc).timestamp()
    entry = _rate_limits.get(client_ip)
    if entry is None or (now - entry[1]) > _RATE_LIMIT_WINDOW:
        _rate_limits[client_ip] = (1, now)
        return
    count, window_start = entry
    if count >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {_RATE_LIMIT_MAX} requests per {_RATE_LIMIT_WINDOW}s",
        )
    _rate_limits[client_ip] = (count + 1, window_start)


async def _verify_bearer(request: Request):
    """FastAPI dependency: verify Authorization: Bearer <token>."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")
    token = auth[7:]
    try:
        expected = _load_bearer_token()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid bearer token")
    _check_rate_limit(request.client.host if request.client else "unknown")


# ============================================================================
# FASTAPI ROUTER
# ============================================================================

def get_a2a_router() -> APIRouter:
    """Create and return the A2A protocol router.

    Mount on the main app:
        from thunderbird_a2a_protocol import get_a2a_router
        app.include_router(get_a2a_router())
    """
    router = APIRouter(tags=["A2A Protocol"])

    # --- Agent Card (public, no auth) ---
    @router.get("/.well-known/agent.json")
    async def agent_card():
        """A2A Agent Card — describes this agent system's capabilities."""
        return build_agent_card()

    # --- Create Task ---
    @router.post("/a2a/tasks", dependencies=[Depends(_verify_bearer)])
    async def create_task(req: TaskCreateRequest, request: Request):
        """Create a new A2A task and begin execution.

        The task is created in 'submitted' state, then the target persona
        is invoked asynchronously. Poll GET /a2a/tasks/{task_id} or subscribe
        to the SSE stream for updates.
        """
        pid = req.target_persona.upper()
        if pid not in _PERSONA_CAPABILITIES and pid not in ("A1", "A6"):
            raise HTTPException(
                status_code=400,
                detail=f"Unknown persona '{req.target_persona}'. "
                       f"Available: {', '.join(_PERSONA_CAPABILITIES.keys())}",
            )

        task_id = _store.create_task(
            target_persona=pid,
            metadata=req.metadata,
        )

        # Store the initial user message
        parts_raw = [p.model_dump() for p in req.message.parts]
        msg_meta = req.message.metadata or {}
        _store.add_message(task_id, req.message.role, parts_raw, msg_meta)

        query = _extract_text(req.message)
        if not query:
            raise HTTPException(status_code=400, detail="Message must contain text content")

        # Fire and forget — execute in background
        asyncio.create_task(_execute_task(task_id, pid, query))

        logger.info(f"A2A task created: {task_id} → {pid}")
        return {"task_id": task_id, "state": TaskState.SUBMITTED.value}

    # --- Get Task Status ---
    @router.get("/a2a/tasks/{task_id}", dependencies=[Depends(_verify_bearer)])
    async def get_task(task_id: str):
        """Get the current state and messages of a task."""
        task = _store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task

    # --- Send Follow-up Message ---
    @router.post("/a2a/tasks/{task_id}/messages", dependencies=[Depends(_verify_bearer)])
    async def send_message(task_id: str, req: TaskMessageRequest):
        """Send a follow-up message to an existing task.

        If the task is completed or failed, a new persona call is made with
        the full conversation history as context.
        """
        task = _store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if task["state"] == TaskState.CANCELED.value:
            raise HTTPException(status_code=409, detail="Task has been canceled")

        # Store the new message
        parts_raw = [p.model_dump() for p in req.message.parts]
        msg_meta = req.message.metadata or {}
        _store.add_message(task_id, req.message.role, parts_raw, msg_meta)

        query = _extract_text(req.message)
        if not query:
            raise HTTPException(status_code=400, detail="Message must contain text content")

        # Build context from conversation history
        history_lines = []
        for msg in task["messages"]:
            role_label = "USER" if msg["role"] == "user" else "AGENT"
            for part in msg["parts"]:
                if part.get("type") == "text" and part.get("text"):
                    history_lines.append(f"[{role_label}]: {part['text']}")

        context = "\n".join(history_lines)
        full_query = f"Conversation context:\n{context}\n\nNew message:\n{query}"

        # Re-execute with context
        asyncio.create_task(_execute_task(task_id, task["target_persona"], full_query))

        return {"task_id": task_id, "state": TaskState.WORKING.value, "message": "Follow-up received"}

    # --- SSE Stream ---
    @router.get("/a2a/tasks/{task_id}/stream", dependencies=[Depends(_verify_bearer)])
    async def stream_task(task_id: str):
        """Subscribe to Server-Sent Events for task updates.

        Events:
          - state: {"state": "working|completed|failed|canceled"}
          - message: {"role": "agent", "parts": [...], "metadata": {...}}
        """
        task = _store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        with _sse_lock:
            if task_id not in _sse_subscribers:
                _sse_subscribers[task_id] = []
            _sse_subscribers[task_id].append(queue)

        async def event_stream():
            try:
                # Send current state first
                yield f"event: state\ndata: {json.dumps({'state': task['state']})}\n\n"

                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

                        # Terminal states — close stream
                        if event["event"] == "state" and event["data"].get("state") in (
                            "completed", "failed", "canceled"
                        ):
                            break
                    except asyncio.TimeoutError:
                        # SSE keepalive
                        yield f": keepalive\n\n"
            finally:
                with _sse_lock:
                    subs = _sse_subscribers.get(task_id, [])
                    if queue in subs:
                        subs.remove(queue)
                    if not subs:
                        _sse_subscribers.pop(task_id, None)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # --- List Tasks ---
    @router.get("/a2a/tasks", dependencies=[Depends(_verify_bearer)])
    async def list_tasks(limit: int = 50, state: Optional[str] = None):
        """List recent tasks, optionally filtered by state."""
        if state and state not in [s.value for s in TaskState]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state. Must be one of: {', '.join(s.value for s in TaskState)}",
            )
        tasks = _store.list_tasks(limit=limit, state=state)
        return {"tasks": tasks, "count": len(tasks)}

    # --- Cancel Task ---
    @router.post("/a2a/tasks/{task_id}/cancel", dependencies=[Depends(_verify_bearer)])
    async def cancel_task(task_id: str):
        """Cancel a running task."""
        if _store.cancel_task(task_id):
            _notify_subscribers(task_id, "state", {"state": "canceled"})
            return {"task_id": task_id, "state": TaskState.CANCELED.value}
        task = _store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        raise HTTPException(
            status_code=409,
            detail=f"Task is in terminal state: {task['state']}",
        )

    return router


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_a2a_protocol_tools(mcp_server):
    """Register A2A protocol tools with the MCP server.

    Tools:
      - a2a_create_task: Create and dispatch a task to a persona via A2A protocol
      - a2a_task_status: Check the status and messages of an A2A task
      - a2a_list_tasks: List recent A2A tasks with optional state filter
    """
    from pydantic import Field as PField

    @mcp_server.tool(
        name="a2a_create_task",
        annotations={"title": "A2A Protocol — Create Task", "readOnlyHint": False},
    )
    async def a2a_create_task(
        query: str = PField(..., description="The query/instruction for the target persona"),
        target_persona: str = PField("COS", description="Persona ID: COS, A2, A3, A5, A9, CH, A12"),
        metadata_json: str = PField("{}", description="Optional JSON metadata string"),
    ) -> str:
        """Create an A2A protocol task and dispatch it to a Wing persona.

        The task runs asynchronously. Use a2a_task_status to check results.
        External agent systems can also call this via the REST API.
        """
        try:
            meta = json.loads(metadata_json) if metadata_json else {}
        except json.JSONDecodeError:
            meta = {}

        pid = target_persona.upper()
        task_id = _store.create_task(target_persona=pid, metadata=meta)

        parts = [{"type": "text", "text": query}]
        _store.add_message(task_id, "user", parts, meta)

        # Execute synchronously for MCP (caller wants the result)
        try:
            from thunderbird_personas import call_persona, resolve_id

            resolved = resolve_id(pid)
            cap = _PERSONA_CAPABILITIES.get(resolved, {})
            if not cap:
                # Unknown persona — route to COS
                resolved = "COS"
                query = f"[A2A → {pid}] {query}"

            _store.update_state(task_id, TaskState.WORKING)
            result = call_persona(resolved, f"[A2A Protocol] {query}", max_tokens=2000)

            answer = result.get("answer", "")
            response_parts = [{"type": "text", "text": answer}]
            response_meta = {
                "persona": result.get("persona", resolved),
                "persona_name": result.get("name", ""),
                "model": result.get("model", ""),
            }
            _store.add_message(task_id, "agent", response_parts, response_meta)
            _store.update_state(task_id, TaskState.COMPLETED)

            return json.dumps({
                "task_id": task_id,
                "state": "completed",
                "persona": resolved,
                "answer": answer[:1500] + ("..." if len(answer) > 1500 else ""),
            }, indent=2, default=str)

        except Exception as exc:
            _store.update_state(task_id, TaskState.FAILED)
            _store.add_message(task_id, "agent",
                               [{"type": "text", "text": f"Error: {exc}"}],
                               {"error": True})
            return json.dumps({
                "task_id": task_id,
                "state": "failed",
                "error": str(exc),
            }, indent=2)

    @mcp_server.tool(
        name="a2a_task_status",
        annotations={"title": "A2A Protocol — Task Status", "readOnlyHint": True},
    )
    async def a2a_task_status(
        task_id: str = PField(..., description="The A2A task ID (e.g., 'a2a-abc123def456')"),
    ) -> str:
        """Check the status and messages of an A2A protocol task."""
        task = _store.get_task(task_id)
        if not task:
            return json.dumps({"error": f"Task {task_id} not found"})

        # Trim long messages for readability
        trimmed_messages = []
        for msg in task["messages"]:
            trimmed = {**msg}
            for part in trimmed.get("parts", []):
                if part.get("type") == "text" and part.get("text") and len(part["text"]) > 800:
                    part["text"] = part["text"][:800] + "..."
            trimmed_messages.append(trimmed)
        task["messages"] = trimmed_messages

        return json.dumps(task, indent=2, default=str)

    @mcp_server.tool(
        name="a2a_list_tasks",
        annotations={"title": "A2A Protocol — List Tasks", "readOnlyHint": True},
    )
    async def a2a_list_tasks(
        limit: int = PField(20, description="Max tasks to return"),
        state: str = PField("", description="Filter by state: submitted, working, completed, failed, canceled (empty = all)"),
    ) -> str:
        """List recent A2A protocol tasks with optional state filter."""
        filter_state = state if state else None
        tasks = _store.list_tasks(limit=limit, state=filter_state)
        return json.dumps({
            "tasks": tasks,
            "count": len(tasks),
            "filter": filter_state or "all",
        }, indent=2, default=str)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    if "--test" in sys.argv:
        print("A2A Protocol module loads OK")
        card = build_agent_card()
        print(f"Agent card: {card['name']}")
        print(f"Sub-agents: {len(card['sub_agents'])}")
        for sa in card["sub_agents"]:
            ext = " [EXTERNAL]" if sa["accepts_external_tasks"] else ""
            print(f"  {sa['id']}: {sa['name']}{ext}")
        print(f"DB path: {DB_PATH}")
        print(f"Token file: {BEARER_TOKEN_FILE} (exists: {BEARER_TOKEN_FILE.exists()})")

        # Test task store
        tid = _store.create_task("COS", {"test": True})
        _store.add_message(tid, "user", [{"type": "text", "text": "Test query"}])
        _store.update_state(tid, TaskState.COMPLETED)
        task = _store.get_task(tid)
        print(f"\nTest task: {task['task_id']} — state: {task['state']}")
        print(f"Messages: {len(task['messages'])}")

        tasks = _store.list_tasks(limit=5)
        print(f"Total tasks in store: {len(tasks)}")
        print("\nReady.")
        sys.exit(0)

    if "--card" in sys.argv:
        print(json.dumps(build_agent_card(), indent=2))
        sys.exit(0)

    if "--serve" in sys.argv:
        # Standalone test server
        from fastapi import FastAPI
        import uvicorn

        test_app = FastAPI(title="A2A Protocol Test Server")
        test_app.include_router(get_a2a_router())

        port = 8767
        for arg in sys.argv:
            if arg.startswith("--port="):
                port = int(arg.split("=", 1)[1])

        print(f"Starting A2A Protocol test server on :{port}")
        print(f"Agent card: http://localhost:{port}/.well-known/agent.json")
        uvicorn.run(test_app, host="127.0.0.1", port=port, log_level="info")
    else:
        print("Usage:")
        print("  python thunderbird_a2a_protocol.py --test     # Validate module")
        print("  python thunderbird_a2a_protocol.py --card     # Print agent card JSON")
        print("  python thunderbird_a2a_protocol.py --serve    # Run standalone test server")
        sys.exit(0)
