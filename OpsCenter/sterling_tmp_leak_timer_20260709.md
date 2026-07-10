# /tmp Leak Cleanup Timer — Build Status (Sterling / A7)
*2026-07-09 · RAZORBACK session · routine infra hygiene, no Commander gate*

## Problem (found this session)
`/tmp` is a 6.7GB tmpfs with `usrquota`. Flatpak Google Chrome (Commander's interactive
desktop browser, bwrap sandbox) leaks V8/shared-memory cache blobs into `/tmp` as
`.{16-hex}-00000000.so` (~13MB ELF objects) instead of `/dev/shm` — the sandbox doesn't
pass `/dev/shm` through for this app. Chrome mmaps, unmaps, then fails to unlink, so they
accumulate (403 files / 5.2GB observed) until `/tmp` fills and ANY `/tmp` write — including
bash's internal temp writes — fails "Disk quota exceeded". Caused a prior Bash-tool outage.

## What I built
- **`scripts/tmp_leak_cleanup.py`** — idempotent, safe-anytime cleaner. Globs exactly
  `/tmp/.*-00000000.so` (maxdepth 1, no recursion, no other `/tmp` content touched).
  Deletes a file ONLY if it passes all three independent gates:
  1. `fuser <file>` exits non-zero (not held/mmapped by path; exit-code only, no `-m`).
  2. basename absent from every `/proc/*/maps` — namespace-robust backstop (reads `/proc`
     host-side, so it sees the bwrap-sandboxed Chrome even if path tools are namespace-blind).
  3. mtime older than 5 min — covers the just-created / about-to-be-mapped race.
  Logs count + bytes freed to `logs/tmp_leak_cleanup.log` (RotatingFileHandler, 1MB × 3).
- **`~/.config/systemd/user/tmp-leak-cleanup.service`** — Type=oneshot, `Nice=10`,
  journal output. Deliberately **no `PrivateTmp`** (that would isolate `/tmp` and defeat it).
- **`~/.config/systemd/user/tmp-leak-cleanup.timer`** — `OnBootSec=5min`,
  `OnUnitActiveSec=30min`, `Persistent=true`. Enabled + started.

## Verification (live, this session)
- Pre-build positive control: current 7 leak files showed `maps_hit=none` across all
  `/proc/*/maps`, `fuser` exit=1, lsof-by-path empty — confirmed genuine orphans.
- First real run: `candidates=7 deleted=6 freed=77.9MB skipped_held=0 skipped_young=1`.
  The age guard correctly spared the one file with a fresh mtime. `/tmp` count 7 → 1.
- `systemctl --user list-timers` shows `tmp-leak-cleanup.timer` scheduled, next 17:50 MDT,
  30-min cadence, last run 4s ago.

## Chrome / safety confirmation
Did NOT kill, restart, or touch the live Chrome process. Only orphaned garbage blobs
matching the exact filename pattern were removed. Nothing currently in use was deleted
(`skipped_held=0`; the sole young file was retained by the age guard). No other `/tmp`
content was in scope.

## ci_registry.json — SKIPPED (with reasoning)
Not added. `config/ci_registry.json`'s `skills` array is the razor-sharp policy table for
**Wing-critical capabilities** — each entry carries id/access/gate owners, a keeper, a
health-probe path, currency window, reeval cadence, latency SLA, fallback, and a
replacement policy. A garbage-collector timer has none of those semantics, has no external
dependency to keep current, and its failure does not stop the Wing (worst case: `/tmp`
slowly refills, already the pre-existing condition). Registering it would pollute the
registry's meaning. It is ordinary systemd hygiene alongside `cache-cleanup.timer`, which
is likewise not a CI entry. If failure-visibility is ever wanted, the right move is a line
in the daily A7 audit, not a CI-registry row.

*— Sterling, A7*
