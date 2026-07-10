#!/usr/bin/env python3
"""
core/monitoring/crash_reporter.py — Thunderbird Wing Crash Reporter
Dreams2Memories Travel, LLC · built 2026-07-09

Zero-dependency (stdlib only) crash/exception capture for ALL Wing Python
services, without hand-writing a signal handler or try/except wrapper in
every script. Built after the Telegram gateway restarted ~57x/5 days with
zero diagnostic trail anywhere — no traceback, no signal, nothing.

WHAT install() CATCHES:
  1. Fatal C-level crashes (segfault, abort, bus error, illegal instr, FPE)
     -> faulthandler.enable(), full traceback of all threads, written to a
        persistent per-process log file.
  2. Uncaught exceptions on the MAIN thread -> sys.excepthook override.
  3. Uncaught exceptions on ANY OTHER thread (poll loops, thread pools,
     listener threads) -> threading.excepthook override. sys.excepthook
     does NOT fire for thread exceptions — this is the specific gap that
     hid the telegram-gw incident (D2MC2C/Dani/Relay run as poll threads).
  4. SIGTERM -> logged via faulthandler.register(..., chain=True) BEFORE
     the process exits, then the default terminate behavior still runs.

WHAT IT DOES NOT CATCH (say so, don't imply otherwise):
  - SIGKILL / a hard OOM-kill by the kernel. No process can catch SIGKILL,
    ever. Check `journalctl -k` / dmesg for an OOM marker, or cgroup
    accounting, separately — this module cannot see it.
  - Intentional sys.exit()/os._exit() calls — those are correct exits, not
    crashes, and correctly bypass this module.
  - asyncio Task exceptions that are never awaited/checked. Neither
    sys.excepthook nor threading.excepthook fire for these. Call
    install_asyncio_handler(loop) explicitly for any service with its own
    event loop (e.g. an AgentMail WebSocket listener).

FLEET-WIDE ZERO-TOUCH INSTALL (no per-script edits):
  core/monitoring/sitecustomize.py runs automatically at *every* Python
  interpreter start-up for any process whose PYTHONPATH includes
  core/monitoring — because Python's `site` module auto-imports
  `sitecustomize` if it's importable from sys.path. `deploy/
  thunderbird_pythonpath.env` is already `EnvironmentFile=`-sourced by 51
  systemd units; adding `core/monitoring` to that PYTHONPATH is the single
  fleet-wide switch (done 2026-07-09). Nothing else changes.

PER-SCRIPT FALLBACK (anything NOT started under that env, e.g. a one-off
cron script or an ad-hoc `python3 foo.py`):
    from core.monitoring.crash_reporter import install
    install()

Log location: logs/crash_reports/<script-stem>_<pid>.log — one file per
process invocation, never overwritten. `ls -t logs/crash_reports | head`
shows what died most recently.
"""

from __future__ import annotations

import atexit
import faulthandler
import logging
import os
import signal
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

_INSTALLED = False  # guard: sitecustomize + an explicit import must not double-install

REPO_ROOT = Path(__file__).resolve().parents[2]
CRASH_LOG_DIR = REPO_ROOT / "logs" / "crash_reports"


def _script_stem() -> str:
    try:
        stem = Path(sys.argv[0]).stem
        return stem or "interactive"
    except Exception:
        return "unknown"


def _open_crash_log():
    CRASH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = CRASH_LOG_DIR / f"{_script_stem()}_{os.getpid()}.log"
    # line-buffered (buffering=1) so a segfault mid-write still flushes prior lines
    return open(path, "a", buffering=1), path


