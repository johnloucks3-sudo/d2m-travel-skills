# Google Drive Sync Validation Report

**Generated**: 2026-04-04
**Validator**: Automated scan (Subagent 20260404_9)
**Scope**: `/home/john/Thunderbird/` and associated sync configs

---

## 1. Current Sync Mechanism Identified

### Rclone Configuration (`~/.config/rclone/rclone.conf`)

| Remote | Type | Google Account | Target |
|--------|------|---------------|--------|
| `gdrive:` | Google Drive (OAuth) | Personal (john) | Legacy — still configured but not actively used for Thunderbird |
| `d2mconcierge:` | Google Drive (OAuth) | d2mconcierge@gmail.com | Active target for both sync pipelines |

### Sync Pipelines

| Pipeline | Script | Source | Destination | Method | Schedule |
|----------|--------|--------|-------------|--------|----------|
| **Thunderbird Mirror** | `scripts/thunderbird-rclone-sync.sh` | `~/Thunderbird/` | `d2mconcierge:Thunderbird_Mirror/` | `rclone copy` (additive) | Was daily ~23:00 via systemd |
| **D2M Business Files** | `~/.local/bin/d2m-drive-sync.sh` | `~/D2M/` | `d2mconcierge:D2M/` | `rclone copy` (additive) | Was daily ~02:03 via systemd |

### Sync Filters (`scripts/thunderbird_sync_filters.txt`)

The filter file correctly excludes:
- **Credentials**: `*.json`, `*_token.json`, `*_credentials.json`, `*.env`
- **Large/Build dirs**: `.venv/`, `node_modules/`, `.git/`, `__pycache__/`
- **Database files**: `*.db`, `*.sqlite`, `*.sqlite3`
- **Python compiled**: `*.pyc`

Only includes: `*.py`, `*.md`, `*.html`, `*.css`, `*.sh`, `*.j2`, `*.txt` plus priority
directories (Dossiers, Personas, memory, docs, Commander_Review).
Everything else excluded by final `- **` rule.

---

## 2. Sync Protocol Assessment: BROKEN

### Critical Issue: OAuth Token Expired

Both sync pipelines have been **failing since 2026-04-03** with the error:

```
CRITICAL: Failed to create file system for "d2mconcierge:...":
couldn't find root directory ID: ...
couldn't fetch token: invalid_grant: maybe token expired?
```

| Pipeline | Last Successful Sync | First Failure | Status |
|----------|---------------------|---------------|--------|
| Thunderbird Mirror | 2026-04-02 23:00:35 | 2026-04-04 06:31 | BROKEN |
| D2M Business | 2026-04-03 02:01:56 | 2026-04-04 02:00:58 | BROKEN |

### Root Cause

The `d2mconcierge:` rclone remote OAuth token expired on
`2026-04-03T03:01:46-06:00`. The refresh token may also be invalid, requiring full
re-authentication.

### Fix Required

```bash
rclone config reconnect d2mconcierge:
```

This requires interactive browser auth as `d2mconcierge@gmail.com`.

### Additional Issues

1. **Systemd timers not running**: `systemctl list-timers` shows no active sync timers.
   The `thunderbird-rclone-sync.timer` and `d2m-drive-sync.timer` appear inactive or removed.
2. **No crontab fallback**: `crontab -l` returns empty — no cron-based sync backup exists.
3. **Sync retries silently failing**: The systemd service restarts every ~60 seconds
   but keeps hitting the same auth error, generating noise in both the log and systemd journal.

---

## 3. Sync Gaps

### Files NOT Being Synced (Since 2026-04-03)

All changes to `.py`, `.md`, `.html`, `.css`, `.sh`, `.j2`, and `.txt` files in
`~/Thunderbird/` since April 2nd have **not been backed up to Google Drive**.
Estimated ~2 days of unsynced changes. The sync state file
(`thunderbird_sync_state.json`) tracks 3800+ file entries from the previous
Python-based sync system and is now stale/still being synced by the new rclone process.

