"""
Thunderbird Google Tasks Integration
=====================================
Dreams2Memories Travel, LLC

MCP tools for Google Tasks API:
  - list_task_lists       — show all task lists
  - list_tasks            — tasks in a list (with overdue flagging)
  - create_task           — add a task with optional due date and notes
  - complete_task         — mark a task done
  - delete_task           — remove a task
  - create_client_task    — shortcut: creates a D2M-formatted client follow-up task

Uses unified auth: thunderbird_google_auth.get_tasks()
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from thunderbird_google_auth import get_tasks

logger = logging.getLogger(__name__)

# Default task list name for D2M client follow-ups
D2M_TASK_LIST_NAME = "D2M Client Tasks"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_service():
    return get_tasks()


def _find_list_id(service, list_name: str) -> Optional[str]:
    """Return task list ID by name, or None if not found."""
    result = service.tasklists().list(maxResults=50).execute()
    for tl in result.get("items", []):
        if tl.get("title", "").strip().lower() == list_name.strip().lower():
            return tl["id"]
    return None


def _ensure_d2m_list(service) -> str:
    """Return D2M task list ID, creating it if it doesn't exist."""
    list_id = _find_list_id(service, D2M_TASK_LIST_NAME)
    if list_id:
        return list_id
    result = service.tasklists().insert(body={"title": D2M_TASK_LIST_NAME}).execute()
    logger.info(f"Created task list: {D2M_TASK_LIST_NAME}")
    return result["id"]


def _to_rfc3339(date_str: str) -> str:
    """Convert YYYY-MM-DD to RFC3339 (Tasks API requires time component)."""
    return f"{date_str}T00:00:00.000Z"


