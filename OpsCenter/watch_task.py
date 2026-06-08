#!/usr/bin/env python3
"""
watch_task.py — Live token-streaming watcher for headless Claude dispatch tasks.

Watches both the output file (done signal) AND the log file (live stream-json tokens).
Prints each token as Claude generates it — no more "screen with no movement."

Usage:
  python3 OpsCenter/watch_task.py <output_file> <pid>
  python3 OpsCenter/watch_task.py <output_file> <pid> --log-file /path/to/log
  python3 OpsCenter/watch_task.py <output_file> <pid> --timeout 3600
"""

import json
import os
import sys
import time
from pathlib import Path

POLL_INTERVAL   = 0.3     # How fast to poll log file for new tokens (300ms)
HEARTBEAT_EVERY = 15      # Print a heartbeat line if no tokens for this many seconds
DEFAULT_TIMEOUT = 1800


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _fmt_time(secs: float) -> str:
    if secs < 60:
        return f"{int(secs)}s"
    m, s = divmod(int(secs), 60)
    return f"{m}m{s:02d}s"


def _extract_token(line: str) -> str:
    """Extract text delta from a stream-json line. Returns '' if not a text token."""
    try:
        evt = json.loads(line)
        etype = evt.get("type", "")
        # Per-token delta
        if etype == "content_block_delta":
            delta = evt.get("delta", {})
            if delta.get("type") == "text_delta":
                return delta.get("text", "")
        # Complete assistant turn (fallback)
        if etype == "assistant":
            parts = []
            for block in evt.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "".join(parts)
    except (json.JSONDecodeError, KeyError):
        pass
    return ""


def watch(output_file: str, pid: int, log_file: str | None, timeout: int) -> int:
    out   = Path(output_file)
    log   = Path(log_file) if log_file else None
    start = time.monotonic()

    print(f"🤖  Claude dispatched — PID {pid}")
    print(f"    Output → {output_file}")
    if log:
        print(f"    Log    → {log_file}")
    print(f"{'─' * 60}")
    sys.stdout.flush()

    log_pos          = 0
    last_token_time  = time.monotonic()
    chars_on_line    = 0
    printed_any      = False
    heartbeat_count  = 0

    while True:
        elapsed = time.monotonic() - start

        # ── Live token drain from log file ──────────────────────────
        if log and log.exists():
            try:
                with open(log, "r", errors="replace") as fh:
                    fh.seek(log_pos)
                    new_data = fh.read()
                    log_pos  = fh.tell()

                if new_data:
                    for raw_line in new_data.splitlines():
                        tok = _extract_token(raw_line)
                        if tok:
                            sys.stdout.write(tok)
                            sys.stdout.flush()
                            chars_on_line   += len(tok)
                            last_token_time  = time.monotonic()
                            printed_any      = True
                            heartbeat_count  = 0
            except OSError:
                pass

        # ── Done check ──────────────────────────────────────────────
        if out.exists() and out.stat().st_size > 0:
            if printed_any:
                print()  # newline after streaming tokens
            print(f"\n✅  Done in {_fmt_time(elapsed)}")
            print(f"{'─' * 60}")
            # Only print output if no tokens were streamed (avoid double-printing)
            if not printed_any:
                print(out.read_text())
            return 0

        # ── Timeout ─────────────────────────────────────────────────
        if elapsed >= timeout:
            if printed_any:
                print()
            print(f"\n⏱  Timeout after {_fmt_time(elapsed)}")
            print(f"    Check: cat {output_file}")
            return 1

        # ── Heartbeat when no tokens for a while ────────────────────
        silent_for = time.monotonic() - last_token_time
        if silent_for >= HEARTBEAT_EVERY:
            heartbeat_count += 1
            # Newline first so heartbeat doesn't interrupt a partial token line
            if chars_on_line > 0:
                print()
                chars_on_line = 0
            bar_filled = min(20, int((elapsed / 60) * 20))  # fills over ~1 min
            bar = "█" * bar_filled + "░" * (20 - bar_filled)
            print(f"  ⏳ [{bar}] {_fmt_time(elapsed)} — working (PID {pid} alive={_pid_alive(pid)})")
            sys.stdout.flush()
            last_token_time = time.monotonic()  # reset so we don't flood

        time.sleep(POLL_INTERVAL)


def main() -> None:
    args     = sys.argv[1:]
    if len(args) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <output_file> <pid> [--log-file PATH] [--timeout SECS]")

    output_file = args[0]
    pid         = int(args[1])
    log_file    = None
    timeout     = DEFAULT_TIMEOUT

    i = 2
    while i < len(args):
        if args[i] == "--timeout" and i + 1 < len(args):
            timeout = int(args[i + 1])
            i += 2
        elif args[i] == "--log-file" and i + 1 < len(args):
            log_file = args[i + 1]
            i += 2
        else:
            i += 1

    # Auto-detect log file if not provided: look for matching .log next to output
    if not log_file:
        out_path = Path(output_file)
        candidates = [
            out_path.with_suffix(".log"),
            out_path.parent / (out_path.stem + ".log"),
        ]
        for c in candidates:
            if c.exists():
                log_file = str(c)
                break

    sys.exit(watch(output_file, pid, log_file, timeout))


if __name__ == "__main__":
    main()