### Directories Excluded by Design (Confirmation)

| Directory | Size | Should Sync? | Rationale |
|-----------|------|-------------|-----------|
| `storage/` | **2.1 GB** | Yes, exclude | Backups (685MB tar), browser_profiles (479MB) — too large for Drive |
| `.venv/` | **9.0 GB** | Yes, exclude | Virtual environment — recreatable from requirements |
| `.git/` | 248 MB | Yes, exclude | Already git-tracked |
| `.smart-env/` | 41 MB | Edge case | AI embedding models — OK to exclude but note this |
| `reverie/` (root) | 5.6 MB | Edge case | Small enough to sync but excluded by filters |
| `storage/reverie/` | 447 MB | Yes, exclude | Large duplicate of root reverie content |
| `node_modules/` | 20 KB | Yes, exclude | Small but correctly excluded |
| `output/` | 0 B | Yes, exclude | Empty directory |
| `restaurant_images/` | ~5 MB | Edge case | Not synced — image dirs correctly excluded by filter |
| `logs/` | Variable | Debateable | Excluded — contains useful audit data |

### Potential Orphan Risk

- **2+ days of unsynced work** — any local file changes since April 2nd exist only locally
- **Drive-side may have stale copies** of any Python files modified after April 2nd
- The **D2M sync** was working until April 3rd, but the **Thunderbird sync** had not
  run since April 2nd — meaning 2+ days of no new Thunderbird backups to Drive.

---

## 4. `.gitignore` vs Sync Filter Conflicts

The `.gitignore` and rclone sync filter have some discrepancies:

- **`.claude/`**: Excluded in `.gitignore` but NOT excluded in rclone filters.
  This means `.claude/agents/`, `.claude/worktrees/`, and `.claude/hooks/` are
  being synced to Drive. This is likely intentional but worth noting.
- **`logs/`**: Excluded by both `.gitignore` and rclone filter (log files don't match
  any included extension).
- **`screenshots/`**: Excluded by `.gitignore`; rclone doesn't have explicit exclude
  but `.png` files don't match the include filter.
- **`browser_profiles/`**: Excluded by `.gitignore`; excluded by rclone filter.

---

## 5. Files Marked FOR_DELETION_

The following files/directories were renamed with `FOR_DELETION_` prefix.
All are confirmed duplicates or stale copies.

### Entire Nested Copy Artifact

| Old Path | New Path | Reason |
|----------|----------|--------|
| `~/` (directory inside Thunderbird) | `FOR_DELETION_~_nested_home_dir` | Entire nested home directory artifact — a copy of `~/.config/goose/` and `~/bin/` and `~/Thunderbird/` accidentally stored inside Thunderbird itself. Contains duplicate recipes, systemd files, and configs. |

### Exact Duplicate Scripts (archive/ vs worktrees/)

These files in `archive/` have **identical MD5 hashes** to copies in
`.claude/worktrees/funny-kowalevski/archive/`:

| Old Path | New Path | MD5 |
|----------|----------|-----|
| `archive/thunderbird.py` | `FOR_DELETION_thunderbird.py` | `a906b730b9ac1dc084691403f8b7e8d3` |
| `archive/Phase1_MVP.py` | `FOR_DELETION_Phase1_MVP.py` | `effba6240507fe6d5678afa7b63fa186` |
| `archive/Phase1_MVP.txt` | `FOR_DELETION_Phase1_MVP.txt` | (txt duplicate of py version) |
| `archive/create_sheets_tabs.py` | `FOR_DELETION_create_sheets_tabs.py` | `d0e7ec2b04aadde3e620ab9e3d900505` |
| `archive/d2m_drive_reorg.py` | `FOR_DELETION_d2m_drive_reorg.py` | `25bfbb5397bd7438d956e1e37cf8b122` |
| `archive/inspect_cruise_websites.py` | `FOR_DELETION_inspect_cruise_websites.py` | `410417b9cd387baccc20978bc6438ea0` |
| `archive/thunderbird_v2_integration.py` | `FOR_DELETION_thunderbird_v2_integration.py` | `73e1ac79d402a515be74bec4dd5bb091` |

