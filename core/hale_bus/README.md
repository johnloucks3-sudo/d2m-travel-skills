# HALE BUS — Inter-Hale Communication & Coordination

**Status:** ✅ BUILT & DEPLOYED 2026-06-24

**Classification:** CI (Critical Infrastructure)

**Authority:** Commander directive 2026-06-24 (Weapons Free)

---

## What It Does

The HALE BUS enables all 8 Hale instances (Claude Code, OpenCode, DeepSeek, Copilot, Codex, Gemini, Browser, Headless) to **share operational state and coordinate work** via a shared JSON file.

**Every Hale instance:**
- Reads the bus at session startup (mandatory)
- Writes the bus at session end (checkpoint)
- Sees what other instances are working on
- Receives critical directives and alerts
- Picks up handoff work from other instances

**Result:** Continuous operational state across all platforms, no loss of context when switching between instance types.

---

## Architecture

| Component | File | Purpose |
|-----------|------|---------|
| **State Bus** | `hale_bus_state.json` | Shared JSON file (read by all, written by all) |
| **Read Handler** | `hale_bus_read.py` | Load state at session startup |
| **Write Handler** | `hale_bus_write.py` | Checkpoint state at session end |
| **Package Init** | `__init__.py` | Public API for bus functions |
| **Integration Guide** | `INTEGRATION.md` | How to wire into session init + stop hook |
| **Test Suite** | `test_hale_bus.py` | Validation harness |

---

## Quick Start

### For Users

**At session startup:**
```python
from core.hale_bus.hale_bus_read import load_bus_at_startup
load_bus_at_startup("claude_code")  # or your instance type
```

**At session end:**
```python
from core.hale_bus.hale_bus_write import checkpoint_session
checkpoint_session("claude_code")
```

### For Integration

See `INTEGRATION.md` for wiring into:
- `OpsCenter/session_init.py` (startup load)
- Session stop hook (end checkpoint)

---

## State File Format

**Path:** `core/hale_bus/hale_bus_state.json`

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
      "alerts": []
    },
    "opencode": {...},
    ...
  },
  "critical_state": {
    "commander_directives": [...],
    "fpd_alerts": [...],
    "handoff_queue": [...]
  },
  "operational_state": {
    "wing_health_summary": {...},
    "last_full_scan": "...",
    "next_scan_due": "..."
  }
}
```

---

## Key Functions

### Read API

```python
from core.hale_bus import (
    read_bus_state,              # Raw state dict
    get_other_instances_state,   # Other active instances
    get_critical_directives,     # Commander orders
    get_fpd_alerts,              # Final payment due alerts
    get_handoff_queue,           # Work queued for me
    startup_brief,               # Formatted brief
    load_bus_at_startup,         # Full startup load
)
```

### Write API

```python
from core.hale_bus import (
    write_bus_state,             # Write raw state
    read_hale_state,             # Read operational state
    checkpoint_session,          # Full end-of-session write
)
```

---

## Standing Order Binding

**Reference:** `Personas/hale_cos.md` § ACTIVE STANDING ORDERS, item 9

**Binding:** All 8 Hale instances (non-negotiable)

**Enforcement:**
- Session init must call `load_bus_at_startup()` FIRST
- Session end must call `checkpoint_session()` LAST
- No exceptions. No configuration. Always active.

---

## Security Constraints

**⚠️ NO SECRETS IN THE BUS**

The bus file is shared across instances. Store **only**:
- Mission & project IDs
- FPD dates and amounts
- Operational status
- High-level Commander directives

**Never store:**
- API keys, passwords, tokens
- Client PII (names, addresses, booking refs)
- Sensitive financial details

---

## Testing

```bash
# Run test suite
python3 core/hale_bus/test_hale_bus.py

# Expected output:
# ✅ All tests passed!
```

---

## Troubleshooting

### Bus file not found
```bash
mkdir -p ~/Thunderbird/core/hale_bus
python3 -c "from core.hale_bus.hale_bus_write import checkpoint_session; checkpoint_session('claude_code')"
```

### Instances showing OFFLINE
**Cause:** Previous sessions didn't call `checkpoint_session()` at end.

**Fix:** Ensure your stop hook includes the checkpoint call.

### Bus state corrupted
```bash
rm ~/Thunderbird/core/hale_bus/hale_bus_state.json
python3 -c "from core.hale_bus.hale_bus_write import checkpoint_session; checkpoint_session('claude_code')"
```

---

## Implementation Notes

**Design principles:**
1. **Simple.** One JSON file, two Python modules, no external deps.
2. **Mandatory.** No opt-in. Every session loads & writes.
3. **Resilient.** Missing file → fresh init. Corrupt JSON → empty state (non-fatal).
4. **Secure.** No secrets in the bus. Public data only.
5. **Lightweight.** ≤2KB state file. ≤50ms load/write overhead.

**Instance detection:**
- Environment variable: `HALE_INSTANCE`
- Fallback: "claude_code"
- Override in `checkpoint_session(instance_type)` / `load_bus_at_startup(instance_type)`

---

## Future Extensions

Not implemented yet (could be added):
- Encryption for shared systems
- Persistence to cloud (Drive, S3)
- Real-time bus updates (vs. file-based)
- Bus message retention (event log)
- Instance health heartbeat

---

*Built: 2026-06-24*
*Deployed: 2026-06-24*
*Authority: Commander directive (Weapons Free)*
*CI Classification: CRITICAL INFRASTRUCTURE*
