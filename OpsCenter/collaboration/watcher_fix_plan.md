# WATCHER DEPENDENCY FIX PLAN
**A7 (Gauge Sterling) — Diagnostic Report**
**Date:** 2026-04-01 | **Task:** WATCHER_DEPENDENCY_FIX

---

## ISSUE / ROOT CAUSE

Goose reported `ModuleNotFoundError: No module named 'watchdog'`. Diagnosis reveals this was a **past error, not current**. The watcher is operational.

**Findings:**

| Check | Result |
|---|---|
| Service interpreter | `/home/john/Thunderbird/.venv/bin/python3` ✅ (correct — venv, not system Python) |
| watchdog installed in venv | `watchdog 6.0.0` ✅ installed and functional |
| `from watchdog.observers import Observer` | Imports cleanly ✅ |
| Service current status | **active (running)** — PID 182207, uptime 9h ✅ |
| Service file config warning | ⚠️ Line 1 of service file is a stray path string (causes harmless "Assignment outside of section" journal warning) |

**Root Cause of Original Error:** The `ModuleNotFoundError` occurred before `watchdog` was installed in the venv. It is now resolved. The service was restarted at 21:35 MDT on 2026-03-31 and has been running cleanly since.

---

## DISCUSSION

The service file at `/home/john/.config/systemd/user/thunderbird-inbox-watcher.service` has its own file path (`~/.config/systemd/user/thunderbird-inbox-watcher.service`) as a literal first line before any `[Unit]` section header. systemd parses this as an assignment outside a section and emits a warning — but ignores it. Service still loads and runs correctly.

This was likely inserted when the file was created with a `cat` heredoc that included the filename as a comment, but without the `#` prefix.

---

## OPTIONS

**Option A (Recommended):** Remove the stray line 1 from the service file. Eliminates journal noise. Low risk — no functional change.

**Option B:** Leave as-is. Service runs fine. Warning is cosmetic only.

---

## ACTIONS

### If the `watchdog` error resurfaces (prevention):

```bash
# Verify watchdog is in the venv
/home/john/Thunderbird/.venv/bin/pip show watchdog

# If missing, install it:
/home/john/Thunderbird/.venv/bin/pip install watchdog

# Restart the service:
systemctl --user restart thunderbird-inbox-watcher

# Confirm it came up clean:
systemctl --user status thunderbird-inbox-watcher
journalctl --user -u thunderbird-inbox-watcher -n 20 --no-pager
```

### Fix the stray service file line (Option A):

```bash
# Remove line 1 (the stray path) from the service file
sed -i '1{/^~\/.config\/systemd/d}' ~/.config/systemd/user/thunderbird-inbox-watcher.service

# Reload systemd daemon to pick up the file change
systemctl --user daemon-reload

# Restart service to confirm clean load
systemctl --user restart thunderbird-inbox-watcher

# Verify — journal warning should be gone
journalctl --user -u thunderbird-inbox-watcher -n 5 --no-pager
```

### Health verification one-liner:

```bash
systemctl --user is-active thunderbird-inbox-watcher && \
  /home/john/Thunderbird/.venv/bin/python3 -c "from watchdog.observers import Observer; print('watchdog OK')" && \
  echo "ALL CLEAR"
```

---

## STATUS

**Watcher: OPERATIONAL.** No immediate action required. Recommend applying Option A (line removal) at next maintenance window to clean journal noise.

— A7 Gauge Sterling
