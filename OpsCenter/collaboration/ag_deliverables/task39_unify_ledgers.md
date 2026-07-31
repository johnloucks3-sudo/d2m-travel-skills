# Unify Closure Ledgers

AG-BUILD DONE: Both TCD surfaces now consult and write to the append-only `commander_closures.jsonl` ledger.

## 1. `python3 -m py_compile` Check
```bash
$ python3 -m py_compile tcd/writeback.py tcd/overrides.py core/comms/commander_queue.py
# Exited with code 0
```

## 2. Before/After Intersection Count & Idempotency
The backfill script successfully transferred existing `Closed` status entries from the overrides file into the append-only ledger. Rerunning it was verified to be idempotent.
```
Before intersection count: 0
After intersection count: 94
Idempotency second run added rows: 0
```

## 3. Isolated Temp Stores Test
Verified that a closure via the Sheet path explicitly makes `commander_queue.closed_ids()` aware of the closure, using a strictly isolated temporary environment (overriding `COMMANDER_QUEUE_DATA_ROOT` and mocking the file paths).
```
$ python3 /tmp/task39_isolated_test.py
Closed via Sheet path. commander_queue.closed_ids(): {'test-id-123'}
TEST PASSED: ID is closed in the ledger.
```

## 4. Git Diff
```diff
diff --git a/tcd/overrides.py b/tcd/overrides.py
index 05fa8b4c0..531b5f025 100644
--- a/tcd/overrides.py
+++ b/tcd/overrides.py
@@ -96,5 +96,12 @@ def apply_status(item_id: str, derived_status: str, overrides: dict) -> str:
     reasoning as apply_override for stage. Delete isn't stored here; a
     disposed row's SOURCE is gone, so it stops being collected at all and
     never reaches this function again."""
+    try:
+        from core.comms import commander_queue
+        if commander_queue.is_closed(item_id):
+            return "Closed"
+    except Exception:
+        pass
+
     entry = overrides.get(item_id) or {}
     return entry.get("status") or derived_status
diff --git a/tcd/writeback.py b/tcd/writeback.py
index 1eda0aba1..80fefe288 100644
--- a/tcd/writeback.py
+++ b/tcd/writeback.py
@@ -262,7 +262,14 @@ def _handle_close(row: dict, decisions_path, overrides_path=None, actor: str = "
                    + _gate_note(verdict)),
             decisions_path=decisions_path,
         )
-    _overrides.set_override(row["id"], status="Closed", path=overrides_path)
+    set_override(row["id"], status="Closed", path=overrides_path)
+    
+    try:
+        from core.comms import commander_queue
+        commander_queue.close(row["id"], by="Commander" if actor == "commander" else "system", reason="Closed via TCD writeback")
+    except Exception as e:
+        import logging
+        logging.getLogger(__name__).warning("Failed to record closure in commander_queue for %s: %s", row["id"], e)
```
