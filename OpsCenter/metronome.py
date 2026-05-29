#!/usr/bin/env python3
"""METRONOME — The non-sleeper clock agent for Two-Brain sessions.
Dreams2Memories Travel, LLC

Ticks every 5 minutes via systemd timer. Never sleeps. Tracks cadence,
detects stalled tasks, auto-escalates, writes to metronome_ticks.jsonl.

Usage:
  python metronome.py                    # normal tick
  python metronome.py --status           # print current state, no tick
  python metronome.py --force-tick       # tick even if offline mode
  python metronome.py --reset-sequence   # reset tick counter to 0
  python metronome.py --checkpoints      # print last 5 checkpoints
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKS_FILE = os.path.join(ROOT, "OpsCenter", "metronome_ticks.jsonl")
CHECKPOINT_FILE = os.path.join(ROOT, "OpsCenter", "checkpoints.jsonl")
SHARED_STATE_FILE = os.path.join(ROOT, "OpsCenter", "hale_shared_state.jsonl")
WING_COMMS = os.path.join(ROOT, "OpsCenter", "collaboration", "wing_comms.md")
DISPATCH_SCRIPT = os.path.join(ROOT, "OpsCenter", "dispatch_claude.py")

CADENCE_S = 300  # 5 minutes between ticks
IDLE_YELLOW_S = 300   # 5 min — nudge
IDLE_ORANGE_S = 600   # 10 min — auto-restart
IDLE_RED_S = 900      # 15 min — Telegram alert
IDLE_CRITICAL_S = 1800  # 30 min — auto-close

SEQUENCE_FILE = os.path.join(ROOT, "OpsCenter", ".metronome_seq")
DEEPSEEK_RATE_LOG = os.path.join(ROOT, "OpsCenter", ".deepseek_rate_log")
DOSSIERS_DIR = os.path.join(ROOT, "dossiers")
MISSION_BOARD_FILE = os.path.join(ROOT, "OpsCenter", "mission_board.json")
SPSA_DEDUP_FILE = os.path.join(ROOT, "OpsCenter", "spsa_dedup_state.json")
LIFECYCLE_DEDUP_FILE = os.path.join(ROOT, "OpsCenter", ".lifecycle_alerted.json")
LIFECYCLE_DAILY_SENTINEL = os.path.join(ROOT, "OpsCenter", ".lifecycle_last_scan_date")

# M-076: Regent cookie expiry monitoring
REGENT_COOKIES_MAIN = os.path.join(ROOT, "creds", "regent_cookies.json")
REGENT_COOKIES_OA = os.path.join(ROOT, "creds", "regent_cookies_oa.json")
REGENT_COOKIE_DEDUP_FILE = os.path.join(ROOT, "OpsCenter", ".regent_cookie_alert_dedup.json")
REGENT_COOKIE_ALERT_HOURS = 72  # alert when ASPXAUTH expires within this many hours

# Intel Keeper fires every 3 ticks (3 × 5 min = 15 min), matching keeper TTL cadence
INTEL_KEEPER_SCRIPT = os.path.join(ROOT, "core", "ai_infra", "intel_keeper.py")
INTEL_KEEPER_TICKS = 3  # fire every N ticks


def _get_tick_number():
    try:
        with open(SEQUENCE_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _increment_tick():
    n = _get_tick_number() + 1
    with open(SEQUENCE_FILE, "w") as f:
        f.write(str(n))
    return n


def _reset_tick():
    with open(SEQUENCE_FILE, "w") as f:
        f.write("0")


def _load_dedup(filepath):
    try:
        with open(filepath) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_dedup(filepath, state):
    try:
        with open(filepath, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def _read_last_checkpoint():
    """Return the most recent checkpoint entry, or None."""
    if not os.path.exists(CHECKPOINT_FILE):
        return None
    last = None
    with open(CHECKPOINT_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    last = json.loads(line)
                except json.JSONDecodeError:
                    continue
    return last


def _read_last_heartbeat(instance="hale_oc"):
    """Read the last shared-state entry for a given instance."""
    if not os.path.exists(SHARED_STATE_FILE):
        return None
    last = None
    with open(SHARED_STATE_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("instance") == instance:
                last = entry
    return last


def _age_seconds(ts_str):
    """Calculate how many seconds old a timestamp string is."""
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return int((datetime.now(timezone.utc) - ts).total_seconds())
    except (ValueError, AttributeError):
        return None


def _telegram_alert(message):
    """Send alert to Commander via Telegram."""
    try:
        bot_token = ""
        chat_id = "7554895206"
        poe_env = os.path.join(ROOT, "config", "poe.env")
        if os.path.exists(poe_env):
            for line in open(poe_env):
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    bot_token = line.strip().split("=", 1)[1]
                elif line.startswith("TELEGRAM_COMMANDER_ID="):
                    chat_id = line.strip().split("=", 1)[1]
        if not bot_token:
            return
        import urllib.request
        payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _write_wing_nudge(message):
    os.makedirs(os.path.dirname(WING_COMMS), exist_ok=True)
    with open(WING_COMMS, "a") as f:
        f.write(f"\n---\n## METRONOME NUDGE — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n{message}\n")


def _auto_restart_sonnet(age_s, reason=""):
    """Auto-restart stalled Sonnet dispatch."""
    ts = int(datetime.now(timezone.utc).timestamp())
    outfile = os.path.join(ROOT, "output", f"two_brain_autorestart_{ts}.md")
    try:
        result = subprocess.run(
            [sys.executable, DISPATCH_SCRIPT,
             "--task", f"metronome-autorestart-{ts}",
             "--output", outfile,
             "--prompt", f"METRONOME auto-restart. Previous dispatch stalled at {age_s}s. {reason}. WRITE to {outfile}",
             "--model", "sonnet"],
            capture_output=True, text=True, timeout=30
        )
        _write_wing_nudge(f"METRONOME auto-restarted Sonnet dispatch (stalled {age_s}s). Output: {outfile}")
    except Exception as e:
        _write_wing_nudge(f"METRONOME failed to auto-restart: {e}")


def _record_deepseek_call():
    """Record a DeepSeek V4 Flash API call timestamp. Called by dispatch scripts."""
    os.makedirs(os.path.dirname(DEEPSEEK_RATE_LOG), exist_ok=True)
    with open(DEEPSEEK_RATE_LOG, "a") as f:
        f.write(datetime.now(timezone.utc).isoformat() + "\n")


def _check_deepseek_limits():
    """Check DeepSeek V4 Flash free tier rate limits.
    Limits: 100 req/hour, 500 req/day.
    Returns dict with usage stats and alert state.
    """
    if not os.path.exists(DEEPSEEK_RATE_LOG):
        return {"hourly_used": 0, "daily_used": 0, "hourly_pct": 0, "daily_pct": 0,
                "hourly_limit": 100, "daily_limit": 500, "state": "GREEN", "alarm": None}

    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(hours=24)

    hourly = 0
    daily = 0
    with open(DEEPSEEK_RATE_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ts = datetime.fromisoformat(line)
                if ts > hour_ago:
                    hourly += 1
                if ts > day_ago:
                    daily += 1
            except ValueError:
                continue

    hourly_pct = round(hourly / 100 * 100, 1)
    daily_pct = round(daily / 500 * 100, 1)

    # Check thresholds against TALON compact spec
    alarm = None
    state = "GREEN"
    if hourly >= 95 or daily >= 475:
        state = "CRITICAL"
        alarm = f"DeepSeek V4 CRITICAL: {hourly}/hr ({hourly_pct}%), {daily}/day ({daily_pct}%)"
    elif hourly >= 80 or daily >= 400:
        state = "RED"
        alarm = f"DeepSeek V4 RED: {hourly}/hr ({hourly_pct}%), {daily}/day ({daily_pct}%)"
    elif hourly >= 60 or daily >= 300:
        state = "YELLOW"
        alarm = f"DeepSeek V4 YELLOW: {hourly}/hr ({hourly_pct}%), {daily}/day ({daily_pct}%)"

    return {
        "hourly_used": hourly,
        "daily_used": daily,
        "hourly_pct": hourly_pct,
        "daily_pct": daily_pct,
        "hourly_limit": 100,
        "daily_limit": 500,
        "state": state,
        "alarm": alarm,
    }


def _parse_frontmatter(filepath):
    """Parse YAML-style frontmatter from a markdown file without yaml import.
    Returns dict of key/value pairs, or {} if no frontmatter.
    """
    result = {}
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return result
    if not lines or lines[0].strip() != "---":
        return result
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            result[key.strip()] = val
    return result


def _scan_dossier_fpds():
    """Scan dossiers/*.md for FPD and departure deadline alerts.
    Returns list of alert dicts sorted by urgency (CRITICAL first).
    """
    today = datetime.now(ZoneInfo("America/Denver")).date()
    SKIP_STATUS_WORDS = {"completed", "paid", "cancelled", "archived",
                         "inactive", "void", "complete"}
    alerts = []
    if not os.path.isdir(DOSSIERS_DIR):
        return alerts
    for fname in os.listdir(DOSSIERS_DIR):
        if not fname.endswith(".md"):
            continue
        fm = _parse_frontmatter(os.path.join(DOSSIERS_DIR, fname))
        if not fm:
            continue
        status = fm.get("status", "").lower()
        if any(w in status for w in SKIP_STATUS_WORDS):
            continue
        client = fm.get("client", fname.replace(".md", "")).strip('"')
        ship = fm.get("ship", "")
        # Skip dossiers whose voyage has already departed (>7 days ago)
        dep_str = fm.get("departure", "")
        dep_days = None
        if dep_str:
            try:
                dep_date = datetime.strptime(dep_str, "%Y-%m-%d").date()
                dep_days = (dep_date - today).days
                if dep_days < -7:
                    continue
            except ValueError:
                pass
        # FPD alert — only surface if within actionable window (-14d to +7d)
        fpd_str = fm.get("fpd", "")
        if fpd_str:
            try:
                fpd_date = datetime.strptime(fpd_str, "%Y-%m-%d").date()
                fpd_days = (fpd_date - today).days
                if fpd_days < -14:
                    lvl = None  # Too old — assume handled
                elif fpd_days < 0:
                    lvl = "CRITICAL"  # -14 to -1 days
                elif fpd_days <= 3:
                    lvl = "RED"  # 0 to 3 days
                elif fpd_days <= 7:
                    lvl = "YELLOW"  # 4 to 7 days
                else:
                    lvl = None
                if lvl:
                    amt = fm.get("fpd_amount", "")
                    amt_str = f" ${amt}" if amt else ""
                    alerts.append({"type": "fpd", "level": lvl, "client": client,
                                   "ship": ship, "date": fpd_str, "days": fpd_days,
                                   "msg": f"FPD{amt_str} — {client} ({ship}) — {fpd_str} ({fpd_days:+d}d)"})
            except ValueError:
                pass
        # Departure alert
        if dep_days is not None:
            try:
                if 0 <= dep_days <= 14:
                    lvl = "RED"
                elif 0 < dep_days <= 30:
                    lvl = "YELLOW"
                else:
                    lvl = None
                if lvl:
                    alerts.append({"type": "departure", "level": lvl, "client": client,
                                   "ship": ship, "date": dep_str, "days": dep_days,
                                   "msg": f"DEPARTS — {client} ({ship}) — {dep_str} (T-{dep_days}d)"})
            except ValueError:
                pass
    level_order = {"CRITICAL": 0, "RED": 1, "YELLOW": 2}
    alerts.sort(key=lambda a: (level_order.get(a["level"], 9), a["days"]))
    return alerts


def _rank_missions_today():
    """Return top active missions ranked by priority, max 7."""
    if not os.path.exists(MISSION_BOARD_FILE):
        return []
    try:
        with open(MISSION_BOARD_FILE) as f:
            board = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    SKIP = {"completed", "archived", "audit_complete"}
    PORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    active = [m for m in board.get("missions", [])
              if m.get("status", "").lower() not in SKIP]

    def _key(m):
        pri = PORDER.get(m.get("priority", "P3"), 3)
        susp = (m.get("suspense_date") or "9999-99-99")[:10]
        return (pri, "0000" + susp if susp < today_str else susp)

    active.sort(key=_key)
    return active[:7]


def _scan_lifecycle_windows():
    """Scan dossiers for lifecycle touchpoint windows — runs once per calendar day.
    Derives arc_id/position from days-to-departure via date-window table.
    Outputs [HALE-ROUTE] entries to wing_comms.md.
    NEVER calls _telegram_alert() — lifecycle routing is Hale's domain.
    Per A7 Sterling design gate (output/sterling_metronome_lifecycle_design.md).
    """
    today_mt = datetime.now(ZoneInfo("America/Denver"))
    today_str = today_mt.strftime("%Y-%m-%d")

    # Daily sentinel gate — skip if already ran today
    try:
        if os.path.exists(LIFECYCLE_DAILY_SENTINEL):
            with open(LIFECYCLE_DAILY_SENTINEL) as f:
                if f.read().strip() == today_str:
                    return
    except OSError:
        pass
    try:
        with open(LIFECYCLE_DAILY_SENTINEL, "w") as f:
            f.write(today_str)
    except OSError:
        pass

    today = today_mt.date()

    # Date-window table: (dep_days_lo, dep_days_hi, arc_id, position, action_label)
    # dep_days = departure_date - today (positive=future, negative=past)
    # Client is IN window when dep_days_lo <= dep_days <= dep_days_hi
    # Dedup key uses departure_date, so each (client, arc, position) fires ONCE per voyage.
    # Synchronized with lifecycle_decision_trees.yaml v1.1
    WINDOWS = [
        (270, 330, "arc4", "a", "Air Search open — task A2 Dembe route intel + A9 fare check + A8 airline fit"),
        (200, 220, "arc5", "a", "Dining Preferences — task A2 research dining options + A8 recommend"),
        (169, 200, "arc5", "b", "Dining Candidates — task A2 shortlist candidates (T-200d)"),
        (120, 169, "arc1", "a", "Research & Pricing — task A2 Dembe dest research + A9 Harlan pricing (T-169d)"),
        ( 14,  77, "arc1", "c", "Check-In window — task A3 Dani check-in, confirm next steps"),
        (  0,  14, "arc4", "c", "Final Prep — task A2 pre-departure brief + A3 Dani final touch"),
        (-14,  -7, "arc3", "a", "Insurance window (D+7–D+14) — task A3 Dani insurance pitch"),
        (-30, -15, "arc2", "a", "Post-voyage welcome (D+14+) — task A3 Dani validation + welcome"),
    ]

    if not os.path.isdir(DOSSIERS_DIR):
        return

    # Load dedup state — purge entries for departed voyages (dep_date < today)
    raw_dedup = _load_dedup(LIFECYCLE_DEDUP_FILE)
    dedup = {}
    for key, dep_date_str in raw_dedup.items():
        try:
            dep_d = datetime.strptime(dep_date_str, "%Y-%m-%d").date()
            if dep_d >= today:
                dedup[key] = dep_date_str
        except ValueError:
            pass

    SKIP_STATUS_WORDS = {"completed", "paid", "cancelled", "archived", "inactive", "void", "complete"}
    pending = []  # (client, ship, dep_str, dep_days, arc_id, position, action_label, dedup_key)

    for fname in sorted(os.listdir(DOSSIERS_DIR)):
        if not fname.endswith(".md"):
            continue
        fm = _parse_frontmatter(os.path.join(DOSSIERS_DIR, fname))
        if not fm:
            continue
        status = fm.get("status", "").lower()
        if any(w in status for w in SKIP_STATUS_WORDS):
            continue
        dep_str = fm.get("departure", "")
        if not dep_str:
            continue
        try:
            dep_date = datetime.strptime(dep_str, "%Y-%m-%d").date()
            dep_days = (dep_date - today).days
        except ValueError:
            continue
        # Skip voyages more than 400d out or more than 60d past
        if dep_days > 400 or dep_days < -60:
            continue

        client = fm.get("client", fname.replace(".md", "")).strip('"')
        ship = fm.get("ship", "Unknown")

        for lo, hi, arc_id, position, action_label in WINDOWS:
            if lo <= dep_days <= hi:
                dedup_key = f"{client}|{arc_id}|{position}|{dep_str}"
                if dedup_key not in dedup:
                    pending.append((client, ship, dep_str, dep_days, arc_id, position, action_label, dedup_key))

    if not pending:
        return

    # Write dedup state BEFORE calling _write_wing_nudge (Sterling rule — non-negotiable)
    new_dedup = dict(dedup)
    for _, _, dep_str, _, arc_id, position, _, dedup_key in pending:
        new_dedup[dedup_key] = dep_str
    _save_dedup(LIFECYCLE_DEDUP_FILE, new_dedup)

    # Attempt to load lifecycle_router for structured persona chains (M-072)
    _router = None
    try:
        sys.path.insert(0, ROOT)
        from core.ops.lifecycle_router import get_arc_route as _get_arc_route
        _router = _get_arc_route
    except Exception:
        pass

    # Fire [HALE-ROUTE] nudges to wing_comms.md
    ts_str = today_mt.strftime("%Y-%m-%d %H:%M MT")
    lines = [f"[HALE-ROUTE] LIFECYCLE WINDOWS — {ts_str}"]
    for client, ship, dep_str, dep_days, arc_id, position, action_label, _ in pending:
        # Enrich with structured route chain from lifecycle_router if available
        route_suffix = ""
        if _router:
            try:
                route_data = _router(arc_id, position)
                if "error" not in route_data:
                    chain = " → ".join(s["persona"] for s in route_data.get("route", []))
                    client_tag = " [client-facing]" if route_data.get("client_facing") else ""
                    cos_tag = " [cos-review]" if route_data.get("cos_review") else ""
                    route_suffix = f" | Route: {chain}{client_tag}{cos_tag}"
            except Exception:
                pass
        lines.append(
            f"• **{client}** ({ship}) T{dep_days:+d}d → `{arc_id}/{position}` — {action_label}{route_suffix}"
        )
    _write_wing_nudge("\n".join(lines))


def _check_regent_cookie_expiry():
    """M-076: Check Regent ASPXAUTH cookie expiry on every tick.

    Reads regent_cookies.json (main) and regent_cookies_oa.json (OA account).
    Fires a Telegram alert (once per file per calendar day via dedup) when:
      - ASPXAUTH expires within REGENT_COOKIE_ALERT_HOURS (72h), OR
      - ASPXAUTH expires == -1 (session cookie — always flag as needs re-export)
    Includes re-export instructions in the alert text.
    """
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    threshold = REGENT_COOKIE_ALERT_HOURS * 3600

    dedup = _load_dedup(REGENT_COOKIE_DEDUP_FILE)

    files = [
        (REGENT_COOKIES_MAIN, "MAIN", "rssc.com (primary intel account)"),
        (REGENT_COOKIES_OA, "OA", "rssc.com (OA portal account)"),
    ]

    fired = False
    for cookie_path, label, desc in files:
        if not os.path.exists(cookie_path):
            continue
        dedup_key = f"regent_cookie_{label}:{today_str}"
        if dedup.get(dedup_key) == today_str:
            continue  # already alerted today
        try:
            with open(cookie_path) as f:
                cookies = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        aspx = next(
            (c for c in cookies if c.get("name", "").upper() in (".ASPXAUTH", "ASPXAUTH")),
            None,
        )
        if not aspx:
            continue

        expires_raw = aspx.get("expires", 0)
        alert_msg = None

        if expires_raw == -1:
            # Session cookie — can expire any time; flag for re-export
            alert_msg = (
                f"*METRONOME* \U0001f7e1 REGENT COOKIE — {label} SESSION COOKIE\n"
                f"Account: {desc}\n"
                f"`.ASPXAUTH` is a session cookie (expires on browser close).\n"
                f"Re-export now if intel connector is failing:\n"
                f"`python3 core/intel/thunderbird_ship_intel.py --export-cookies {label.lower()}`"
            )
        elif expires_raw > 0:
            exp_dt = datetime.fromtimestamp(expires_raw, tz=timezone.utc)
            secs_left = (exp_dt - now).total_seconds()
            if secs_left <= threshold:
                hours_left = max(0, int(secs_left / 3600))
                exp_str = exp_dt.strftime("%Y-%m-%d %H:%M UTC")
                icon = "\U0001f534" if hours_left < 24 else "\U0001f7e0"
                alert_msg = (
                    f"*METRONOME* {icon} REGENT COOKIE EXPIRING — {label}\n"
                    f"Account: {desc}\n"
                    f"`.ASPXAUTH` expires: {exp_str} (~{hours_left}h)\n"
                    f"Re-export before expiry:\n"
                    f"1. Open Firefox, log in to rssc.com ({label} account)\n"
                    f"2. Export cookies via Cookie-Editor extension\n"
                    f"3. Save to `creds/regent_cookies{'' if label == 'MAIN' else '_oa'}.json`\n"
                    f"4. Run: `python3 core/intel/thunderbird_ship_intel.py --verify-cookies {label.lower()}`"
                )

        if alert_msg:
            _telegram_alert(alert_msg)
            dedup[dedup_key] = today_str
            fired = True

    if fired:
        _save_dedup(REGENT_COOKIE_DEDUP_FILE, dedup)


def _generate_daily_brief():
    """Compose daily brief message for Telegram from FPD alerts + mission ranking."""
    now_mt = datetime.now(ZoneInfo("America/Denver"))
    date_str = now_mt.strftime("%Y-%m-%d %H:%M MT")
    alerts = _scan_dossier_fpds()
    missions = _rank_missions_today()
    today_str = now_mt.strftime("%Y-%m-%d")
    lines = [f"*\U0001f985 THUNDERBIRD DAILY BRIEF — {date_str}*", ""]
    if alerts:
        lines.append("*\U0001f4c5 DEADLINE ALERTS*")
        for a in alerts:
            icon = {"CRITICAL": "\U0001f534", "RED": "\U0001f7e0", "YELLOW": "\U0001f7e1"}.get(a["level"], "⚪")
            lines.append(f"{icon} {a['msg']}")
        lines.append("")
    else:
        lines.append("*\U0001f4c5 DEADLINES* — None within 30-day window")
        lines.append("")
    if missions:
        lines.append("*\U0001f4cb MISSION BOARD (Top Active)*")
        for m in missions:
            pid = m.get("priority", "?")
            mid = m.get("id", "?")
            title = m.get("title", "?")[:48]
            status = m.get("status", "?")
            susp = (m.get("suspense_date") or "")[:10]
            overdue = " ⚠OVERDUE" if susp and susp < today_str else ""
            susp_str = f" [{susp}]" if susp else ""
            lines.append(f"• `{pid}` {mid}: {title}{susp_str} ({status}){overdue}")
    else:
        lines.append("*\U0001f4cb MISSION BOARD* — No active missions")
    msg = "\n".join(lines)
    return msg[:4000] + "..." if len(msg) > 4000 else msg


def _run_intel_keeper_if_due(tick_n: int) -> str | None:
    """Spawn intel_keeper as a non-blocking subprocess every INTEL_KEEPER_TICKS ticks.

    Returns a status string for the tick log, or None if skipped.
    Playwright-heavy connectors (Regent/Viking) can take 1-3 min — must not block the tick.
    """
    if tick_n % INTEL_KEEPER_TICKS != 0:
        return None
    if not os.path.exists(INTEL_KEEPER_SCRIPT):
        return "keeper_missing"
    try:
        log_path = os.path.join(ROOT, "logs", "intel_keeper_metronome.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as lf:
            proc = subprocess.Popen(
                [sys.executable, INTEL_KEEPER_SCRIPT],
                stdout=lf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                cwd=ROOT,
            )
        return f"keeper_spawned(pid={proc.pid})"
    except Exception as e:
        return f"keeper_error({e})"


def _auto_close_stale(age_s, reason=""):
    """Close stale task and mark for Commander review."""
    _telegram_alert(
        f"*METRONOME ALERT* — Session stale {age_s}s\n"
        f"Auto-closed stale task.\n"
        f"Reason: {reason}\n"
        f"Next: Commander review needed."
    )


# Heartbeat expected only during active Two-Brain sessions.
# If the latest checkpoint is older than the session window, heartbeats
# are expected to go stale — treat as IDLE/OFFLINE, not RED.
SESSION_WINDOW_S = 3600  # 1 hour — if no activity in this long, session is over


def _is_active_session(checkpoint_age):
    """Return True if there's evidence of an active session (recent checkpoint)."""
    if checkpoint_age is None:
        return False
    return checkpoint_age <= SESSION_WINDOW_S


def evaluate_state(checkpoint_age, heartbeat_age, dispatch_age=None):
    """Return (state, action_taken, description) based on age thresholds."""
    action = None

    if checkpoint_age is None and heartbeat_age is None:
        return ("OFFLINE", "first_tick", "No checkpoints or heartbeats found — first METRONOME tick")

    # If no active session (checkpoint > 1hr old), don't escalate heartbeat misses to RED
    if not _is_active_session(checkpoint_age):
        state = "OFFLINE"
        desc = f"Session idle — last checkpoint {checkpoint_age}s ago"
        if heartbeat_age is not None:
            desc += f", last heartbeat {heartbeat_age}s ago (expected — no active session)"
        return (state, None, desc)

    max_age = max(
        a for a in [checkpoint_age, heartbeat_age, dispatch_age]
        if a is not None
    )

    if max_age is None:
        return ("OFFLINE", None, "No age data available")

    if max_age <= IDLE_YELLOW_S:
        return ("GREEN", None, f"Healthy — last activity {max_age}s ago")

    if max_age <= IDLE_ORANGE_S:
        _write_wing_nudge(f"METRONOME YELLOW: Session idle {max_age}s. Activity expected within {CADENCE_S}s cadence.")
        return ("YELLOW", "nudge", f"Nudge written — idle {max_age}s")

    if max_age <= IDLE_RED_S:
        _auto_restart_sonnet(max_age, reason="Session idle threshold crossed")
        return ("ORANGE", "auto_restart", f"Auto-restart dispatched — idle {max_age}s")

    if max_age <= IDLE_CRITICAL_S:
        _telegram_alert(
            f"*METRONOME RED* — Session idle {max_age}s\n"
            f"Auto-restart triggered. Check wing_comms.md for nudge trail."
        )
        return ("RED", "telegram_alert", f"Commander alerted — idle {max_age}s")

    _auto_close_stale(max_age, reason="Session idle > 30 min")
    return ("CRITICAL", "auto_close", f"Task auto-closed — idle {max_age}s")


def main():
    args = sys.argv[1:]

    if "--daily-brief" in args:
        brief = _generate_daily_brief()
        print(brief)
        _telegram_alert(brief)
        return

    if "--reset-sequence" in args:
        _reset_tick()
        print("METRONOME sequence reset to 0")
        return

    if "--checkpoints" in args:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE) as f:
                lines = f.readlines()
            for line in lines[-5:]:
                try:
                    e = json.loads(line.strip())
                    print(f"  {e.get('ts','?'):25s} {e.get('task','?')[:60]}")
                except Exception:
                    print(f"  (parse error) {line.strip()[:80]}")
        else:
            print("No checkpoints found")
        return

    if "--record-deepseek-call" in args:
        _record_deepseek_call()
        print("DeepSeek V4 call recorded")
        return

    tick_n = _get_tick_number()

    if "--status" in args:
        last_ck = _read_last_checkpoint()
        last_hb = _read_last_heartbeat("hale_oc")
        ds = _check_deepseek_limits()
        print(f"METRONOME tick #{tick_n}")
        print(f"  Last checkpoint: {json.dumps(last_ck) if last_ck else 'NONE'}")
        print(f"  Last heartbeat:  {json.dumps(last_hb) if last_hb else 'NONE'}")
        print(f"  DeepSeek V4: {ds['hourly_used']}/hr ({ds['hourly_pct']}%) | {ds['daily_used']}/day ({ds['daily_pct']}%) [{ds['state']}]")
        return

    force = "--force-tick" in args

    # Read state
    last_ck = _read_last_checkpoint()
    last_hb = _read_last_heartbeat("hale_oc")

    ck_age = _age_seconds(last_ck.get("ts")) if last_ck and last_ck.get("ts") else None
    hb_age = _age_seconds(last_hb.get("ts")) if last_hb and last_hb.get("ts") else None

    # If no age data and not forced, skip tick for first run
    if ck_age is None and hb_age is None and not force:
        tick_n = _increment_tick()
        ds = _check_deepseek_limits()
        lc = _scan_dossier_fpds()
        lc_sum = {"critical": len([a for a in lc if a["level"] == "CRITICAL"]),
                  "red": len([a for a in lc if a["level"] == "RED"]),
                  "yellow": len([a for a in lc if a["level"] == "YELLOW"])}
        keeper_status = _run_intel_keeper_if_due(tick_n)
        _check_regent_cookie_expiry()  # M-076 — run even on first tick
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tick": tick_n,
            "cadence_s": CADENCE_S,
            "state": "OFFLINE",
            "last_checkpoint_age_s": None,
            "last_heartbeat_age_s": None,
            "deepseek": {
                "hourly": ds["hourly_used"],
                "daily": ds["daily_used"],
                "hourly_pct": ds["hourly_pct"],
                "daily_pct": ds["daily_pct"],
                "state": ds["state"],
            },
            "lifecycle": lc_sum,
            "action": "first_tick",
            "intel_keeper": keeper_status,
        }
        os.makedirs(os.path.dirname(TICKS_FILE), exist_ok=True)
        with open(TICKS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"METRONOME tick #{tick_n}: OFFLINE (first tick — no data yet)")
        return

    state, action, desc = evaluate_state(ck_age, hb_age)

    # DeepSeek V4 Flash rate limit check
    ds = _check_deepseek_limits()
    if ds["alarm"]:
        desc += f" | {ds['alarm']}"
        if ds["state"] in ("RED", "CRITICAL"):
            _telegram_alert(f"*METRONOME* — {ds['alarm']}")
            _write_wing_nudge(f"METRONOME ALERT: {ds['alarm']}")

    # Lifecycle FPD scan — auto-alert on CRITICAL deadlines
    lc = _scan_dossier_fpds()
    lc_sum = {"critical": len([a for a in lc if a["level"] == "CRITICAL"]),
              "red": len([a for a in lc if a["level"] == "RED"]),
              "yellow": len([a for a in lc if a["level"] == "YELLOW"])}
    today_mt_str = datetime.now(ZoneInfo("America/Denver")).strftime("%Y-%m-%d")
    fpd_dedup = _load_dedup(SPSA_DEDUP_FILE)
    for alert in lc:
        if alert["level"] == "CRITICAL":
            fpd_key = f"fpd:{alert['client']}:{alert['date']}"
            if fpd_dedup.get(fpd_key) != today_mt_str:
                _telegram_alert(f"*METRONOME* \U0001f534 FPD OVERDUE: {alert['msg']}")
                fpd_dedup[fpd_key] = today_mt_str
            break
    _save_dedup(SPSA_DEDUP_FILE, {k: v for k, v in fpd_dedup.items() if v == today_mt_str})
    _scan_lifecycle_windows()
    _check_regent_cookie_expiry()  # M-076 — every tick, deduped daily per account

    tick_n = _increment_tick()
    keeper_status = _run_intel_keeper_if_due(tick_n)

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tick": tick_n,
        "cadence_s": CADENCE_S,
        "state": state,
        "last_checkpoint_age_s": ck_age,
        "last_heartbeat_age_s": hb_age,
        "deepseek": {
            "hourly": ds["hourly_used"],
            "daily": ds["daily_used"],
            "hourly_pct": ds["hourly_pct"],
            "daily_pct": ds["daily_pct"],
            "state": ds["state"],
        },
        "lifecycle": lc_sum,
        "action": action,
        "description": desc,
        "intel_keeper": keeper_status,
    }

    os.makedirs(os.path.dirname(TICKS_FILE), exist_ok=True)
    with open(TICKS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    brief_state = {"GREEN": "✓", "YELLOW": "~", "ORANGE": "!", "RED": "!!", "CRITICAL": "✗"}.get(state, "?")
    print(f"METRONOME tick #{tick_n}: {brief_state} {state} — {desc}")

    if state in ("RED", "CRITICAL"):
        sys.exit(1)


if __name__ == "__main__":
    main()
