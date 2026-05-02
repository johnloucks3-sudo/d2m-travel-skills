"""
thunderbird_cli_monitor.py
Real-Time CLI Usage Monitor — Phase 2 Project #9
Dreams2Memories Travel, LLC | Thunderbird Wing

Displays live token usage, guard state, and routing status in terminal.

Color rules:
  ✅ NORMAL   — green bars
  ⚠️ WARN     — yellow bars
  🔴 CRIT     — solid red bars (static)
  🚨 STOP     — BLINKING RED bars + bold border
  🔄 ROLLBACK — cyan bars

Run:
  python3 thunderbird_cli_monitor.py          # single snapshot
  python3 thunderbird_cli_monitor.py --watch  # live refresh every 30s
  python3 thunderbird_cli_monitor.py --watch --interval 60
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── ANSI codes ──────────────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
BLINK   = "\033[5m"
RED     = "\033[31m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
CYAN    = "\033[36m"
WHITE   = "\033[37m"
DIM     = "\033[2m"
BG_RED  = "\033[41m"

BLINK_RED  = BLINK + RED + BOLD
SOLID_RED  = RED + BOLD
SOLID_YEL  = YELLOW + BOLD
SOLID_GRN  = GREEN
SOLID_CYN  = CYAN + BOLD

# ── Paths ───────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
STATE_FILE      = THUNDERBIRD_DIR / "config" / "rate_guard_state.json"

# ── Limits ──────────────────────────────────────────────────────────────────────
WEEKLY_LIMIT_ALL    = 680_000_000
SESSION_LIMIT       = 59_826_434
THRESH_WARN         = 70
THRESH_CRIT         = 85
THRESH_STOP         = 90
THRESH_ROLLBACK     = 10

TERMINAL_WIDTH_DEFAULT = 80


def _term_width() -> int:
    try:
        return os.get_terminal_size().columns
    except Exception:
        return TERMINAL_WIDTH_DEFAULT


def _supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


def _bar(pct: float, width: int = 25, color_code: str = "") -> str:
    filled  = min(int(pct / (100.0 / width)), width)
    empty   = width - filled
    if color_code:
        return f"{color_code}{'█' * filled}{RESET}{'░' * empty}"
    return "█" * filled + "░" * empty


def _state_color(state: str) -> str:
    m = {
        "NORMAL":   SOLID_GRN,
        "WARN":     SOLID_YEL,
        "CRIT":     SOLID_RED,
        "STOP":     BLINK_RED,
        "ROLLBACK": SOLID_CYN,
    }
    return m.get(state, WHITE)


def _state_icon(state: str) -> str:
    m = {
        "NORMAL":   "✅",
        "WARN":     "⚠️ ",
        "CRIT":     "🔴",
        "STOP":     "🚨",
        "ROLLBACK": "🔄",
    }
    return m.get(state, "ℹ️")


def _level(pct: float) -> str:
    if pct >= THRESH_STOP:    return "STOP"
    if pct >= THRESH_CRIT:    return "CRIT"
    if pct >= THRESH_WARN:    return "WARN"
    if pct < THRESH_ROLLBACK: return "ROLLBACK"
    return "NORMAL"


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


# ── Data fetchers ───────────────────────────────────────────────────────────────

def _get_weekly() -> dict:
    try:
        r = subprocess.run(
            ["ccusage", "weekly", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return {}
        data  = json.loads(r.stdout)
        weeks = data.get("weekly", [])
        if not weeks:
            return {}
        cur   = weeks[-1]
        total = cur.get("totalTokens", 0)
        pct   = round(total / WEEKLY_LIMIT_ALL * 100, 2)

        opus_tk = sonnet_tk = haiku_tk = 0
        for m in cur.get("modelBreakdowns", []):
            name = m.get("modelName", "")
            tok  = (m.get("inputTokens", 0) + m.get("outputTokens", 0) +
                    m.get("cacheCreationTokens", 0) + m.get("cacheReadTokens", 0))
            if "opus"   in name: opus_tk   += tok
            elif "sonnet" in name: sonnet_tk += tok
            elif "haiku"  in name: haiku_tk  += tok

        return {
            "total":  total,
            "pct":    pct,
            "opus":   opus_tk,
            "sonnet": sonnet_tk,
            "haiku":  haiku_tk,
            "cost":   round(cur.get("totalCost", 0), 2),
            "week":   cur.get("week", "?"),
        }
    except Exception:
        return {}


def _get_session() -> dict:
    try:
        r = subprocess.run(
            ["ccusage", "blocks", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return {}
        blocks = json.loads(r.stdout).get("blocks", [])
        for b in reversed(blocks):
            if b.get("isActive") and not b.get("isGap"):
                total    = b.get("totalTokens", 0)
                proj     = b.get("projection", {}) or {}
                proj_tk  = proj.get("totalTokens", total)
                pct      = round(total / SESSION_LIMIT * 100, 1)
                proj_pct = round(proj_tk / SESSION_LIMIT * 100, 1)
                burn     = b.get("burnRate", {}) or {}
                burn_rpm = round(burn.get("tokensPerMinute", 0) / 1000, 1)
                return {
                    "total":     total,
                    "pct":       pct,
                    "proj_pct":  proj_pct,
                    "burn_k":    burn_rpm,
                    "remain":    round(proj.get("remainingMinutes", 0)),
                    "cost":      round(b.get("costUSD", 0), 2),
                }
        return {}
    except Exception:
        return {}


def _get_guard_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


# ── Render ──────────────────────────────────────────────────────────────────────

def render_snapshot(color: bool = True) -> str:
    weekly  = _get_weekly()
    session = _get_session()
    guard   = _get_guard_state()

    w       = _term_width()
    divider = "─" * min(w, 66)
    now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Determine live state
    live_pct   = weekly.get("pct", 0.0)
    live_level = _level(live_pct)

    # Guard file state (may lag behind by one cycle)
    guard_state     = guard.get("state", live_level)
    degr_active     = guard.get("degradation_active", False)
    degr_mode       = guard.get("degradation_mode", "none")

    # Colors
    c     = _state_color(guard_state) if color else ""
    reset = RESET if color else ""
    bold  = BOLD if color else ""
    dim   = DIM if color else ""

    # Header border — blinks when STOP or CRIT
    border_clr = (BLINK_RED if guard_state == "STOP" else
                  SOLID_RED if guard_state == "CRIT" else
                  SOLID_YEL if guard_state == "WARN" else
                  SOLID_GRN) if color else ""

    bar_color = (BLINK_RED if guard_state in ("STOP", "CRIT") else
                 SOLID_YEL if guard_state == "WARN" else
                 SOLID_CYN if guard_state == "ROLLBACK" else
                 SOLID_GRN) if color else ""

    lines = [
        "",
        f"{border_clr}{'═' * min(w, 66)}{reset}",
        f"{border_clr}  THUNDERBIRD RATE-LIMIT MONITOR   {now}{reset}",
        f"{border_clr}{'═' * min(w, 66)}{reset}",
        "",
    ]

    # Guard state banner
    icon = _state_icon(guard_state)
    lines.append(
        f"  Guard State: {c}{bold}{guard_state}{reset}  {icon}"
        + (f"  {c}{bold}[ DEGRADATION {'PARTIAL' if degr_mode == 'partial' else 'FULL'} ]{reset}"
           if degr_active else "")
    )
    lines.append(f"  {dim}{divider}{reset}")
    lines.append("")

    # Weekly bar
    if weekly:
        remaining = max(0, int(WEEKLY_LIMIT_ALL * (100.0 - live_pct) / 100.0))
        bar = _bar(live_pct, 30, bar_color)
        lines.append(f"  WEEKLY ALL-MODELS   [{bar}{reset}] {c}{bold}{live_pct:.1f}%{reset}")
        lines.append(f"  Used:      {_fmt_tokens(weekly['total'])} / {_fmt_tokens(WEEKLY_LIMIT_ALL)}")
        lines.append(f"  Remaining: {bold}{_fmt_tokens(remaining)}{reset} tokens")
        lines.append(f"  Cost:      ${weekly['cost']:.2f} API equiv")

        # Model mix
        total = weekly["total"] or 1
        opus_pct   = round(weekly["opus"]   / total * 100, 1)
        sonnet_pct = round(weekly["sonnet"] / total * 100, 1)
        haiku_pct  = round(weekly["haiku"]  / total * 100, 1)
        lines.append(
            f"  Mix:       Opus {opus_pct}%  Sonnet {sonnet_pct}%  Haiku {haiku_pct}%"
        )
    else:
        lines.append("  WEEKLY DATA: unavailable (ccusage not responding)")

    lines.append("")

    # Session bar
    if session:
        sp = session["proj_pct"]
        sl = _level(sp)
        sc = (BLINK_RED if sl in ("STOP", "CRIT") else
              SOLID_YEL if sl == "WARN" else
              SOLID_GRN) if color else ""
        sbar = _bar(session["pct"], 30, sc)
        lines.append(f"  SESSION BLOCK (5hr)  [{sbar}{reset}] {sc}{session['pct']:.1f}%{reset}  (proj {sp:.1f}%)")
        lines.append(f"  Burn: {session['burn_k']}K tok/min | ~{session['remain']}min left | ${session['cost']:.2f}")
    else:
        lines.append("  SESSION: no active block detected")

    lines.append("")

    # Routing status
    lines.append(f"  {dim}{divider}{reset}")
    lines.append("  ROUTING STATUS")
    if degr_active:
        if degr_mode == "partial":
            lines.append(f"  {SOLID_YEL if color else ''}  • Non-urgent tasks → OpenRouter DeepSeek{reset}")
            lines.append(f"  {SOLID_GRN if color else ''}  • Urgent/client tasks → Max (preserved){reset}")
        elif degr_mode == "full":
            lines.append(f"  {SOLID_RED if color else ''}  • ALL tasks → OpenRouter DeepSeek{reset}")
            lines.append(f"  {SOLID_RED if color else ''}  • Max SUSPENDED (guard active){reset}")
    else:
        lines.append(f"  {SOLID_GRN if color else ''}  • Normal routing — Max active{reset}")

    # Thresholds reminder
    lines.append("")
    lines.append(f"  {dim}Thresholds: WARN {THRESH_WARN}% | CRIT {THRESH_CRIT}% | STOP {THRESH_STOP}% | ROLLBACK <{THRESH_ROLLBACK}%{reset}")

    # Guard last updated
    last_upd = guard.get("last_updated", "")
    if last_upd:
        lines.append(f"  {dim}Guard last polled: {last_upd[:19]}{reset}")

    lines.append(f"{border_clr}{'═' * min(w, 66)}{reset}")
    lines.append("")

    return "\n".join(lines)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def run_watch(interval: int = 30) -> None:
    color = _supports_color()
    try:
        while True:
            clear_screen()
            print(render_snapshot(color=color))
            print(f"  Refreshing every {interval}s — Ctrl+C to exit")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")


# ── CLI ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thunderbird Rate-Limit CLI Monitor")
    parser.add_argument("--watch",    action="store_true", help="Continuous live refresh")
    parser.add_argument("--interval", type=int, default=30, help="Refresh interval in seconds")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    args = parser.parse_args()

    use_color = _supports_color() and not args.no_color

    if args.watch:
        run_watch(interval=args.interval)
    else:
        print(render_snapshot(color=use_color))
