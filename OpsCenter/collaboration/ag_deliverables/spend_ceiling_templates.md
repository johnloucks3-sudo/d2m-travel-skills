# Article 9 Mandatory Spend Ceiling Implementation & Audit Report

**Author:** Talon (HALE-AG / Antigravity)  
**Recipient:** Ms. Victoria "Victory" Hale (Claude / HALE-CC)  
**Date:** 2026-07-30  
**Status:** COMPLETE & VERIFIED  

---

## Executive Summary

Pursuant to **SO-METERED-SPEND-2026 Article 9**, all dispatched task specifications created via the Wing's task-spec builders (`build_ag_task`, `build_oc_task`, `build_flash_task`) now enforce a mandatory, explicit `spend_ceiling` parameter and automatically prepend a top-level `=== MANDATORY SPEND & ENGINE CONSTRAINTS ===` block to every generated prompt text string.

### Article 9 Mandatory Elements Delivered
1. **Spend Ceiling:** Required parameter `spend_ceiling: str` (no silent default). When set to `'zero'` (or `'0'`, `'zero spend'`, etc.), automatically formats as `zero spend — read-only`.
2. **Forbidden Models / Services:** Dynamically imported from `core.relay.engine_limits` (`POE_BROKEN_VIA_OPENCODE` and non-whitelisted models in `POE_WHITELIST`).
3. **Over-Budget Rule:** Emits the exact instruction: `if this appears to require spend beyond your ceiling, STOP and report`.
4. **Top-Level Placement:** The `CONSTRAINTS` block is prepended at line 1 of every generated prompt string rather than buried mid-body.

---

## File Changes & Exclusion Compliance

- **MODIFIED:** `core/relay/task_templates.py`
- **CREATED:** `tests/test_task_templates_ceiling.py`
- **EXCLUDED (UNTOUCHED):**
  - `core/relay/engine_limits.py` (Not modified)
  - `core/relay/contact_ag.py` (Not modified)
  - `core/relay/dispatch_oc.py` (Not modified)

---

## Verification & Acceptance Output

### 1. Python Syntax Compilation (`py_compile`)
```bash
python3 -m py_compile core/relay/task_templates.py
# Return Code: 0
```

### 2. Pytest Execution Output
```bash
python3 -m pytest tests/test_task_templates_ceiling.py -q
# Output:
# .....                                                                    [100%]
# 5 passed in 0.05s
```

### 3. Verification of Article 9 Constraints & Loud Failures

#### Test Case A: Calling Builder Without `spend_ceiling` Raises Exception
```python
>>> build_ag_task("Test task")
TypeError: build_ag_task() missing 1 required keyword-only argument: 'spend_ceiling'

>>> build_oc_task("Test task", spend_ceiling="")
ValueError: spend_ceiling parameter is required and must be a non-empty string...
```

#### Test Case B: Prompt Generated with `spend_ceiling="zero"`
```python
>>> print(build_ag_task("Analyze repo structure", spend_ceiling="zero"))
=== MANDATORY SPEND & ENGINE CONSTRAINTS ===
SPEND CEILING: zero spend — read-only
FORBIDDEN MODELS / SERVICES: Broken via OpenCode (poe/deepseek-v3.2, poe/gemini-3.1-pro, poe/gemini-3.5-flash, poe/gemini-3.6-flash, poe/google/gemini-3.1-pro, poe/google/gemini-3.5-flash); any Poe model not in whitelist (poe/deepseek-v4-flash-e, poe/empiriolabs/deepseek-v4-flash-el, poe/gemini-3.6-flash).
OVER-BUDGET INSTRUCTION: if this appears to require spend beyond your ceiling, STOP and report.
=============================================

Talon — this is CC, coming to you as a peer.
...
```

---

## Git Diff Output

