"""
routing_table.py — Routing Table + Escalation Protocol for Slot Router
Dreams2Memories Travel, LLC

Maps (task_type, complexity) -> {agent, model, dispatch}.
Supports runtime overrides read from overrides.json.
Escalation levels: retry -> upgrade model -> notify Hale -> notify Commander.
"""

import json
import sys
from datetime import date
from pathlib import Path

OVERRIDES_FILE = Path(__file__).parent / 'overrides.json'

# ─── Core routing table ───────────────────────────────────────────────────────

ROUTING_TABLE: dict[tuple[str, str], dict] = {
    ('research', 'simple'):   {'agent': 'A2',          'model': 'sonnet', 'dispatch': 'ask'},
    ('research', 'medium'):   {'agent': 'A2',          'model': 'sonnet', 'dispatch': 'ask'},
    ('research', 'complex'):  {'agent': 'A2',          'model': 'opus',   'dispatch': 'ask-opus'},
    ('research', 'critical'): {'agent': 'A2+A5',       'model': 'opus',   'dispatch': 'ask-opus'},

    ('build',    'simple'):   {'agent': 'Sterling',    'model': 'sonnet', 'dispatch': 'ask'},
    ('build',    'medium'):   {'agent': 'Sterling',    'model': 'sonnet', 'dispatch': 'ask'},
    ('build',    'complex'):  {'agent': 'Sterling',    'model': 'opus',   'dispatch': 'ask-opus'},
    ('build',    'critical'): {'agent': 'Sterling+A5', 'model': 'opus',   'dispatch': 'ask-opus'},

    ('draft',    'simple'):   {'agent': 'Dani',        'model': 'sonnet', 'dispatch': 'ask'},
    ('draft',    'medium'):   {'agent': 'Dani',        'model': 'sonnet', 'dispatch': 'ask'},
    ('draft',    'complex'):  {'agent': 'Dani',        'model': 'sonnet', 'dispatch': 'ask'},
    ('draft',    'critical'): {'agent': 'Dani',        'model': 'sonnet', 'dispatch': 'ask'},

    ('validate', 'simple'):   {'agent': 'Harlan',      'model': 'sonnet', 'dispatch': 'ask'},
    ('validate', 'medium'):   {'agent': 'Harlan',      'model': 'sonnet', 'dispatch': 'ask'},
    ('validate', 'complex'):  {'agent': 'Harlan',      'model': 'opus',   'dispatch': 'ask-opus'},
    ('validate', 'critical'): {'agent': 'Harlan',      'model': 'opus',   'dispatch': 'ask-opus'},

    # decide always goes to Commander via Telegram
    ('decide',   'simple'):   {'agent': 'Commander',   'model': 'n/a',    'dispatch': 'telegram'},
    ('decide',   'medium'):   {'agent': 'Commander',   'model': 'n/a',    'dispatch': 'telegram'},
    ('decide',   'complex'):  {'agent': 'Commander',   'model': 'n/a',    'dispatch': 'telegram'},
    ('decide',   'critical'): {'agent': 'Commander',   'model': 'n/a',    'dispatch': 'telegram'},

    # monitor runs local scripts/watchers
    ('monitor',  'simple'):   {'agent': 'A3',          'model': 'sonnet', 'dispatch': 'script'},
    ('monitor',  'medium'):   {'agent': 'A3',          'model': 'sonnet', 'dispatch': 'script'},
    ('monitor',  'complex'):  {'agent': 'A3',          'model': 'sonnet', 'dispatch': 'script'},
    ('monitor',  'critical'): {'agent': 'A3',          'model': 'sonnet', 'dispatch': 'script'},

    ('maintain', 'simple'):   {'agent': 'Sterling',    'model': 'sonnet', 'dispatch': 'ask'},
    ('maintain', 'medium'):   {'agent': 'Sterling',    'model': 'sonnet', 'dispatch': 'ask'},
    ('maintain', 'complex'):  {'agent': 'Sterling',    'model': 'opus',   'dispatch': 'ask-opus'},
    ('maintain', 'critical'): {'agent': 'Sterling',    'model': 'opus',   'dispatch': 'ask-opus'},
}

# Unknown task type fallback
DEFAULT_ROUTE: dict = {'agent': 'A2', 'model': 'sonnet', 'dispatch': 'ask'}

# ─── Escalation protocol ──────────────────────────────────────────────────────

ESCALATION: dict[int, dict] = {
    1: {'on': 'failure',        'action': 'retry_same',       'max_attempts': 2},
    2: {'on': 'double_failure', 'action': 'upgrade_model',    'from': 'sonnet', 'to': 'opus'},
    3: {'on': 'opus_failure',   'action': 'notify_hale',      'channel': 'telegram'},
    4: {'on': 'timeout',        'action': 'notify_commander', 'channel': 'telegram'},
}

# Timeout in seconds by complexity
TIMEOUT_BY_COMPLEXITY: dict[str, int] = {
    'simple':   600,    # 10 min
    'medium':   1200,   # 20 min
    'complex':  1800,   # 30 min
    'critical': 2400,   # 40 min
}


def _load_overrides() -> dict:
    if not OVERRIDES_FILE.exists():
        return {}
    try:
        return json.loads(OVERRIDES_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def get_route(
    task_type: str,
    complexity: str,
    task_desc: str = '',
    subtype: str = '',
) -> dict:
    """
    Returns the routing dict for (task_type, complexity).
    Applies keyword/client and temporal overrides from overrides.json.
    Falls back to research.simple DEFAULT_ROUTE for unknown types.
    """
    base = ROUTING_TABLE.get((task_type, complexity), DEFAULT_ROUTE)
    route = dict(base)

    overrides = _load_overrides()
    task_lower = task_desc.lower()
    today = date.today().isoformat()

    # ── Keyword / type / client overrides ──
    for override in overrides.get('overrides', []):
        if_type    = override.get('if_type')
        if_subtype = override.get('if_subtype', '')
        if_client  = override.get('if_client', '')

        type_match    = (if_type == task_type)    if if_type    else True
        subtype_match = (if_subtype in subtype)   if if_subtype else True
        client_match  = (if_client.lower() in task_lower) if if_client else True

        if type_match and subtype_match and client_match:
            for key in ('model', 'agent', 'dispatch'):
                if key in override:
                    route[key] = override[key]

    # ── Temporal overrides (date-range) ──
    for tov in overrides.get('temporal_overrides', []):
        valid_from = tov.get('valid_from', '')
        valid_to   = tov.get('valid_to', '9999-12-31')
        if valid_from <= today <= valid_to:
            all_override = tov.get('all', {})
            for key in ('model', 'agent', 'dispatch'):
                if key in all_override:
                    route[key] = all_override[key]

    # Sync dispatch with model — if model was bumped to opus, ensure dispatch follows
    if route.get('model') == 'opus' and route.get('dispatch') == 'ask':
        route['dispatch'] = 'ask-opus'

    return route


def upgrade_route(route: dict) -> dict:
    """Escalation level 2: upgrade route from sonnet → opus."""
    upgraded = dict(route)
    if upgraded.get('model') == 'sonnet':
        upgraded['model'] = 'opus'
        upgraded['dispatch'] = 'ask-opus'
    return upgraded


def get_timeout(complexity: str) -> int:
    return TIMEOUT_BY_COMPLEXITY.get(complexity, 600)


if __name__ == '__main__':
    print("Routing Table\n" + "─" * 60)
    for (t, c), r in ROUTING_TABLE.items():
        print(f"  ({t:10s}, {c:8s}) → agent={r['agent']:14s} model={r['model']:7s} dispatch={r['dispatch']}")
