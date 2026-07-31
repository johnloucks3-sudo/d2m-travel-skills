"""
thunderbird_rate_limit_guard.py
Rate-Limit Auto-Response System — Phase 2 Project #9
Dreams2Memories Travel, LLC | Thunderbird Wing

STATE MACHINE:
  NORMAL  → < 70% weekly consumption
  WARN    → 70–84%   — heads-up alert, no routing change
  CRIT    → 85–89%   — graceful degradation ENGAGES:
                         non-urgent → OpenRouter / DeepSeek
                         urgent     → Max (Claude Code)
  STOP    → ≥ 90%    — hard guard: ALL tasks → DeepSeek
  ROLLBACK→ drops < 10% (weekly reset) — auto-restore NORMAL routing

Telegram alert sent on every state TRANSITION (not on every poll).
State persisted to disk so daemon restarts survive.
"""

import json
import logging
import os
import sqlite3
import subprocess
import urllib.request
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("rate_limit_guard")

# ── Paths ──────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR  = Path("/home/john/Thunderbird")
CONFIG_DIR       = THUNDERBIRD_DIR / "config"
STATE_FILE       = CONFIG_DIR / "rate_guard_state.json"
LOG_DIR          = THUNDERBIRD_DIR / "logs"
LOG_FILE         = LOG_DIR / "rate_limit_guard.log"
COST_DB          = THUNDERBIRD_DIR / "storage" / "ai_costs.db"
HUD_CACHE_PATH   = Path.home() / ".claude" / "hud" / ".usage-cache.json"

POE_ENV_FILE     = CONFIG_DIR / "poe.env"
MAIN_ENV_FILE    = THUNDERBIRD_DIR / ".env"

# ── Thresholds ─────────────────────────────────────────────────────────────────
WEEKLY_LIMIT_ALL = 680_000_000   # tokens — all-models rolling 7-day
SONNET_WARN      = 70    # % — Sonnet weekly heads-up
SONNET_CRIT      = 85    # % — Sonnet graceful degradation
SONNET_STOP      = 95    # % — Sonnet hard block

FIVE_HOUR_WARN   = 70    # % — 5h window heads-up
FIVE_HOUR_CRIT   = 85    # % — 5h window graceful degradation engages
FIVE_HOUR_STOP   = 90    # % — 5h window hard guard

THRESH_WARN      = 70    # % — all-models heads-up
THRESH_CRIT      = 85    # % — all-models graceful degradation engages
THRESH_STOP      = 90    # % — all-models hard guard
THRESH_ROLLBACK  = 10    # % — auto-rollback to NORMAL (post weekly-reset)


class GuardState(str, Enum):
    NORMAL   = "NORMAL"
    WARN     = "WARN"
    CRIT     = "CRIT"
    STOP     = "STOP"
    ROLLBACK = "ROLLBACK"


# Urgency classification — mirrors keyword_router.py tier 3 keywords
URGENT_KEYWORDS = frozenset({
    "client", "urgent", "emergency", "booking", "payment", "deadline",
    "approve", "send", "confirm", "validate", "critical", "immediate",
    "today", "tonight", "asap", "now", "due", "overdue",
})


# ── Config helpers ─────────────────────────────────────────────────────────────

def _read_env_key(key: str) -> str:
    """Read a key from poe.env or .env fallback."""
    for env_path in [POE_ENV_FILE, MAIN_ENV_FILE]:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{key}="):
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(key, "")


def _get_telegram_creds() -> tuple[str, str]:
    token   = _read_env_key("TELEGRAM_BOT_TOKEN")
    chat_id = _read_env_key("TELEGRAM_COMMANDER_ID")
    return token, chat_id


# ── Token usage ────────────────────────────────────────────────────────────────