```diff
diff --git a/core/relay/task_templates.py b/core/relay/task_templates.py
index b30801c46..dfe155123 100644
--- a/core/relay/task_templates.py
+++ b/core/relay/task_templates.py
@@ -15,18 +15,51 @@ opencode-worker.service) has NO PII fence today. build_oc_task() below still
 carries a PII reminder in the prompt text — but that's a courtesy instruction
 to the model, not an enforced fence like the dead module's. Flagged, not
 silently assumed fixed; fencing OC dispatch for real is a separate follow-up.
+
+SO-METERED-SPEND-2026 Article 9: Every task builder requires an explicit
+spend_ceiling parameter and emits a top-level CONSTRAINTS block containing:
+  1. Spend ceiling string (or 'zero spend — read-only')
+  2. Forbidden models/services (imported from engine_limits.py)
+  3. The instruction: 'if this appears to require spend beyond your ceiling, STOP and report'
 """
 from __future__ import annotations
 
 from typing import Optional
 
 from core.silver.gate import is_checkable
+from core.relay.engine_limits import POE_BROKEN_VIA_OPENCODE, POE_WHITELIST
 
 # Same category of tokens the (dead) opencode_worker.py fenced on — kept here
 # as a prompt-level reminder only, not an enforced check (see module docstring).
 _PII_REMINDER_TERMS = ("client names", "email addresses", "booking numbers", "PII")
 
 
+def _build_constraints_block(spend_ceiling: str) -> str:
+    """Build Article 9 CONSTRAINTS block for top of prompt text."""
+    if not spend_ceiling or not isinstance(spend_ceiling, str) or not spend_ceiling.strip():
+        raise ValueError(
+            "spend_ceiling parameter is required and must be a non-empty string "
+            "(e.g., 'zero', 'zero spend — read-only', or explicit point/dollar limit)."
+        )
+
+    cleaned = spend_ceiling.strip()
+    if cleaned.lower() in ("zero", "0", "zero spend", "zero spend - read-only", "zero spend -- read-only", "zero spend — read-only"):
+        ceiling_display = "zero spend — read-only"
+    else:
+        ceiling_display = cleaned
+
+    broken_models = ", ".join(sorted(POE_BROKEN_VIA_OPENCODE))
+    whitelist_models = ", ".join(sorted(POE_WHITELIST))
+
+    return (
+        "=== MANDATORY SPEND & ENGINE CONSTRAINTS ===\n"
+        f"SPEND CEILING: {ceiling_display}\n"
+        f"FORBIDDEN MODELS / SERVICES: Broken via OpenCode ({broken_models}); any Poe model not in whitelist ({whitelist_models}).\n"
+        "OVER-BUDGET INSTRUCTION: if this appears to require spend beyond your ceiling, STOP and report.\n"
+        "============================================="
+    )
+
+
 def _checkability_warning(acceptance_criteria: str) -> str:
     if is_checkable(acceptance_criteria):
         return ""
@@ -41,6 +74,7 @@ def _checkability_warning(acceptance_criteria: str) -> str:
 def build_ag_task(
     task: str,
     *,
+    spend_ceiling: str,
     deliverable_path: Optional[str] = None,
     from_seat: str = "CC",
     verdict_tag: str = "AG",
@@ -51,6 +85,7 @@ def build_ag_task(
     take real ambiguity — thin wrapper around the existing
     contact_ag.peer_prompt(), with a non-blocking checkability warning."""
     from core.relay.contact_ag import peer_prompt
+    constraints = _build_constraints_block(spend_ceiling)
     prompt = peer_prompt(
         task, deliverable_path=deliverable_path, from_seat=from_seat,
         verdict_tag=verdict_tag, strengths=strengths,
@@ -58,12 +93,13 @@ def build_ag_task(
     if acceptance_criteria:
         prompt += f"\n\nAcceptance criteria: {acceptance_criteria}"
         prompt += _checkability_warning(acceptance_criteria)
-    return prompt
+    return f"{constraints}\n\n{prompt}"
 
 
 def build_oc_task(
     task: str,
     *,
+    spend_ceiling: str,
     acceptance_criteria: str,
     deliverable_path: Optional[str] = None,
     steps: Optional[list[str]] = None,
@@ -72,7 +108,10 @@ def build_oc_task(
     but not judgment-capable — ambiguity, not model IQ, is the real risk.
     Numbered bounded steps, explicit absolute output path, explicit
     stop-and-report condition instead of an open-ended judgment call."""
+    constraints = _build_constraints_block(spend_ceiling)
     lines = [
+        constraints,
+        "",
         "OC task — execute the numbered steps exactly. Do not improvise "
         "beyond what's written; if a step is unclear or blocked, STOP and "
         "report why instead of guessing.",
@@ -96,6 +135,7 @@ def build_oc_task(
 def build_flash_task(
     task: str,
     *,
+    spend_ceiling: str,
     acceptance_criteria: str,
     deliverable_path: Optional[str] = None,
     literal_steps: Optional[list[str]] = None,
@@ -111,7 +151,10 @@ def build_flash_task(
             f"(a count, path, ref, or artifact) — got {acceptance_criteria!r}. "
             f"Flash cannot safely fill this gap the way AG/OC might."
         )
+    constraints = _build_constraints_block(spend_ceiling)
     lines = [
+        constraints,
+        "",
         "Flash task — follow the literal steps below exactly, in order. "
         "Every step is either a command to run or exact text to produce. "
         "Do not interpret, summarize, or add anything not listed.",
@@ -125,3 +168,4 @@ def build_flash_task(
         lines.append(f"\nWrite your result to the ABSOLUTE path: {deliverable_path}")
     lines.append(f"\nDONE means exactly: {acceptance_criteria}")
     return "\n".join(lines)
```
