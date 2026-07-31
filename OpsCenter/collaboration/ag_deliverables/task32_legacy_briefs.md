# AG-BUILD DONE: Legacy Report Scripts Disabled and Guarded

Hale, here is the verification of the requested fixes to stop the legacy report scripts from firing off-schedule.

## 1. Acceptance Criteria Verified

### Compilation Check
```
$ python3 -m py_compile supertimer/bots/ai_exec_bot.py agents/thunderbird_daily_brief.py agents/thunderbird_eod_brief.py
[Exit 0]
```

### Tasks Removed from `ai_exec_bot.py`
```
$ grep -c "daily-brief" supertimer/bots/ai_exec_bot.py
0
$ grep -c "eod-brief" supertimer/bots/ai_exec_bot.py
0
```

### Window Guard Execution Proof
Running the scripts explicitly at 09:10 MT shows the window guards correctly refusing execution and exiting 0 without sending:
```
$ python3 agents/thunderbird_daily_brief.py
2026-07-30 09:10:38,690 INFO Guard refused: time is 09:10, outside 06:30 window. Exiting without sending.
[Exit 0]

$ python3 agents/thunderbird_eod_brief.py
2026-07-30 09:10:38,776 INFO Guard refused: time is 09:10, outside 18:00 window. Exiting without sending.
[Exit 0]
```

## 2. Git Diff
```diff
diff --git a/agents/thunderbird_daily_brief.py b/agents/thunderbird_daily_brief.py
index b11f318a5..09876cca4 100644
--- a/agents/thunderbird_daily_brief.py
+++ b/agents/thunderbird_daily_brief.py
@@ -1138,6 +1138,12 @@ def main():
 
     # ── SEND LOCK CHECK ───────────────────────────────────────────────────────
     if not args.preview and not args.force:
+        now_mt = _mt_now()
+        target = now_mt.replace(hour=6, minute=30, second=0, microsecond=0)
+        if abs((now_mt - target).total_seconds()) > 600:
+            logger.info(f"Guard refused: time is {now_mt.strftime('%H:%M')}, outside 06:30 window. Exiting without sending.")
+            sys.exit(0)
+            
         if _lock_exists(date_str):
             logger.info(f"Send-lock exists for {date_str} — brief already sent today. Exiting.")
             return
diff --git a/agents/thunderbird_eod_brief.py b/agents/thunderbird_eod_brief.py
index d9846e218..cf32ec274 100644
--- a/agents/thunderbird_eod_brief.py
+++ b/agents/thunderbird_eod_brief.py
@@ -740,6 +740,12 @@ def main():
 
     # ── SEND LOCK CHECK ─────────────────────────────────────────────────────
     if not args.preview and not args.force:
+        now_mt = _mt_now()
+        target = now_mt.replace(hour=18, minute=0, second=0, microsecond=0)
+        if abs((now_mt - target).total_seconds()) > 600:
+            logger.info(f"Guard refused: time is {now_mt.strftime('%H:%M')}, outside 18:00 window. Exiting without sending.")
+            sys.exit(0)
+            
         if _lock_exists(date_str):
             logger.info(f"EOD send-lock exists for {date_str} — already sent today. Exiting.")
             return
diff --git a/supertimer/bots/ai_exec_bot.py b/supertimer/bots/ai_exec_bot.py
index fcd385384..f79ae3f96 100644
--- a/supertimer/bots/ai_exec_bot.py
+++ b/supertimer/bots/ai_exec_bot.py
@@ -32,12 +32,6 @@ class AIExecBot(BotBase):
         Task("power-harvest",
              venv("api/thunderbird_power_harvest.py"),
              interval_sec=86400, timeout_sec=600),
-        Task("daily-brief",
-             venv("agents/thunderbird_daily_brief.py"),
-             interval_sec=86400, timeout_sec=300),
-        Task("eod-brief",
-             venv("agents/thunderbird_eod_brief.py"),
-             interval_sec=86400, timeout_sec=300),
         Task("metronome",
              venv("OpsCenter/metronome.py"),
              interval_sec=300, timeout_sec=60),
```

The issue is fully mitigated. The systemd timer wasn't enough because the bot ran them as tasks. Both the tasks have been purged from the active bot roster, and defense-in-depth has been placed onto the individual scripts directly.
