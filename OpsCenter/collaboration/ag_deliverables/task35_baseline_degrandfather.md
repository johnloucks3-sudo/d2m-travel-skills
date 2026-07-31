AG-BUILD DONE: Baseline grandfathering removed for target files and worktrees. Scanner correctly updated.

**1. Baseline Entries Check**
```bash
$ python3 -c "import json;d=json.load(open('tests/no_direct_sends_baseline.json'));print('entries:',len(d))"
entries: 2
```

**2. Zero 'worktrees' occurrences**
```bash
$ grep -c "worktrees" tests/no_direct_sends_baseline.json || echo "0 matches"
0 matches
```

**3. Test Failure Output (Expected)**
```bash
$ python3 -m pytest tests/test_no_direct_sends.py -x 2>&1 | tail -20
        new_files = sorted({_file_of(v) for v in current} - baseline_files)
>       assert not new_files, (
            f"\n{len(new_files)} NEW file(s) call {name} directly, bypassing "
            "core/comms/commander_channel.py::notify().\n"
            "Route the message through notify() so it is deduped, rendered, batched to the\n"
            "06:30/18:30 windows, and audited. If this is genuinely a TRANSPORT rather than\n"
            "a caller, add it to ALLOWLIST and say why.\n\n  " + "\n  ".join(new_files)
        )
E       AssertionError: 
E         1 NEW file(s) call Gmail messages().send() directly, bypassing core/comms/commander_channel.py::notify().
E         Route the message through notify() so it is deduped, rendered, batched to the
E         06:30/18:30 windows, and audited. If this is genuinely a TRANSPORT rather than
E         a caller, add it to ALLOWLIST and say why.
E         
E           scripts/morning_brief_engine.py
E       assert not ['scripts/mo..._engine.py']

tests/test_no_direct_sends.py:113: AssertionError
=========================== short test summary info ============================
FAILED tests/test_no_direct_sends.py::test_no_new_direct_sends[gmail-Gmail messages().send()-pattern0]
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
============================== 1 failed in 0.17s ===============================
```

**4. Git Diff Snippets**
```diff
diff --git a/tests/test_no_direct_sends.py b/tests/test_no_direct_sends.py
--- a/tests/test_no_direct_sends.py
+++ b/tests/test_no_direct_sends.py
@@ -41,6 +41,7 @@ ALLOWLIST = {
 EXCLUDE_DIRS = {
     ".git", "node_modules", "__pycache__", ".venv", "venv",
     "archive", "mcps", "Antigravity-x64", ".smart-env",
+    ".claude", "worktrees",
 }
 
 GMAIL_SEND = re.compile(r"messages\(\)\s*\.\s*send\s*\(")
diff --git a/tests/no_direct_sends_baseline.json b/tests/no_direct_sends_baseline.json
--- a/tests/no_direct_sends_baseline.json
+++ b/tests/no_direct_sends_baseline.json
@@ -10,7 +10,6 @@
-  "scripts/morning_brief_engine.py:710: service.users().messages().send(",
-  "scripts/brief_email_sender.py:186: sent = service.users().messages().send(userId=\"me\", body={\"raw\": raw}).execute()",
... (hundreds of duplicate worktrees lines and other target scripts removed)
```
