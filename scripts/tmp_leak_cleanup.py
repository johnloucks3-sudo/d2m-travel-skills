#!/usr/bin/env python3
"""tmp_leak_cleanup.py -- safe garbage collector for Flatpak-Chrome /tmp cache leak.

CONTEXT (found 2026-07-09, RAZORBACK session -- Sterling/A7):
  /tmp is a 6.7GB tmpfs with usrquota. The Commander's interactive Flatpak Google
  Chrome (bwrap sandbox) leaks V8/shared-memory cache blobs directly into /tmp as
  files named `.{16-hex}-00000000.so` (~13MB ELF shared objects each) instead of
  using /dev/shm -- the sandbox doesn't pass /dev/shm through for this app. Chrome
  mmaps, unmaps, then FAILS TO UNLINK, so they accumulate indefinitely (403 files /
  5.2GB observed) until /tmp fills and ANY /tmp write -- including bash's internal
  temp writes -- fails "Disk quota exceeded". That caused a prior Bash-tool outage.

WHAT THIS DOES:
  Periodically deletes ONLY orphaned leak blobs, with three independent safety gates.
  It NEVER touches the live Chrome process, and never any other /tmp content.

SAFETY GATES (a file is deleted only if ALL pass):
  1. fuser <file> exits non-zero          -> no process holds it open/mmapped (by path)
  2. basename absent from every /proc/*/maps -> namespace-robust backstop (bwrap-safe;
                                                /proc is host-visible for all PIDs)
  3. mtime older than MIN_AGE_SECONDS      -> covers the just-created / about-to-be-
                                                mapped race that fuser can't see yet

  Unlinking a still-mapped tmpfs file does NOT crash Chrome (inode survives until
  unmap), but gate 2 prevents reclaiming a blob Chrome may re-open by name. Gates are
  complementary, not redundant -- fuser catches long-lived maps with old mtimes; the
  age guard catches fresh files fuser hasn't seen mapped yet.

Idempotent. Safe to run anytime, by hand or via timer.
"""
import glob
import logging
import os
import subprocess
import time
from logging.handlers import RotatingFileHandler

# Exact leak signature only -- leading dot + 16 hex + "-00000000.so", maxdepth 1 (no **).
GLOB_PATTERN = "/tmp/.*-00000000.so"
MIN_AGE_SECONDS = 300  # 5 min -- don't touch a blob Chrome may be mid-write / about to map
LOG_PATH = "/home/john/Thunderbird/logs/tmp_leak_cleanup.log"

_maps_cache = None


def _load_all_maps_basenames():
    """Return the raw concatenated text of every readable /proc/<pid>/maps once.

    We substring-match basenames against this. /proc is host-visible for all PIDs
    regardless of the process's mount namespace, so this sees bwrap-sandboxed Chrome
    even if path-based tools (fuser/lsof) are namespace-blind on this system.
    """
    global _maps_cache
    if _maps_cache is not None:
        return _maps_cache
    buf = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/maps", "r") as fh:
                buf.append(fh.read())
        except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
            continue
    _maps_cache = "\n".join(buf)
    return _maps_cache


def _held_by_fuser(path):
    """True if fuser reports ANY process holding the file (exit 0). Rely on exit code
    only, never parse stdout. Plain `fuser <file>` -- NOT `-m` (which would treat the
    arg as the whole tmpfs and always report in-use)."""
    try:
        rc = subprocess.run(
            ["fuser", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        ).returncode
        return rc == 0
    except (subprocess.TimeoutExpired, OSError):
        # Cannot determine -> treat as held (fail safe: do not delete).
        return True


def _mapped_in_proc(path):
    """True if the file's basename appears in any /proc/<pid>/maps (mmapped somewhere)."""
    return os.path.basename(path) in _load_all_maps_basenames()


def main():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logger = logging.getLogger("tmp_leak_cleanup")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3)
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(h)

    now = time.time()
    candidates = glob.glob(GLOB_PATTERN)  # matches dotfiles (pattern begins with '.')

    deleted = 0
    bytes_freed = 0
    skipped_held = 0
    skipped_young = 0

    for path in candidates:
        try:
            st = os.stat(path)
        except FileNotFoundError:
            continue  # raced away
        # Gate 3: age
        if (now - st.st_mtime) < MIN_AGE_SECONDS:
            skipped_young += 1
            continue
        # Gate 1: fuser  &  Gate 2: /proc maps
        if _held_by_fuser(path) or _mapped_in_proc(path):
            skipped_held += 1
            continue
        # All gates passed -> safe to reclaim
        try:
            size = st.st_size
            os.unlink(path)
            deleted += 1
            bytes_freed += size
        except FileNotFoundError:
            continue
        except OSError as e:
            logger.info(f"ERROR unlink {path}: {e}")

    logger.info(
        f"run: candidates={len(candidates)} deleted={deleted} "
        f"freed={bytes_freed / 1_048_576:.1f}MB "
        f"skipped_held={skipped_held} skipped_young={skipped_young}"
    )
    # Also print for journal (systemd captures stdout).
    print(
        f"tmp_leak_cleanup: deleted {deleted} file(s), "
        f"freed {bytes_freed / 1_048_576:.1f}MB, "
        f"skipped {skipped_held} held / {skipped_young} too-young"
    )


if __name__ == "__main__":
    main()