def install(logger_name: str = "crash_reporter") -> Optional[Path]:
    """
    Install the full crash-capture surface for this process. Idempotent —
    safe to call from sitecustomize.py AND from a script's own top that
    also imports this module directly.
    """
    global _INSTALLED
    if _INSTALLED:
        return None
    _INSTALLED = True

    fh_file, log_path = _open_crash_log()
    log = logging.getLogger(logger_name)
    # Tracks whether anything worth keeping ever got written. Wing services
    # fire constantly (51 systemd units share this PYTHONPATH) — without
    # this, logs/crash_reports/ would fill with thousands of empty
    # install+clean-exit files from perfectly healthy runs. Only an actual
    # incident (signal dump / exception / SIGTERM) flips this, and only
    # then does the file survive a clean exit.
    _incident = {"happened": False}

    fh_file.write(
        f"=== crash_reporter installed pid={os.getpid()} script={sys.argv[0]!r} "
        f"at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
    )
    fh_file.flush()

    # 1) Fatal C-level signals: SIGSEGV, SIGFPE, SIGABRT, SIGBUS, SIGILL
    faulthandler.enable(file=fh_file, all_threads=True)

    # 2) Uncaught exceptions on the main thread
    _orig_excepthook = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_tb):
        _incident["happened"] = True
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        fh_file.write(f"\n=== UNCAUGHT EXCEPTION (main thread) ===\n{msg}\n")
        fh_file.flush()
        try:
            log.critical("UNCAUGHT EXCEPTION (main thread):\n%s", msg)
        except Exception:
            pass
        _orig_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    # 3) Uncaught exceptions on any OTHER thread. sys.excepthook does NOT
    #    fire here — this is the gap that hid the telegram-gw incident.
    _orig_thread_hook = threading.excepthook

    def _thread_excepthook(args: "threading.ExceptHookArgs"):
        _incident["happened"] = True
        msg = "".join(
            traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        )
        thread_name = args.thread.name if args.thread is not None else "unknown"
        fh_file.write(f"\n=== UNCAUGHT EXCEPTION (thread={thread_name!r}) ===\n{msg}\n")
        fh_file.flush()
        try:
            log.critical("UNCAUGHT EXCEPTION (thread=%s):\n%s", thread_name, msg)
        except Exception:
            pass
        _orig_thread_hook(args)

    threading.excepthook = _thread_excepthook

    # 4) SIGTERM — usually not a Python exception (no traceback to show),
    #    but this is the only way to know "something outside this process
    #    told it to die" (systemd Restart=always stop/restart, a watchdog
    #    issuing `systemctl restart`, an OOM kill under MemoryMax) instead
    #    of a silent restart with zero trace, which is what actually
    #    happened in the telegram-gw incident this module was built for.
    #    chain=True re-runs the default handler afterward so the process
    #    still terminates exactly as it does today — systemd's
    #    Restart=always sees the same exit it always saw.
    try:
        faulthandler.register(signal.SIGTERM, file=fh_file, all_threads=True, chain=True)
    except Exception:
        # register() can fail off the main thread or on unsupported
        # platforms (Windows). Fall back to a plain signal.signal logger
        # that still exits cleanly.
        def _sigterm_handler(signum, frame):
            _incident["happened"] = True
            fh_file.write(
                f"\n=== SIGTERM received pid={os.getpid()} "
                f"at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
            )
            fh_file.flush()
            try:
                log.warning("SIGTERM received — process exiting")
            except Exception:
                pass
            sys.exit(0)

        try:
            signal.signal(signal.SIGTERM, _sigterm_handler)
        except Exception:
            pass  # e.g. not the main thread; nothing more we can do here

    def _mark_clean_exit():
        # If nothing interesting ever happened, don't leave a file behind.
        # With 51 systemd units sharing this PYTHONPATH, an unconditional
        # keep-everything policy would fill logs/crash_reports/ with
        # thousands of empty "installed / clean exit" files from healthy
        # runs. A genuine incident (exception/thread-exception/SIGTERM)
        # already flipped _incident["happened"] above and that file stays.
        # A true crash (segfault) or a SIGTERM caught by faulthandler's own
        # C-level handler terminates the process before atexit can run at
        # all, so this cleanup path never fires for those — they always
        # survive too.
        try:
            if _incident["happened"]:
                fh_file.write(
                    f"=== clean exit pid={os.getpid()} at "
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
                )
                fh_file.flush()
            else:
                fh_file.close()
                try:
                    log_path.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass

    atexit.register(_mark_clean_exit)

    return log_path


def install_asyncio_handler(loop, logger_name: str = "crash_reporter") -> None:
    """
    Call explicitly for any service running its own asyncio event loop
    (e.g. a WebSocket listener). asyncio silently swallows exceptions
    raised inside Tasks that are never awaited/checked — neither
    sys.excepthook nor threading.excepthook see these. This is the asyncio
    equivalent of #3 in install() and is NOT installed automatically.
    """
    log = logging.getLogger(logger_name)
    fh_file, _ = _open_crash_log()

    def _handler(loop, context):
        msg = context.get("message", "asyncio exception")
        exc = context.get("exception")
        if exc is not None:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        else:
            tb = ""
        fh_file.write(f"\n=== ASYNCIO EXCEPTION ===\n{msg}\n{tb}\n")
        fh_file.flush()
        try:
            log.critical("ASYNCIO EXCEPTION: %s\n%s", msg, tb)
        except Exception:
            pass

    loop.set_exception_handler(_handler)


if __name__ == "__main__":
    # Smoke test: install, then immediately raise, to eyeball a real log file.
    p = install()
    print(f"crash_reporter installed. Log: {p}")
    raise RuntimeError("crash_reporter self-test — this is expected")
