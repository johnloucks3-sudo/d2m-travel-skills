"""
oc_hygiene — keep the OpenCode lane usable.

THE PROBLEM (measured 2026-07-30)
---------------------------------
`opencode run` either answers in ~25s or blocks FOREVER with zero output. Not
slow — binary. It never errors, never times out from the far side, and prints
nothing at all (not even its own `> build · model` banner), so a caller watching
stdout cannot tell "working" from "dead".

Measured, same model, same task, same repo, minutes apart:

    with other opencode runs live      without them
    s1  400s  hung                     deepseek-v4-flash-free   24s  OK
    s2  400s  hung                     ling-3.0-flash-free      31s  OK
    s3  400s  hung

The only change was killing the other `opencode` processes.

WHAT IS PROVEN
    1. Clearing live `opencode` processes reliably restores fast operation.
    2. Hangs correlate with the number of concurrent `opencode` runs.
    3. `timeout` does NOT orphan the child — tested explicitly, wrapper and
       child both died. An earlier "orphaned process" theory was WRONG and is
       recorded here so nobody rebuilds on it.

WHAT IS INFERRED (not proven — do not state as fact)
    The far side appears to grant a limited number of concurrent slots and to
    QUEUE excess requests indefinitely rather than rejecting them. That fits
    every observation, including the odd one: during a 4-way burst exactly one
    run returned in 25s while its three siblings hung — consistent with a single
    slot freeing and being taken.

WHY IT LOOKED LIKE OTHER THINGS
    This masqueraded as a sandbox problem (it is not — in-repo paths hung too),
    a SQLite lock problem (the write lock was free and freelist_count was 0),
    and a model-quality problem (it is not — the same model scores 3/3 when it
    runs at all). OpenCode's real failure rate today was ~38%, but that was
    process contention, not capability.
"""

import os
import signal
import subprocess
import time

OC_PROC_NAME = "opencode"

# Never run more than this many `opencode` processes at once. Deliberately
# conservative: the cost of waiting is seconds, the cost of exceeding it is a
# run that hangs for the full timeout and produces nothing.
MAX_CONCURRENT = 2

# A run that has outlived this is not going to finish. Healthy runs land in
# 25-210s; every observed hang ran to its full timeout with no output.
STALE_AFTER_S = 300

# How long to wait for a slot before giving up and saying so.
SLOT_WAIT_S = 90
SLOT_POLL_S = 3


def _oc_processes() -> list[tuple[int, int]]:
    """[(pid, age_seconds)] for live `opencode` processes, excluding ourselves.

    Matches the executable name exactly (`pgrep -x`). A substring match would
    also hit the shell command that CONTAINS the word "opencode" — during this
    investigation a `pkill -f "opencode run"` killed its own parent shell.
    """
    me = os.getpid()
    try:
        out = subprocess.run(["pgrep", "-x", OC_PROC_NAME],
                             capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    procs = []
    for line in out.stdout.split():
        try:
            pid = int(line)
        except ValueError:
            continue
        if pid == me:
            continue
        # NEVER touch an interactive (TTY-attached) OpenCode session — that is
        # the Commander's live window, not a dispatch worker. Sweeping it was
        # the "auto-logoff" bug (fixed 2026-08-07). Headless `opencode run`
        # dispatchers are detached (tty '?') and ARE the correct sweep target.
        try:
            tty = subprocess.run(["ps", "-o", "tty=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            tty = ""
        if tty and tty != "?":
            continue
        try:
            age = subprocess.run(["ps", "-o", "etimes=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5)
            procs.append((pid, int(age.stdout.strip() or 0)))
        except Exception:
            procs.append((pid, 0))
    return procs


def sweep_stale(stale_after_s: int = STALE_AFTER_S, *, dry_run: bool = False) -> dict:
    """Kill `opencode` processes older than stale_after_s. Never touches young ones.

    Returns {'killed': [...], 'spared': [...], 'dry_run': bool}. Safe to call
    before every dispatch — with a healthy lane it finds nothing and costs one
    `pgrep`.
    """
    killed, spared = [], []
    for pid, age in _oc_processes():
        if age < stale_after_s:
            spared.append({"pid": pid, "age_s": age})
            continue
        if not dry_run:
            # TERM first; a hung run has no work to lose, but give it the chance
            # to close its DB handle cleanly rather than leaving a hot WAL.
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                continue
            except Exception:
                pass
        killed.append({"pid": pid, "age_s": age})

    if killed and not dry_run:
        time.sleep(3)
        still = {p for p, _ in _oc_processes()}
        for k in killed:
            if k["pid"] in still:
                try:
                    os.kill(k["pid"], signal.SIGKILL)
                    k["escalated"] = "SIGKILL"
                except Exception:
                    pass
    return {"killed": killed, "spared": spared, "dry_run": dry_run}


def wait_for_slot(max_concurrent: int = MAX_CONCURRENT,
                  wait_s: int = SLOT_WAIT_S) -> dict:
    """Block until fewer than max_concurrent `opencode` runs are live.

    Returns {'ok': bool, 'waited_s': int, 'live': int}. ok=False means the lane
    is saturated — the caller should defer rather than pile on, because an
    excess run does not fail fast, it hangs for its whole timeout.
    """
    start = time.time()
    while True:
        live = len(_oc_processes())
        if live < max_concurrent:
            return {"ok": True, "waited_s": int(time.time() - start), "live": live}
        if time.time() - start >= wait_s:
            return {"ok": False, "waited_s": int(time.time() - start), "live": live}
        time.sleep(SLOT_POLL_S)


def before_dispatch(*, max_concurrent: int = MAX_CONCURRENT,
                    stale_after_s: int = STALE_AFTER_S,
                    wait_s: int = SLOT_WAIT_S) -> dict:
    """Call immediately before any `opencode run`. Sweep, then wait for a slot.

    Returns {'ok', 'reason', 'swept', 'slot'}. ok=False means DO NOT DISPATCH.
    """
    swept = sweep_stale(stale_after_s)
    slot = wait_for_slot(max_concurrent, wait_s)
    if not slot["ok"]:
        return {"ok": False,
                "reason": (f"OC lane saturated: {slot['live']} runs live "
                           f"(max {max_concurrent}) after waiting {slot['waited_s']}s. "
                           "Dispatching anyway would hang, not fail."),
                "swept": swept, "slot": slot}
    return {"ok": True, "reason": "", "swept": swept, "slot": slot}


def run_args(cmd: list[str], timeout_s: int) -> dict:
    """kwargs for subprocess.run that kill the whole process GROUP on timeout.

    subprocess.run(cmd, timeout=...) kills only the direct child. Using
    start_new_session + an explicit killpg guarantees nothing survives to hold a
    slot. Belt-and-braces: `timeout` was measured NOT to orphan here, but the
    cost of being wrong is a hung lane, so we do not rely on it.
    """
    return {"args": cmd, "timeout": timeout_s, "start_new_session": True,
            "capture_output": True, "text": True}


def kill_group(proc) -> None:
    """Kill a Popen's entire process group. Use after a TimeoutExpired."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        time.sleep(2)
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    import json
    import sys
    if "--sweep" in sys.argv:
        print(json.dumps(sweep_stale(dry_run="--dry-run" in sys.argv), indent=1))
    else:
        print(json.dumps({"live": _oc_processes(),
                          "check": before_dispatch(wait_s=5)}, indent=1))
