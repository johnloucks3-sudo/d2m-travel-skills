# HALE BUS INTEGRATION GUIDE

## Overview

The HALE BUS allows all 8 Hale instances to share operational state via JSON. This enables continuity and coordination across:
- Claude Code
- OpenCode
- DeepSeek/Telegram
- Copilot CLI
- Codex
- Gemini CLI
- Browser
- Headless spawns

**Two critical integration points:**
1. **Session startup** (MANDATORY): Load prior state from bus
2. **Session end**: Write current state to bus

---

## 1. SESSION STARTUP (Mandatory)

Wire into `OpsCenter/session_init.py` as the **first operation** after imports.

### Code Pattern

```python
# OpsCenter/session_init.py — TOP of file, after imports

from core.hale_bus.hale_bus_read import load_bus_at_startup

def main():
    """Session initialization — HALE BUS LOAD FIRST."""
    
    # Load inter-Hale state (MANDATORY)
    # Detect instance type from environment or default
    instance_type = os.getenv("HALE_INSTANCE", "claude_code")
    bus_state = load_bus_at_startup(instance_type)
    
    if bus_state:
        print(f"✅ Inter-Hale state loaded: {len(bus_state)} categories")
        # bus_state keys: other_instances, critical_directives, fpd_alerts, handoff_queue
    
    # Continue with rest of session init...
    # ... other initialization ...
```

### What It Does

1. Reads `core/hale_bus/hale_bus_state.json`
2. Prints brief summary of other active instances
3. Loads critical directives (Commander orders)
4. Surfaces FPD (Final Payment Due) alerts
5. Shows handoff queue items for this instance
6. Returns state dict for use in session

### Instance Type Detection

Environment variables to set (context-specific):

```bash
# Claude Code
export HALE_INSTANCE="claude_code"

# OpenCode
export HALE_INSTANCE="opencode"

# Deepseek/Telegram
export HALE_INSTANCE="deepseek_telegram"

# Fallback: "claude_code"
```

---

## 2. SESSION END (Checkpoint)

Wire into your session's **stop hook** (or explicit end-of-session code).

### Code Pattern

```python
# Anywhere in session cleanup/stop hook

from core.hale_bus.hale_bus_write import checkpoint_session

def on_session_end():
    """Session cleanup — HALE BUS WRITE LAST."""
    
    instance_type = os.getenv("HALE_INSTANCE", "claude_code")
    
    # Write state to bus
    checkpoint_session(instance_type)
    print("✅ Session state checkpointed to HALE BUS")
    
    # Continue with other cleanup...
```

### What It Does

1. Reads current `hale_state.json`
2. Extracts open missions and active projects
3. Updates `hale_bus_state.json` with this instance's state
4. Sets `last_seen` timestamp
5. Marks instance as ONLINE (until next session doesn't checkpoint)

---

## 3. SHARED STATE FILE FORMAT

**Path:** `core/hale_bus/hale_bus_state.json`

**Schema:**
```json
{
  "bus_version": "1.0",
  "last_updated": "2026-06-24T21:47:00-06:00Z",
  "source_instance": "claude_code",
  "hale_instances": {
    "claude_code": {
      "status": "ONLINE",
      "last_seen": "2026-06-24T21:47:00-06:00Z",
      "open_missions": ["MISSION-317", "MISSION-318"],
      "active_projects": ["PROJ-MCLEOD-2984034-FPD"],
      "pending_decisions": [],
      "alerts": []
    },
    "opencode": {
      "status": "STANDBY",
      "last_seen": "2026-06-24T20:39:00-06:00Z",
      ...
    },
    ...
  },
  "critical_state": {
    "commander_directives": [...],
    "blocked_work": [],
    "handoff_queue": [...],
    "fpd_alerts": [...]
  },
  "operational_state": {
    "wing_health_summary": {...},
    "last_full_scan": "...",
    "next_scan_due": "..."
  }
}
```

### Key Fields

- **hale_instances** — Status of all 8 instances (ONLINE/STANDBY/OFFLINE)
- **critical_state.commander_directives** — High-priority orders shared across instances
- **critical_state.fpd_alerts** — Final payment due alerts (all instances check these)
- **critical_state.handoff_queue** — Work items queued from one instance to another
- **operational_state** — System health summary

---

## 4. USING BUS DATA IN YOUR CODE

### Check What Other Instances Are Doing

```python
from core.hale_bus import get_other_instances_state

instances = get_other_instances_state(exclude_instance="claude_code")
for inst, state in instances.items():
    print(f"{inst}: {len(state['open_missions'])} missions open")
```

### Get FPD Alerts

```python
from core.hale_bus import get_fpd_alerts

fpds = get_fpd_alerts()
for alert in fpds:
    print(f"⚠️ {alert['client']}: FPD {alert['fpd']} ({alert['days_remaining']}d)")
```

### Check Critical Directives

```python
from core.hale_bus import get_critical_directives

directives = get_critical_directives()
for d in directives:
    if d['status'] == "IN_PROGRESS":
        print(f"🔴 {d['id']}: {d['scope']}")
```

### Get Handoff Queue

```python
from core.hale_bus import get_handoff_queue

handoffs = get_handoff_queue()
for h in handoffs:
    if h['to_instance'] == "claude_code":
        print(f"📋 From {h['from_instance']}: {h['task']}")
```

---

## 5. SECURITY & CONSTRAINTS

**⚠️ NO SECRETS IN THE BUS**

The bus file is world-readable (on shared systems) and passed between instances. Never store:
- API keys
- Passwords
- OAuth tokens
- Client PII (names, addresses, booking refs)

**Allowed content:**
- Mission IDs and project IDs
- Client first names only (paired with mission ID, not full record)
- FPD dates and dollar amounts (generic, not to specific clients)
- Operational status (system health, queue depth)
- Commander directives (high-level scope only)

---

## 6. TROUBLESHOOTING

### Bus file not found at startup

**Symptom:** `⚠️ HALE BUS READ ERROR: [Errno 2] No such file or directory`

**Fix:** Create the directory and initialize the file:
```bash
mkdir -p ~/Thunderbird/core/hale_bus
python3 -c "from core.hale_bus.hale_bus_write import checkpoint_session; checkpoint_session('claude_code')"
```

### Instances showing as OFFLINE

**Symptom:** All instances except current show `status: OFFLINE`

**Cause:** Previous sessions didn't call `checkpoint_session()` at end.

**Fix:** Ensure session end hook includes:
```python
from core.hale_bus.hale_bus_write import checkpoint_session
checkpoint_session(instance_type)
```

### Bus state corrupted or stale

**Reset the bus:**
```bash
rm ~/Thunderbird/core/hale_bus/hale_bus_state.json
python3 -c "from core.hale_bus.hale_bus_write import checkpoint_session; checkpoint_session('claude_code')"
```

---

## 7. ARCHITECTURE REFERENCE

| Component | File | Purpose |
|-----------|------|---------|
| **Read Handler** | `hale_bus_read.py` | Load state at startup (mandatory) |
| **Write Handler** | `hale_bus_write.py` | Checkpoint state at session end |
| **State File** | `hale_bus_state.json` | Shared JSON (all instances read/write) |
| **Package Init** | `__init__.py` | Public API for bus functions |

---

## 8. STANDING ORDER REFERENCE

**Full SO:** `Personas/hale_cos.md` § ACTIVE STANDING ORDERS, item 9

**Binding:** All 8 Hale instances

**Enforcement:** Session init + stop hook

---

*Last updated: 2026-06-24*
*Author: Hale / Thunderbird Wing*
*CI Classification: CRITICAL INFRASTRUCTURE*
