AG-BUILD DONE: Added MAX_REPAIR_ATTEMPTS=3 cap, durable state tracking, and escalation routing.

### 1. Test Script and Output
I wrote a test script that dynamically overrides `STATE_PATH` with `tempfile.TemporaryDirectory() / "ci_sentinel_state.json"` to strictly ensure test safety and isolated verification.

**Script:**
```python
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import core.ci.self_observability
from core.ci.self_observability import should_dispatch, MAX_REPAIR_ATTEMPTS

def test_should_dispatch():
    now = datetime.now(timezone.utc)
    unit = "test.service"
    
    with tempfile.TemporaryDirectory() as td:
        temp_state_path = Path(td) / "ci_sentinel_state.json"
        core.ci.self_observability.STATE_PATH = temp_state_path
        
        print(f"MAX_REPAIR_ATTEMPTS = {MAX_REPAIR_ATTEMPTS}")
        
        state = {unit: {"attempts": 0}}
        print(f"Attempts 0: {should_dispatch(unit, state, now)}")
        
        state = {unit: {"attempts": 1}}
        print(f"Attempts 1: {should_dispatch(unit, state, now)}")
        
        state = {unit: {"attempts": 2}}
        print(f"Attempts 2: {should_dispatch(unit, state, now)}")
        
        state = {unit: {"attempts": 3}}
        print(f"Attempts >= 3: {should_dispatch(unit, state, now)}")

if __name__ == "__main__":
    test_should_dispatch()
```

**Output (`python3 /tmp/test_so.py`):**
```text
MAX_REPAIR_ATTEMPTS = 3
Attempts 0: True
Attempts 1: True
Attempts 2: True
Attempts >= 3: False
```

### 2. Compilation and grep check

**Command:**
```bash
python3 -m py_compile /home/john/Thunderbird/core/ci/self_observability.py
grep -c 'MAX_REPAIR_ATTEMPTS' /home/john/Thunderbird/core/ci/self_observability.py
```
**Output:**
```text
4
```
*(Compilation exits 0 with no syntax errors)*

### 3. Git Diff
Here are the changes applied to `core/ci/self_observability.py`:

```diff
diff --git a/core/ci/self_observability.py b/core/ci/self_observability.py
index b5648fbcc..ce1a58c3b 100644
--- a/core/ci/self_observability.py
+++ b/core/ci/self_observability.py
@@ -24,6 +24,7 @@ RESTART_THRESHOLD = 5          # restarts in the unit's lifetime counter delta
 ERROR_THRESHOLD = 100          # journal error/warning lines in the window
 ERROR_WINDOW_MIN = 10
 DISPATCH_COOLDOWN_MIN = 30     # don't re-dispatch a fixer for the same unit within this
+MAX_REPAIR_ATTEMPTS = 3
 
 
 # ---------- pure, testable logic ----------
@@ -43,7 +44,11 @@ def classify(nrestarts: int, errors: int,
 def should_dispatch(unit: str, state: dict, now: datetime,
                     cooldown_min: int = DISPATCH_COOLDOWN_MIN) -> bool:
     """True unless a fixer was dispatched for this unit within the cooldown."""
-    last = state.get(unit, {}).get("last_dispatch")
+    u_state = state.get(unit, {})
+    if u_state.get("attempts", 0) >= MAX_REPAIR_ATTEMPTS:
+        return False
+        
+    last = u_state.get("last_dispatch")
     if not last:
         return True
     dt = datetime.fromisoformat(last)
@@ -128,8 +133,23 @@ def _load_state() -> dict:
     return {}
 
 
-def _save_state(state: dict) -> None:
+def _save_state(state: dict, preserve_disk_attempts: bool = True) -> None:
     STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
+    
+    if preserve_disk_attempts and STATE_PATH.exists():
+        try:
+            with open(STATE_PATH, "r") as f:
+                fcntl.flock(f, fcntl.LOCK_SH)
+                disk_state = json.load(f)
+            for u, disk_u in disk_state.items():
+                if isinstance(disk_u, dict) and "attempts" in disk_u:
+                    if u in state and isinstance(state[u], dict):
+                        state[u]["attempts"] = disk_u["attempts"]
+                    else:
+                        state[u] = {"attempts": disk_u["attempts"]}
+        except Exception:
+            pass
+
     with open(STATE_PATH, "w") as f:
         fcntl.flock(f, fcntl.LOCK_EX)
         f.write(json.dumps(state, indent=2) + "\n")
@@ -263,7 +283,15 @@ def assess(unit: str) -> dict:
     baseline = _load_baseline().get(unit, r["nrestarts"])
     r["restarts_recent"] = max(0, r["nrestarts"] - baseline)
     residual = fuse(r)
-    return {"unit": unit, "resolved": not residual, "residual": residual, "reading": r}
+    resolved = not residual
+    
+    if resolved:
+        st = _load_state()
+        if unit in st and st[unit].get("attempts", 0) > 0:
+            st[unit]["attempts"] = 0
+            _save_state(st, preserve_disk_attempts=False)
+            
+    return {"unit": unit, "resolved": resolved, "residual": residual, "reading": r}
 
 
 ALERT_TIER = "sonnet"          # the alert bird's capability (fix-grade reasoning)
@@ -313,6 +341,18 @@ def dispatch_remediation(breach: dict) -> dict:
     the agent reports it cannot fix (sudo/spend/client-send). Falls back to a cold
     headless spawn if the managed API is unavailable (slow strike beats no strike)."""
     unit = breach["unit"]
+    
+    st = _load_state()
+    u_st = st.setdefault(unit, {})
+    u_st["attempts"] = u_st.get("attempts", 0) + 1
+    _save_state(st, preserve_disk_attempts=False)
+    
+    if u_st["attempts"] >= MAX_REPAIR_ATTEMPTS:
+        msg = f"Max repair attempts ({MAX_REPAIR_ATTEMPTS}) reached for {unit}. Escalate to human."
+        notify_hale("ESCALATE_CAP_HIT", unit, msg)
+        escalate_to_commander(unit, msg)
+        return {"unit": unit, "dispatched": False, "escalate": True, "error": msg}
+
     prompt = _fix_prompt(breach)
     # Primary: scramble the managed-agent alert bird (fast) — under a HARD wall-clock
     # timeout so a hung managed API can never wedge the oneshot sentinel (CRIT-2).
```

**Implementation Note on State Persistence:**
The core vulnerability of integrating into the existing `ci_sentinel.py` loop was that `ci_sentinel` caches the `state` dict in memory at the beginning of the loop and writes it back at the end. Without modifications to `_save_state`, it would have overwritten the attempts set by `dispatch_remediation` with its stale copy. To counteract this, `_save_state` defaults to a `preserve_disk_attempts` overlay merge, protecting the attempt counters from in-memory overwrites by the sentinel script while allowing `dispatch_remediation` and `assess` to write updates directly using `_save_state(..., preserve_disk_attempts=False)`.

Good call on getting a second pair of eyes. This fix will stop the endless bleeding.
