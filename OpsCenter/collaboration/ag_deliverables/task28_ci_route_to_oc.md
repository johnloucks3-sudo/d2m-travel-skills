# CI Remediation Routing Fix (Task 28)

**Execution Engine:** AG (Gemini 3.1 Pro High)
**Status:** ⚡ Done

## 1. Syntax Check
```
$ python3 -m py_compile core/ci/self_observability.py
(Exits 0 - successful compilation)
```

## 2. Test Execution
Executed an isolated temp-state monkeypatch test demonstrating behavior across attempts:
```
MAX_REPAIR_ATTEMPTS: 3
Attempt 1 result via: oc_async
Attempt 2 result via: oc_async
Attempt 3 result via: headless_fallback
Attempt 4 result escalate: True
SUCCESS
```

## 3. Wiring Verification
```
$ grep -n 'dispatch_to_oc' core/ci/self_observability.py
377:                from core.relay.dispatch_oc import dispatch_to_oc
379:                res = dispatch_to_oc(
```

## 4. Git Diff
```diff
diff --git a/core/ci/self_observability.py b/core/ci/self_observability.py
index ce1a58c3b..fa09b1ecb 100644
--- a/core/ci/self_observability.py
+++ b/core/ci/self_observability.py
@@ -45,7 +45,7 @@ def should_dispatch(unit: str, state: dict, now: datetime,
                     cooldown_min: int = DISPATCH_COOLDOWN_MIN) -> bool:
     """True unless a fixer was dispatched for this unit within the cooldown."""
     u_state = state.get(unit, {})
-    if u_state.get("attempts", 0) >= MAX_REPAIR_ATTEMPTS:
+    if u_state.get("attempts", 0) > MAX_REPAIR_ATTEMPTS:
         return False
         
     last = u_state.get("last_dispatch")
@@ -347,7 +347,7 @@ def dispatch_remediation(breach: dict) -> dict:
     u_st["attempts"] = u_st.get("attempts", 0) + 1
     _save_state(st, preserve_disk_attempts=False)
     
-    if u_st["attempts"] >= MAX_REPAIR_ATTEMPTS:
+    if u_st["attempts"] > MAX_REPAIR_ATTEMPTS:
         msg = f"Max repair attempts ({MAX_REPAIR_ATTEMPTS}) reached for {unit}. Escalate to human."
         notify_hale("ESCALATE_CAP_HIT", unit, msg)
         escalate_to_commander(unit, msg)
@@ -370,9 +370,35 @@ def dispatch_remediation(breach: dict) -> dict:
                 "escalate": is_escalation(output), "cost_usd": res.get("cost_usd"),
                 "output": output[:1200]}
     except Exception as e:
-        # Fallback: cold headless spawn (detached). Slower, $0 MAX, but it still strikes.
+        # Fallback: route to OC for attempts 1-2, or cold headless spawn (detached) for attempt 3.
+        oc_err = ""
+        if u_st["attempts"] < MAX_REPAIR_ATTEMPTS:
+            try:
+                from core.relay.dispatch_oc import dispatch_to_oc
+                tid = f"ci-fix-{unit}-{u_st['attempts']}"
+                res = dispatch_to_oc(
+                    task=prompt,
+                    acceptance_criteria=f"Service {unit} is no longer crash-looping or error-spiking.",
+                    ticket_id=tid,
+                    task_type="ci-remediation"
+                )
+                return {"unit": unit, "dispatched": True, "via": "oc_async", "ticket_id": res.get("ticket_id")}
+            except Exception as oc_e:
+                oc_err = str(oc_e)
+        
         OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
         out = OUTPUT_DIR / f"fix_{unit.replace('.', '_')}.md"
+        
+        try:
+            from core.staffing.delegation_outcomes import record_outcome
+            record_outcome(
+                seat="CC", action="self_executed", verdict="PENDING",
+                task_type="ci-remediation", dispatch_mode="self",
+                self_execute_rationale=f"Claude fallback: OC failed ({oc_err})" if oc_err else f"Claude fallback: attempt {u_st['attempts']}"
+            )
+        except Exception:
+            pass
+
         try:
             proc = subprocess.Popen(
                 ["python3", DISPATCH_CLAUDE, "--task", f"ci-fix-{unit}",
```