def _fmt_task(task: dict) -> dict:
    """Return a clean task dict for MCP output."""
    due = task.get("due", "")
    if due:
        due = due[:10]  # Strip time component for display
    return {
        "id": task.get("id"),
        "title": task.get("title", ""),
        "notes": task.get("notes", ""),
        "status": task.get("status", ""),
        "due": due,
        "completed": task.get("completed", "")[:10] if task.get("completed") else "",
    }


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_tasks_tools(mcp: FastMCP):

    @mcp.tool(
        name="list_task_lists",
        annotations={"title": "List Google Task Lists", "readOnlyHint": True}
    )
    async def list_task_lists() -> str:
        """List all Google Task lists available to the account."""
        try:
            svc = _get_service()
            result = svc.tasklists().list(maxResults=50).execute()
            lists = [
                {"id": tl["id"], "title": tl["title"]}
                for tl in result.get("items", [])
            ]
            return json.dumps({"task_lists": lists, "count": len(lists)}, indent=2)
        except Exception as e:
            logger.error(f"list_task_lists failed: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="list_tasks",
        annotations={"title": "List Tasks", "readOnlyHint": True}
    )
    async def list_tasks(
        list_name: str = Field(D2M_TASK_LIST_NAME, description="Task list name"),
        show_completed: bool = Field(False, description="Include completed tasks"),
        max_results: int = Field(50, description="Max tasks to return", ge=1, le=100),
    ) -> str:
        """List tasks in a task list, flagging overdue items."""
        try:
            svc = _get_service()
            list_id = _find_list_id(svc, list_name)
            if not list_id:
                return json.dumps({"error": f"Task list not found: {list_name}"})

            params = {
                "tasklist": list_id,
                "maxResults": max_results,
                "showCompleted": show_completed,
                "showHidden": show_completed,
            }
            result = svc.tasks().list(**params).execute()
            tasks = result.get("items", [])

            today = datetime.now(timezone.utc).date()
            output = []
            for t in tasks:
                fmt = _fmt_task(t)
                if fmt["due"] and fmt["status"] != "completed":
                    due_date = datetime.strptime(fmt["due"], "%Y-%m-%d").date()
                    fmt["overdue"] = due_date < today
                else:
                    fmt["overdue"] = False
                output.append(fmt)

            overdue_count = sum(1 for t in output if t.get("overdue"))
            return json.dumps({
                "list_name": list_name,
                "tasks": output,
                "count": len(output),
                "overdue": overdue_count,
            }, indent=2)
        except Exception as e:
            logger.error(f"list_tasks failed: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="create_task",
        annotations={"title": "Create Task", "readOnlyHint": False}
    )
    async def create_task(
        title: str = Field(..., description="Task title"),
        list_name: str = Field(D2M_TASK_LIST_NAME, description="Task list name"),
        due_date: Optional[str] = Field(None, description="Due date YYYY-MM-DD"),
        notes: Optional[str] = Field(None, description="Task notes / description"),
    ) -> str:
        """Create a new task in a Google Task list."""
        try:
            svc = _get_service()
            list_id = _find_list_id(svc, list_name)
            if not list_id:
                # Create the list if it doesn't exist
                result = svc.tasklists().insert(body={"title": list_name}).execute()
                list_id = result["id"]
                logger.info(f"Created task list: {list_name}")

            body = {"title": title, "status": "needsAction"}
            if due_date:
                body["due"] = _to_rfc3339(due_date)
            if notes:
                body["notes"] = notes

            task = svc.tasks().insert(tasklist=list_id, body=body).execute()
            return json.dumps({
                "status": "created",
                "task": _fmt_task(task),
                "list_name": list_name,
            }, indent=2)
        except Exception as e:
            logger.error(f"create_task failed: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="complete_task",
        annotations={"title": "Complete Task", "readOnlyHint": False}
    )
    async def complete_task(
        task_id: str = Field(..., description="Task ID (from list_tasks)"),
        list_name: str = Field(D2M_TASK_LIST_NAME, description="Task list name"),
    ) -> str:
        """Mark a task as completed."""
        try:
            svc = _get_service()
            list_id = _find_list_id(svc, list_name)
            if not list_id:
                return json.dumps({"error": f"Task list not found: {list_name}"})

            task = svc.tasks().get(tasklist=list_id, task=task_id).execute()
            task["status"] = "completed"
            task["completed"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

            updated = svc.tasks().update(tasklist=list_id, task=task_id, body=task).execute()
            return json.dumps({
                "status": "completed",
                "task": _fmt_task(updated),
            }, indent=2)
        except Exception as e:
            logger.error(f"complete_task failed: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="delete_task",
        annotations={"title": "Delete Task", "readOnlyHint": False, "destructiveHint": True}
    )
    async def delete_task(
        task_id: str = Field(..., description="Task ID (from list_tasks)"),
        list_name: str = Field(D2M_TASK_LIST_NAME, description="Task list name"),
    ) -> str:
        """Permanently delete a task."""
        try:
            svc = _get_service()
            list_id = _find_list_id(svc, list_name)
            if not list_id:
                return json.dumps({"error": f"Task list not found: {list_name}"})

            svc.tasks().delete(tasklist=list_id, task=task_id).execute()
            return json.dumps({"status": "deleted", "task_id": task_id})
        except Exception as e:
            logger.error(f"delete_task failed: {e}")
            return json.dumps({"error": str(e)})

    @mcp.tool(
        name="create_client_task",
        annotations={"title": "Create D2M Client Follow-Up Task", "readOnlyHint": False}
    )
    async def create_client_task(
        client_name: str = Field(..., description="Client full name"),
        action: str = Field(..., description="What needs to be done"),
        due_date: Optional[str] = Field(None, description="Due date YYYY-MM-DD"),
        booking_id: Optional[str] = Field(None, description="Booking reference if applicable"),
        priority: str = Field("normal", description="Priority: high | normal | low"),
    ) -> str:
        """Create a D2M-formatted client follow-up task in the D2M Client Tasks list.

        Auto-formats title as: [PRIORITY] ClientName — Action
        Notes include booking ID if provided.
        """
        try:
            svc = _get_service()
            list_id = _ensure_d2m_list(svc)

            prefix = {"high": "🔴", "low": "🟢", "normal": "🟡"}.get(priority, "🟡")
            title = f"{prefix} {client_name} — {action}"

            notes_parts = []
            if booking_id:
                notes_parts.append(f"Booking: {booking_id}")
            notes_parts.append(f"Created: {datetime.now().strftime('%Y-%m-%d')}")
            notes = "\n".join(notes_parts) if notes_parts else None

            body = {"title": title, "status": "needsAction"}
            if due_date:
                body["due"] = _to_rfc3339(due_date)
            if notes:
                body["notes"] = notes

            task = svc.tasks().insert(tasklist=list_id, body=body).execute()
            return json.dumps({
                "status": "created",
                "task": _fmt_task(task),
                "list_name": D2M_TASK_LIST_NAME,
            }, indent=2)
        except Exception as e:
            logger.error(f"create_client_task failed: {e}")
            return json.dumps({"error": str(e)})