def get_sonnet_weekly_pct(max_age_hours: float = 24.0) -> Optional[float]:
    """Read Sonnet weekly % from claude_usage_reports table.
    Returns None if unavailable or if newest reading is older than max_age_hours (default 24h).
    """
    if not COST_DB.exists():
        return None
    try:
        conn = sqlite3.connect(str(COST_DB), timeout=3)
        row = conn.execute(
            "SELECT ts, sonnet_weekly_pct FROM claude_usage_reports ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row and row[0] is not None and row[1] is not None:
            ts_str = str(row[0])
            if "Z" in ts_str:
                ts_str = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_hours = (now - dt).total_seconds() / 3600.0
            if age_hours > max_age_hours:
                logger.warning(
                    "get_sonnet_weekly_pct: newest row is %.1f hours old (> %.1fh threshold) — treating as stale/None",
                    age_hours, max_age_hours
                )
                return None
            return float(row[1])
    except Exception as e:
        logger.error("get_sonnet_weekly_pct: %s", e)
    return None


def get_five_hour_pct() -> Optional[float]:
    """Read the live 5-hour OAuth usage % from the existing HUD cache
    (~/.claude/hud/.usage-cache.json), refreshed every 60s by an unrelated tool.
    Returns None if the file is missing, unreadable, malformed, reports an error,
    or is missing the fiveHour figure — never guess.
    """
    if not HUD_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(HUD_CACHE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        if data.get("error"):
            return None
        inner = data.get("data")
        if not isinstance(inner, dict):
            return None
        if "fiveHour" not in inner or inner["fiveHour"] is None:
            return None
        return float(inner["fiveHour"])
    except Exception as e:
        logger.error("get_five_hour_pct: %s", e)
        return None


def get_weekly_pct() -> tuple[Optional[float], int]:
    """Return (weekly_consumption_pct, total_tokens_used).
    Returns (None, 0) on failure — None means UNKNOWN, never treat it as zero.
    """
    try:
        result = subprocess.run(
            ["ccusage", "weekly", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None, 0

        data  = json.loads(result.stdout)
        weeks = data.get("weekly", [])
        if not weeks:
            return None, 0

        current = weeks[-1]
        total   = current.get("totalTokens", 0)
        pct     = round(total / WEEKLY_LIMIT_ALL * 100, 2)
        return pct, total

    except Exception as e:
        logger.error("get_weekly_pct: %s", e)
        return None, 0


def tokens_remaining(used_pct: Optional[float]) -> int:
    """Tokens remaining in weekly budget."""
    if used_pct is None:
        return 0
    return max(0, int(WEEKLY_LIMIT_ALL * (100.0 - used_pct) / 100.0))


# ── State persistence ──────────────────────────────────────────────────────────

def _default_state() -> dict:
    return {
        "state":           GuardState.NORMAL.value,
        "last_pct":        0.0,
        "last_total":      0,
        "last_updated":    "",
        "state_entered_at": "",
        "transitions":     [],
        "degradation_active": False,
        "degradation_mode":   "none",  # none | partial | full
    }


def load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return _default_state()


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Routing logic ──────────────────────────────────────────────────────────────

def classify_urgency(task_description: str) -> str:
    """Return 'urgent' or 'non_urgent' based on task text."""
    lower = task_description.lower()
    for kw in URGENT_KEYWORDS:
        if kw in lower:
            return "urgent"
    return "non_urgent"


def get_routing_override(
    task_description: str,
    current_state: GuardState,
) -> dict:
    """
    Given current guard state, return routing decision for a task.

    Returns:
        {
            "engine":    "max" | "opencode_free" | "normal",
            "model":     str,
            "reason":    str,
            "degraded":  bool,
        }
    """
    if current_state == GuardState.NORMAL or current_state == GuardState.ROLLBACK:
        return {
            "engine":   "normal",
            "model":    "claude-sonnet-4-6",
            "reason":   "Normal routing — within budget",
            "degraded": False,
        }

    if current_state == GuardState.WARN:
        return {
            "engine":   "normal",
            "model":    "claude-sonnet-4-6",
            "reason":   "WARN level — routing unchanged, monitoring",
            "degraded": False,
        }

    if current_state == GuardState.CRIT:
        urgency = classify_urgency(task_description)
        if urgency == "urgent":
            return {
                "engine":   "max",
                "model":    "claude-sonnet-4-6",
                "reason":   "CRIT 85%+ — urgent task → Max preserved",
                "degraded": True,
            }
        else:
            return {
                "engine":   "opencode_free",
                "model":    "opencode/deepseek-v4-flash-free",
                "reason":   "CRIT 85%+ — non-urgent → OpenCode free tier (DeepSeek V4 Flash)",
                "degraded": True,
            }

    if current_state == GuardState.STOP:
        return {
            "engine":   "opencode_free",
            "model":    "opencode/big-pickle",
            "reason":   "STOP 90%+ — all tasks → OpenCode free tier (Big Pickle)",
            "degraded": True,
        }

    return {
        "engine":   "normal",
        "model":    "claude-sonnet-4-6",
        "reason":   "Unknown state — default normal",
        "degraded": False,
    }


def route_task(task_description: str) -> dict:
    """
    Public API: given a task, return routing recommendation.
    Loads current state from disk and decides.
    """
    state_data = load_state()
    guard_state = GuardState(state_data.get("state", GuardState.NORMAL.value))
    return get_routing_override(task_description, guard_state)


# ── Telegram alerts ────────────────────────────────────────────────────────────

def _send_telegram(message: str) -> bool:
    token, chat_id = _get_telegram_creds()
    if not token or not chat_id:
        logger.warning("Telegram creds missing — alert not sent: %s", message[:80])
        return False
    try:
        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id":    chat_id,
            "text":       message,
            "parse_mode": "HTML",
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False


def _alert_message(
    new_state: GuardState,
    used_pct: Optional[float],
    total_tokens: int,
    prev_state: GuardState,
    sonnet_pct: Optional[float] = None,
    five_hour_pct: Optional[float] = None,
) -> str:
    remaining = tokens_remaining(used_pct)
    rem_m = remaining // 1_000_000
    rem_k = (remaining % 1_000_000) // 1_000

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    state_icons = {
        GuardState.NORMAL:   "✅",
        GuardState.WARN:     "⚠️",
        GuardState.CRIT:     "🔴",
        GuardState.STOP:     "🚨",
        GuardState.ROLLBACK: "🔄",
    }

    icon = state_icons.get(new_state, "ℹ️")

    if used_pct is None:
        weekly_line = "All models weekly: [UNKNOWN — telemetry unavailable]"
    else:
        bar_filled = min(max(0, int(used_pct / 5)), 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        weekly_line = f"All models weekly: [{bar}] {used_pct:.1f}%"

    if five_hour_pct is None:
        five_hour_line = "5-hour window:    [UNKNOWN — telemetry unavailable]"
    else:
        fh_filled = min(max(0, int(five_hour_pct / 5)), 20)
        fh_bar = "█" * fh_filled + "░" * (20 - fh_filled)
        five_hour_line = f"5-hour window:    [{fh_bar}] {five_hour_pct:.1f}%"

    if sonnet_pct is None:
        sonnet_line = "Sonnet weekly:      [UNKNOWN — telemetry unavailable]"
    else:
        sonnet_filled = min(max(0, int(sonnet_pct / 5)), 20)
        sonnet_bar = "█" * sonnet_filled + "░" * (20 - sonnet_filled)
        sonnet_line = f"Sonnet weekly:      [{sonnet_bar}] {sonnet_pct:.1f}%"

    lines = [
        f"{icon} <b>Rate-Limit Guard — {new_state.value}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Transition: {prev_state.value} → <b>{new_state.value}</b>",
        weekly_line,
        five_hour_line,
        sonnet_line,
        f"Tokens used: {total_tokens:,}",
        f"Remaining:  <b>{rem_m}M {rem_k:03d}K tokens</b>",
        f"",
    ]

    if new_state == GuardState.WARN:
        lines += [
            "⚠️ Heads-up — 70% weekly budget consumed.",
            "Routing unchanged. Monitor closely.",
        ]
    elif new_state == GuardState.CRIT:
        lines += [
            "🔴 <b>GRACEFUL DEGRADATION ENGAGED</b>",
            "• Non-urgent tasks → OpenCode free tier (DeepSeek V4 Flash)",
            "• Urgent/client tasks → Max preserved",
            "CLI monitor switched to blinking red.",
        ]
    elif new_state == GuardState.STOP:
        lines += [
            "🚨 <b>HARD GUARD ACTIVE — 90%+ consumed</b>",
            "• ALL tasks → OpenCode free tier (Big Pickle)",
            "• Max suspended except Commander override",
            "Take a break or wait for weekly reset.",
        ]
    elif new_state == GuardState.ROLLBACK:
        lines += [
            "🔄 <b>AUTO-ROLLBACK — budget reset detected</b>",
            "Weekly consumption dropped below 10%.",
            "Normal routing restored. Degradation lifted.",
        ]
    elif new_state == GuardState.NORMAL:
        lines += ["✅ Usage within normal range. Full routing active."]

    lines.append(f"\n<i>{ts} | Rate-Limit Guard v1.0</i>")
    return "\n".join(lines)


# ── State transition engine ────────────────────────────────────────────────────

STATE_SEVERITY = {
    GuardState.ROLLBACK: 0,
    GuardState.NORMAL:   1,
    GuardState.WARN:     2,
    GuardState.CRIT:     3,
    GuardState.STOP:     4,
}


def _compute_target_state(
    pct: Optional[float],
    sonnet_pct: Optional[float] = None,
    five_hour_pct: Optional[float] = None,
) -> GuardState:
    # 1. Weekly axis
    if pct is None:
        weekly_state = GuardState.CRIT
    elif pct < THRESH_ROLLBACK:
        weekly_state = GuardState.ROLLBACK
    elif pct < THRESH_WARN:
        weekly_state = GuardState.NORMAL
    elif pct < THRESH_CRIT:
        weekly_state = GuardState.WARN
    elif pct < THRESH_STOP:
        weekly_state = GuardState.CRIT
    else:
        weekly_state = GuardState.STOP

    # 2. Sonnet axis
    if sonnet_pct is None:
        sonnet_state = GuardState.ROLLBACK
    elif sonnet_pct >= SONNET_STOP:
        sonnet_state = GuardState.STOP
    elif sonnet_pct >= SONNET_CRIT:
        sonnet_state = GuardState.CRIT
    elif sonnet_pct >= SONNET_WARN:
        sonnet_state = GuardState.WARN
    else:
        sonnet_state = GuardState.ROLLBACK

    # 3. Five-hour axis
    if five_hour_pct is None:
        five_hour_state = GuardState.WARN
    elif five_hour_pct >= FIVE_HOUR_STOP:
        five_hour_state = GuardState.STOP
    elif five_hour_pct >= FIVE_HOUR_CRIT:
        five_hour_state = GuardState.CRIT
    elif five_hour_pct >= FIVE_HOUR_WARN:
        five_hour_state = GuardState.WARN
    else:
        five_hour_state = GuardState.ROLLBACK

    return max(
        [weekly_state, sonnet_state, five_hour_state],
        key=lambda s: STATE_SEVERITY[s],
    )


def _degradation_mode(state: GuardState) -> str:
    if state == GuardState.CRIT:
        return "partial"   # non-urgent → DeepSeek, urgent → Max
    if state == GuardState.STOP:
        return "full"      # all → DeepSeek
    return "none"


def evaluate(send_alerts: bool = True) -> dict:
    """
    Core evaluation cycle.  Called by daemon, CLI, or on-demand.

    Returns dict with current state, transition info, routing recommendation.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    pct, total = get_weekly_pct()
    five_hour_pct = get_five_hour_pct()
    sonnet_pct = get_sonnet_weekly_pct()
    target     = _compute_target_state(pct, sonnet_pct, five_hour_pct)
    state_data = load_state()
    prev_state = GuardState(state_data.get("state", GuardState.NORMAL.value))

    transitioned = (target != prev_state)
    now_iso = datetime.now(timezone.utc).isoformat()

    if transitioned:
        transition_record = {
            "from":  prev_state.value,
            "to":    target.value,
            "pct":   pct,
            "at":    now_iso,
        }
        transitions = state_data.get("transitions", [])[-49:]  # keep last 50
        transitions.append(transition_record)

        state_data.update({
            "state":              target.value,
            "state_entered_at":   now_iso,
            "transitions":        transitions,
            "degradation_active": target in (GuardState.CRIT, GuardState.STOP),
            "degradation_mode":   _degradation_mode(target),
        })

        logger.info("State transition: %s → %s (pct=%s, 5h=%s)", prev_state.value, target.value, pct, five_hour_pct)

        if send_alerts:
            # CRIT/STOP → D2MC2C (Commander action needed — model routing degraded)
            # WARN/NORMAL → silent (logged in state file, surfaced in AM brief)
            if target in (GuardState.CRIT, GuardState.STOP, GuardState.ROLLBACK):
                msg  = _alert_message(target, pct, total, prev_state, sonnet_pct, five_hour_pct)
                sent = _send_telegram(msg)
                state_data["last_telegram_sent"] = now_iso if sent else ""
            else:
                logger.info("State WARN/NORMAL — suppressing D2MC2C, will surface in AM brief")

    state_data.update({
        "last_pct":           pct,
        "last_five_hour_pct": five_hour_pct,
        "last_total":         total,
        "last_updated":       now_iso,
    })
    save_state(state_data)

    remaining = tokens_remaining(pct)
    return {
        "state":               target.value,
        "prev_state":          prev_state.value,
        "transitioned":        transitioned,
        "weekly_pct":          pct,
        "five_hour_pct":       five_hour_pct,
        "sonnet_weekly_pct":   sonnet_pct,
        "total_tokens":        total,
        "tokens_remaining":    remaining,
        "degradation_active":  state_data["degradation_active"],
        "degradation_mode":    state_data["degradation_mode"],
        "routing_sample":      get_routing_override("client booking urgent", target),
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if "--route" in sys.argv:
        # Usage: python3 thunderbird_rate_limit_guard.py --route "task description"
        idx  = sys.argv.index("--route")
        task = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "generic task"
        r    = route_task(task)
        print(json.dumps(r, indent=2))
    elif "--state" in sys.argv:
        print(json.dumps(load_state(), indent=2))
    elif "--test-alert" in sys.argv:
        state_data = load_state()
        state      = GuardState(state_data.get("state", "NORMAL"))
        pct        = state_data.get("last_pct", 0.0)
        total      = state_data.get("last_total", 0)
        msg        = _alert_message(state, pct, total, GuardState.NORMAL)
        sent       = _send_telegram(msg)
        print(f"Alert sent: {sent}")
        print(msg)
    else:
        result = evaluate(send_alerts=True)
        print(json.dumps(result, indent=2))
