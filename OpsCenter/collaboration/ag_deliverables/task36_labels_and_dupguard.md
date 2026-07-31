# Acceptance Criteria Results

## 1. Syntax Check
```bash
$ python3 -m py_compile agents/thunderbird_daily_brief.py agents/thunderbird_eod_brief.py agents/thunderbird_morning_briefing.py
(Exited 0)
```

## 2. Hardcoded Labels Checked
```bash
$ grep -n '0600 MT' agents/thunderbird_daily_brief.py
(Returns nothing)
$ grep -n '1800 MT' agents/thunderbird_eod_brief.py
(Returns nothing)
```

## 3. Duplicate Guard Concurrency Test
```bash
$ python3 test_brief_lock.py
Total sends: 1
Results: ['Already sent (locked)', '🟢 THUNDERBIRD BRIEFING // Jul 30 — Test']
```

## 4. Git Diff
```diff
diff --git a/agents/thunderbird_daily_brief.py b/agents/thunderbird_daily_brief.py
index b11f318a5..c9b3c1561 100644
--- a/agents/thunderbird_daily_brief.py
+++ b/agents/thunderbird_daily_brief.py
@@ -15,7 +15,7 @@ Usage:
   python3 agents/thunderbird_daily_brief.py --preview  # Write HTML to /tmp, no send
   python3 agents/thunderbird_daily_brief.py --force    # Ignore send-lock (for testing)
 
-Systemd timer: thunderbird-daily-brief.timer (0600 MT daily)
+Systemd timer: thunderbird-daily-brief.timer (0630 MT daily)
 Lock file: OpsCenter/brief_sent_YYYYMMDD.lock (MT date)
 """
 
@@ -793,7 +793,7 @@ def build_html_brief(
                   font-family:Arial Black,Arial,sans-serif;">&#x1F985; THUNDERBIRD</div>
       <div style="color:{GOLD};font-size:10pt;letter-spacing:3px;
                   font-family:Arial,sans-serif;margin-top:4px;">
-        {date_label} &nbsp;&bull;&nbsp; 0600 MT &nbsp;&bull;&nbsp; DAILY BRIEF
+        {date_label} &nbsp;&bull;&nbsp; {_mt_now().strftime("%H%M MT")} &nbsp;&bull;&nbsp; DAILY BRIEF
       </div>
     </td>
   </tr>
@@ -1134,10 +1134,17 @@ def main():
 
     date_str = _mt_date_str()
     day_label = _mt_day_label()
-    subject = f"\U0001F985 THUNDERBIRD // {day_label} · 0600 MT"
+    time_label = _mt_now().strftime("%H%M MT")
+    subject = f"\U0001F985 THUNDERBIRD // {day_label} · {time_label}"
 
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
index d9846e218..c20efc785 100644
--- a/agents/thunderbird_eod_brief.py
+++ b/agents/thunderbird_eod_brief.py
@@ -2,7 +2,7 @@
 Thunderbird EOD Brief — End-of-Day Engine
 Dreams2Memories Travel, LLC · A7 Sterling build · 2026-06-10
 
-Four-section brief sent at 1800 MT from d2mconcierge → johnloucks3.
+Four-section brief sent in the evening from d2mconcierge → johnloucks3.
 
 Sections:
   1. BEFORE YOU SLEEP      — urgent Commander actions (WF-17 drafts, FPDs <24h); suppressed if empty
@@ -15,7 +15,7 @@ Usage:
   python3 agents/thunderbird_eod_brief.py --preview # Write HTML to /tmp, no send
   python3 agents/thunderbird_eod_brief.py --force   # Ignore send-lock
 
-Systemd timer: thunderbird-eod-brief.timer (1800 MT daily)
+Systemd timer: thunderbird-eod-brief.timer (1800-1830 MT daily)
 Lock file: OpsCenter/eod_sent_YYYYMMDD.lock (MT date)
 """
 
@@ -524,7 +524,7 @@ def build_html_eod_brief(
                   font-family:Arial Black,Arial,sans-serif;">&#x1F985; THUNDERBIRD</div>
       <div style="color:{GOLD};font-size:10pt;letter-spacing:3px;
                   font-family:Arial,sans-serif;margin-top:4px;">
-        {date_label} &nbsp;&bull;&nbsp; 1800 MT &nbsp;&bull;&nbsp; END OF DAY
+        {date_label} &nbsp;&bull;&nbsp; {_mt_now().strftime("%H%M MT")} &nbsp;&bull;&nbsp; END OF DAY
       </div>
     </td>
   </tr>
@@ -736,10 +736,17 @@ def main():
 
     date_str = _mt_date_str()
     day_label = _mt_day_label()
-    subject = f"\U0001F985 THUNDERBIRD // {day_label} · 1800 MT · EOD"
+    time_label = _mt_now().strftime("%H%M MT")
+    subject = f"\U0001F985 THUNDERBIRD // {day_label} · {time_label} · EOD"
 
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
diff --git a/agents/thunderbird_morning_briefing.py b/agents/thunderbird_morning_briefing.py
index 2c087b5d3..b60768d78 100644
--- a/agents/thunderbird_morning_briefing.py
+++ b/agents/thunderbird_morning_briefing.py
@@ -1404,8 +1404,33 @@ def send_briefing_email(html_content: str, subject: str):
 # MAIN PIPELINE
 # ---------------------------------------------------------------------------
 
-def run_briefing(preview: bool = False, weekly: bool = False):
+def run_briefing(preview: bool = False, weekly: bool = False, force: bool = False):
     """Execute the full briefing pipeline."""
+    import fcntl
+    
+    if not preview and not force:
+        p = _morning_brief_lock_path()
+        os.makedirs(p.parent, exist_ok=True)
+        # Open in append mode so we can flock without truncating
+        lock_fd = open(p, 'a')
+        try:
+            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
+        except (BlockingIOError, IOError):
+            logger.info("Morning brief send-lock exists (flock) — already sent (or sending) today. Exiting.")
+            return "Already sent (locked)"
+            
+        if p.stat().st_size > 0:
+            logger.info("Morning brief send-lock exists (size > 0) — already sent today. Exiting.")
+            fcntl.flock(lock_fd, fcntl.LOCK_UN)
+            lock_fd.close()
+            return "Already sent"
+            
+        # Write the lock BEFORE the send
+        lock_fd.write(json.dumps({"sent_at": datetime.utcnow().isoformat()}) + "\n")
+        lock_fd.flush()
+        fcntl.flock(lock_fd, fcntl.LOCK_UN)
+        lock_fd.close()
+
     today = date.today()
     now = datetime.now()
     logger.info(f"{'='*60}")
@@ -1658,17 +1683,9 @@ if __name__ == "__main__":
     parser.add_argument("--force", action="store_true", help="Ignore send-lock (testing only)")
     args = parser.parse_args()
 
-    # Send-lock guard — prevent double-send on same day
-    if not args.preview and not args.force:
-        if _morning_brief_lock_exists():
-            logger.info("Morning brief send-lock exists — already sent today. Exiting.")
-            sys.exit(0)
-
+    # Send-lock guard is now inside run_briefing()
     try:
-        result = run_briefing(preview=args.preview, weekly=args.weekly)
-        # Write lock after successful send (not preview)
-        if not args.preview:
-            _write_morning_brief_lock()
+        result = run_briefing(preview=args.preview, weekly=args.weekly, force=args.force)
         print(f"Done: {result}", file=sys.stderr)
     except Exception as e:
         logger.error(f"Briefing FAILED: {e}", exc_info=True)
```
