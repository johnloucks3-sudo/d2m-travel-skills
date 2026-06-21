#!/usr/bin/env python3
"""
CI DAILY ROUTINE — cadence governor
===================================
Dreams2Memories Travel, LLC · SO_TECH_VANGUARD_ELEVATION_20260621

Commander directive 2026-06-21: run the CI health check DAILY until it reports
100% RAZOR_SHARP for 7 consecutive days, then drop to WEEKLY. Any sub-100% day
resets the streak and holds daily.

Runs the razor-sharp sweep, records the day's result + streak, pages on
degradation (via ci_sweep's own pager), and — once 7 consecutive perfect days
are banked — rewrites ci-sweep.timer to weekly. Idempotent per day.

State: OpsCenter/state/ci_routine_state.json
Exit 0 always (cadence governor; sweep-level paging handled inside).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.ci_health import sweep, degradations, write_dashboard  # noqa: E402

STATE = Path("/home/john/Thunderbird/OpsCenter/state/ci_routine_state.json")
TIMER = Path.home() / ".config" / "systemd" / "user" / "ci-sweep.timer"
STREAK_TARGET = 7


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"streak": 0, "cadence": "daily", "history": []}


def set_timer_cadence(weekly: bool) -> str:
    """Rewrite ci-sweep.timer OnCalendar. Returns a status string; never raises."""
    if not TIMER.exists():
        return "timer file absent — cadence recorded only"
    try:
        txt = TIMER.read_text()
        new_cal = "OnCalendar=Mon *-*-* 06:00:00 America/Denver" if weekly \
                  else "OnCalendar=*-*-* 06:00:00 America/Denver"
        import re
        txt2 = re.sub(r"OnCalendar=.*", new_cal, txt, count=1)
        if txt2 != txt:
            TIMER.write_text(txt2)
            subprocess.run(["systemctl", "--user", "daemon-reload"], timeout=15)
            subprocess.run(["systemctl", "--user", "restart", "ci-sweep.timer"], timeout=15)
            return f"timer set to {'weekly' if weekly else 'daily'}"
        return "timer already at target cadence"
    except Exception as e:
        return f"timer rewrite failed ({e}) — cadence recorded only"


def main() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results = sweep(update_verified=True)
    write_dashboard(results)
    degraded = degradations(results)

    total = len(results)
    green = sum(1 for r in results if r.get("status") == "RAZOR_SHARP")
    perfect = (green == total and total > 0)

    st = load_state()
    # one record per day (idempotent)
    st["history"] = [h for h in st.get("history", []) if h.get("date") != today]
    st["streak"] = (st.get("streak", 0) + 1) if perfect else 0
    st["history"].append({"date": today, "green": green, "total": total,
                          "perfect": perfect, "streak": st["streak"]})
    st["history"] = st["history"][-30:]

    # page on degradation (reuse ci_sweep's pager path)
    if degraded:
        try:
            from OpsCenter.wing_page import page
            client_red = [d for d in degraded
                          if d["id"] in {"portal-access", "credential-keepalive"}
                          and d["status"] in ("RED", "REPLACE")]
            page("commander" if client_red else "whetstone",
                 "CI daily routine — not razor-sharp:\n" +
                 "\n".join(f"- {d['name']}: {d['status']}" for d in degraded))
        except Exception as e:
            print(f"[page failed: {e}]", file=sys.stderr)

    # cadence transition
    if st["streak"] >= STREAK_TARGET and st.get("cadence") != "weekly":
        st["cadence"] = "weekly"
        st["cadence_note"] = f"{set_timer_cadence(weekly=True)} on {today} (streak {st['streak']})"
    elif st["streak"] < STREAK_TARGET and st.get("cadence") != "daily":
        st["cadence"] = "daily"
        st["cadence_note"] = f"{set_timer_cadence(weekly=False)} on {today} (streak reset)"

    st["last_run"] = today
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))

    print(f"CI routine {today}: {green}/{total} RAZOR_SHARP | "
          f"streak {st['streak']}/{STREAK_TARGET} | cadence={st['cadence']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