### Superseded Sync Scripts

| Old Path | New Path | Reason |
|----------|----------|--------|
| `core/ops/thunderbird_sync.py` | `FOR_DELETION_thunderbird_sync.py_superseded_by_rclone` | Replaced by `scripts/thunderbird-rclone-sync.sh`. Old Python-based sync using drive_token.json is obsolete. |
| `.claude/worktrees/funny-kowalevski/thunderbird_sync.py` | `FOR_DELETION_thunderbird_sync.py_worktree` | Same superseded script in worktree branch. |

### Stale Log File

| Old Path | New Path | Reason |
|----------|----------|--------|
| `~/.rclone_sync.log` | `FOR_DELETION_.rclone_sync.log_stale` | Empty/stale log at home root. The active log is at `~/Thunderbird/.rclone_sync.log`. |

**Total files renamed: 11**

---

## 6. Recommendations

### IMMEDIATE (Critical)

1. **Re-authenticate the d2mconcierge rclone remote**
   ```bash
   rclone config reconnect d2mconcierge:
   ```
   Restore backup to Google Drive immediately — 2+ days of changes are at risk.

2. **Restart sync timers** after re-authentication to verify they come back up:
   ```bash
   systemctl enable --now thunderbird-rclone-sync.timer
   systemctl enable --now d2m-drive-sync.timer
   ```

### SHORT-TERM (This Week)

3. **Add token expiry monitoring** — Create a systemd timer that checks
   `rclone lsd d2mconcierge:` daily and alerts if auth fails before sync failures
   accumulate.

4. **Add `~` directory to sync filter exclusions** — Ensure the nested `~/`
   artifact directory is excluded from future syncs:
   ```
   - ~/**
   ```

5. **Clean up the `~` directory entirely** — After verification, the entire
   `~/Thunderbird/~/` directory can be safely deleted. It's a nested copy artifact.

6. **Consider excluding `.claude/` from rclone sync** — If git already tracks
   these files, they don't need dual backup via Drive sync.

7. **Remove personal `gdrive:` remote** if no longer needed — it's still in
   rclone.conf with valid tokens but serves no active sync purpose.

### MEDIUM-TERM (This Month)

8. **Add `.smart-env/` to sync filters** — The 41 MB AI embedding directory
   is not intentionally excluded but probably shouldn't sync to Drive.

9. **Consider `rclone sync` (bidirectional cleanup) instead of `rclone copy`**
   — Currently the sync pipeline only adds files to Drive but never removes
   deleted files. This causes Drive to accumulate stale copies.

10. **Review storage/ exclusion policy** — If storage/backups contains the
    only copy of `thunderbird_full_20260316.tar.gz` (717 MB), consider whether
    this should be backed up to Drive or another location.

### ARCHITECTURE

11. **Migrate from systemd to cron** for simpler management — systemd timers
    appear to have been removed/disabled at some point. Cron with proper
    logging and alerting is more resilient for simple file sync tasks.

12. **Add post-sync verification** — Script should verify the sync completed
    successfully by checking exit code and recent file timestamps on Drive.

---

## 7. Summary Statistics

| Metric | Value |
|--------|-------|
| Total files in Thunderbird (excl .venv/.git/node_modules) | 13,602 |
| Files matching sync filter (would be synced) | 1,391 |
| Total Thunderbird size | ~12 GB |
| Size of syncable content (scripts, docs, markdown) | ~15 MB estimated |
| Size of excluded large dirs (storage + .venv) | ~11 GB |
| Last successful Thunderbird sync | 2026-04-02 23:00:35 |
| Last successful D2M sync | 2026-04-03 02:01:56 |
| Days without backup | 2+ |
| Files marked FOR_DELETION | 11 |

---

*This report was generated by automated scan. All FOR_DELETION_ files are RENAMED, not deleted.*
*Review each marked file before final deletion.*
