#!/usr/bin/env python3
"""
slot_router.py — Slot Router CLI + MCP Entry Point
Dreams2Memories Travel, LLC | MISSION-174

Intelligent task dispatcher: classify → route → dispatch → monitor.

CLI Usage:
  python3 slot_router.py route "Research Bergen weather July 2027"
  python3 slot_router.py route "Research Bergen weather" --dry
  python3 slot_router.py status slot_abc12345
  python3 slot_router.py list
  python3 slot_router.py list --status running
  python3 slot_router.py cancel slot_abc12345
  python3 slot_router.py override --type research --model opus [--reason "text"]
  python3 slot_router.py mcp_tools
  python3 slot_router.py mcp_call slot_router_route '{"task": "Research Bergen weather"}'

Anti-recursion: slot_router never routes its own maintenance tasks.
Unknown task types default to research.simple → A2/Sonnet.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure this package directory is on sys.path regardless of invocation CWD
_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from classifier import classify
from routing_table import get_route, get_timeout
from dispatcher import (
    make_task_record,
    dispatch,
    cancel_task,
    _load_tasks,
    _save_task,
)

OVERRIDES_FILE = _HERE / 'overrides.json'

# ─── Anti-recursion guard ─────────────────────────────────────────────────────

_SELF_KEYWORDS = frozenset({
    'slot_router', 'slot router', 'task dispatcher', 'routing table',
    'slot_router.py', 'classifier.py', 'dispatcher.py', 'monitor.py',
})


def _is_self_referential(task_desc: str) -> bool:
    low = task_desc.lower()
    return any(kw in low for kw in _SELF_KEYWORDS)


# ─── Core routing entry point ─────────────────────────────────────────────────

def route_task(task_desc: str, dry_run: bool = False) -> dict:
    """
    Full pipeline: classify → get_route (with overrides) → make_task_record → dispatch.
    Returns the TaskRecord dict.
    dry_run=True skips dispatch and returns the classified+routed record.
    """
    if _is_self_referential(task_desc):
        return {
            'id':     'blocked',
            'status': 'blocked',
            'error':  'Anti-recursion guard: slot_router cannot route its own maintenance tasks. Use direct execution.',
            'task':   task_desc,
        }

    c = classify(task_desc)

    route = get_route(
        task_type=c.task_type,
        complexity=c.complexity,
        task_desc=task_desc,
        subtype=c.subtype,
    )

    record = make_task_record(
        task_desc=task_desc,
        classified_type=c.subtype,
        complexity=c.complexity,
        route=route,
    )
    record['classification_confidence'] = c.confidence

    if dry_run:
        record['status'] = 'dry_run'
        return record

    return dispatch(record, route)


def get_status(task_id: str) -> dict | None:
    return _load_tasks().get(task_id)


def list_tasks(status_filter: str | None = None, limit: int = 20) -> list[dict]:
    tasks = list(_load_tasks().values())
    tasks.sort(key=lambda t: t.get('started_at', ''), reverse=True)
    if status_filter:
        tasks = [t for t in tasks if t.get('status') == status_filter]
    return tasks[:limit]


def apply_override(override_type: str, model: str, reason: str = '') -> dict:
    """Append a type-level override to overrides.json (takes effect immediately)."""
    overrides: dict = {}
    if OVERRIDES_FILE.exists():
        try:
            overrides = json.loads(OVERRIDES_FILE.read_text())
        except json.JSONDecodeError:
            pass

    entry: dict = {'if_type': override_type, 'model': model}
    if reason:
        entry['reason'] = reason

    overrides.setdefault('overrides', []).append(entry)
    OVERRIDES_FILE.write_text(json.dumps(overrides, indent=2))
    return entry


# ─── MCP Tool definitions ─────────────────────────────────────────────────────

MCP_TOOLS = [
    {
        'name': 'slot_router_route',
        'description': (
            'Route a task to the optimal agent+model. '
            'Classifies the task, selects the best agent, dispatches it, and returns task_id + dispatch plan.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'task': {
                    'type': 'string',
                    'description': 'Task description to classify and route',
                },
                'dry_run': {
                    'type': 'boolean',
                    'description': 'If true, classify and plan but do not dispatch',
                    'default': False,
                },
            },
            'required': ['task'],
        },
    },
    {
        'name': 'slot_router_status',
        'description': 'Check the current status of a routed task by task_id.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'task_id': {
                    'type': 'string',
                    'description': 'Task ID returned by slot_router_route (e.g. slot_abc12345)',
                },
            },
            'required': ['task_id'],
        },
    },
    {
        'name': 'slot_router_list',
        'description': 'List recent routed tasks with optional status filter and limit.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'status': {
                    'type': 'string',
                    'enum': ['running', 'success', 'failed', 'escalated', 'cancelled', 'pending', 'dry_run'],
                    'description': 'Filter by task status (omit for all)',
                },
                'limit': {
                    'type': 'integer',
                    'description': 'Max tasks to return (default 20)',
                    'default': 20,
                },
            },
        },
    },
]


def handle_mcp_call(tool_name: str, args: dict) -> dict:
    """Dispatch an MCP tool call. Returns a JSON-serializable result."""
    if tool_name == 'slot_router_route':
        return route_task(args['task'], dry_run=args.get('dry_run', False))
    elif tool_name == 'slot_router_status':
        result = get_status(args['task_id'])
        return result if result else {'error': f"Task not found: {args['task_id']}"}
    elif tool_name == 'slot_router_list':
        return {
            'tasks': list_tasks(
                status_filter=args.get('status'),
                limit=args.get('limit', 20),
            )
        }
    else:
        return {'error': f'Unknown MCP tool: {tool_name}'}


# ─── CLI formatting ───────────────────────────────────────────────────────────

def _fmt_record(record: dict) -> str:
    route = record.get('routed_to', {})
    lines = [
        f"  ID:         {record.get('id')}",
        f"  Status:     {record.get('status')}",
        f"  Type:       {record.get('classified_type')}",
        f"  Complexity: {record.get('complexity')}",
        f"  Confidence: {record.get('classification_confidence', '?')}",
        f"  Agent:      {route.get('agent')}",
        f"  Model:      {route.get('model')}",
        f"  Dispatch:   {route.get('dispatch')}",
        f"  PID:        {record.get('pid')}",
        f"  Output:     {record.get('output_file')}",
        f"  Started:    {record.get('started_at')}",
        f"  Attempts:   {record.get('attempts')}",
    ]
    if record.get('error'):
        lines.append(f"  Error:      {record.get('error')}")
    return '\n'.join(lines)


# ─── CLI entry point ──────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print(__doc__)
        return 1

    cmd = args[0]

    # ── route ──────────────────────────────────────────────────────────────────
    if cmd == 'route':
        remaining = [a for a in args[1:] if a not in ('--dry', '--dry-run')]
        dry = '--dry' in args or '--dry-run' in args
        if not remaining:
            print("Usage: slot_router.py route <task description> [--dry]")
            return 1
        task_desc = ' '.join(remaining)
        record = route_task(task_desc, dry_run=dry)
        tag = 'DRY RUN — ' if dry else ''
        print(f"\nSlot Router — {tag}Dispatched\n{'─' * 52}")
        print(_fmt_record(record))
        print()
        return 0 if record.get('status') not in ('failed', 'blocked') else 1

    # ── status ─────────────────────────────────────────────────────────────────
    elif cmd == 'status':
        if len(args) < 2:
            print("Usage: slot_router.py status <task_id>")
            return 1
        record = get_status(args[1])
        if not record:
            print(f"Task not found: {args[1]}")
            return 1
        print(f"\nTask: {args[1]}\n{'─' * 52}")
        print(_fmt_record(record))
        print()
        return 0

    # ── list ───────────────────────────────────────────────────────────────────
    elif cmd == 'list':
        status_filter = None
        if '--status' in args:
            idx = args.index('--status')
            if idx + 1 < len(args):
                status_filter = args[idx + 1]
        tasks = list_tasks(status_filter=status_filter)
        if not tasks:
            print("No tasks found.")
            return 0
        label = f"({status_filter})" if status_filter else "(all)"
        print(f"\nSlot Router Tasks {label} — {len(tasks)} shown\n{'─' * 72}")
        print(f"  {'ID':20s} {'STATUS':12s} {'TYPE':28s} TASK")
        print(f"  {'─'*20} {'─'*12} {'─'*28} {'─'*30}")
        for t in tasks:
            print(
                f"  {t.get('id',''):20s} "
                f"{t.get('status',''):12s} "
                f"{t.get('classified_type',''):28s} "
                f"{t.get('task','')[:50]}"
            )
        print()
        return 0

    # ── cancel ─────────────────────────────────────────────────────────────────
    elif cmd == 'cancel':
        if len(args) < 2:
            print("Usage: slot_router.py cancel <task_id>")
            return 1
        record = cancel_task(args[1])
        if not record:
            print(f"Task not found: {args[1]}")
            return 1
        print(f"Cancelled: {args[1]}")
        return 0

    # ── override ────────────────────────────────────────────────────────────────
    elif cmd == 'override':
        override_type = None
        model = None
        reason = ''
        i = 1
        while i < len(args):
            if args[i] == '--type' and i + 1 < len(args):
                override_type = args[i + 1]; i += 2
            elif args[i] == '--model' and i + 1 < len(args):
                model = args[i + 1]; i += 2
            elif args[i] == '--reason' and i + 1 < len(args):
                reason = args[i + 1]; i += 2
            else:
                i += 1
        if not override_type or not model:
            print("Usage: slot_router.py override --type <type> --model <model> [--reason <text>]")
            return 1
        entry = apply_override(override_type, model, reason)
        print(f"Override applied to overrides.json: {json.dumps(entry)}")
        return 0

    # ── mcp_tools ──────────────────────────────────────────────────────────────
    elif cmd == 'mcp_tools':
        print(json.dumps(MCP_TOOLS, indent=2))
        return 0

    # ── mcp_call ───────────────────────────────────────────────────────────────
    elif cmd == 'mcp_call':
        if len(args) < 3:
            print("Usage: slot_router.py mcp_call <tool_name> '<json_args>'")
            return 1
        tool_name = args[1]
        mcp_args  = json.loads(args[2])
        result    = handle_mcp_call(tool_name, mcp_args)
        print(json.dumps(result, indent=2))
        return 0

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: route | status | list | cancel | override | mcp_tools | mcp_call")
        return 1


if __name__ == '__main__':
    sys.exit(main())
