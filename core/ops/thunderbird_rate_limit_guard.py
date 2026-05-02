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

POE_ENV_FILE     = CONFIG_DIR / "poe.env"
MAIN_ENV_FILE    = THUNDERBIRD_DIR / ".env"

# ── Thresholds ─────────────────────────────────────────────────────────────────
WEEKLY_LIMIT_ALL = 680_000_000   # tokens — all-models rolling 7-day

THRESH_WARN      = 70    # % — heads-up
THRESH_CRIT      = 85    # % — graceful degradation engages
THRESH_STOP      = 90    # % — hard guard, all to DeepSeek
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

def get_weekly_pct() -> tuple[float, int]:
    """Return (weekly_consumption_pct, total_tokens_used).
    Returns (0.0, 0) on failure.
    """
    try:
        result = subprocess.run(
            ["ccusage", "weekly", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return 0.0, 0

        data  = json.loads(result.stdout)
        weeks = data.get("weekly", [])
        if not weeks:
            return 0.0, 0

        current = weeks[-1]
        total   = current.get("totalTokens", 0)
        pct     = round(total / WEEKLY_LIMIT_ALL * 100, 2)
        return pct, total

    except Exception as e:
        logger.error("get_weekly_pct: %s", e)
        return 0.0, 0


def tokens_remaining(used_pct: float) -> int:
    """Tokens remaining in weekly budget."""
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
            "engine":    "max" | "openrouter_deepseek" | "normal",
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
                "engine":   "openrouter_deepseek",
                "model":    "deepseek/deepseek-chat-v3-0324",
                "reason":   "CRIT 85%+ — non-urgent → OpenRouter DeepSeek",
                "degraded": True,
            }

    if current_state == GuardState.STOP:
        return {
            "engine":   "openrouter_deepseek",
            "model":    "deepseek/deepseek-chat-v3-0324",
            "reason":   "STOP 90%+ — all tasks → OpenRouter DeepSeek",
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


# ── OpenRouter dispatch (degraded mode) ───────────────────────────────────────

def dispatch_openrouter(
    prompt: str,
    system: str = "You are a helpful assistant in the Thunderbird Wing for Dreams2Memories Travel.",
    model: str = "deepseek/deepseek-chat-v3-0324",
    max_tokens: int = 2048,
) -> str:
    """Send task to OpenRouter DeepSeek when in degraded mode."""
    import requests as _req  # noqa: PLC0415

    api_key = _read_env_key("OPENROUTER_API_KEY")
    if not api_key:
        return "[DEGRADED ERROR] OPENROUTER_API_KEY not configured"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer":  "https://dreams2memories.com",
        "X-Title":       "Thunderbird Wing — Degraded Mode",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":      model,
        "messages":   [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": max_tokens,
    }
    try:
        resp = _req.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[DEGRADED ERROR] OpenRouter failed: {e}"


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
    used_pct: float,
    total_tokens: int,
    prev_state: GuardState,
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
    bar_filled = min(int(used_pct / 5), 20)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    lines = [
        f"{icon} <b>Rate-Limit Guard — {new_state.value}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Transition: {prev_state.value} → <b>{new_state.value}</b>",
        f"Weekly: [{bar}] {used_pct:.1f}%",
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
            "• Non-urgent tasks → OpenRouter DeepSeek",
            "• Urgent/client tasks → Max preserved",
            "CLI monitor switched to blinking red.",
        ]
    elif new_state == GuardState.STOP:
        lines += [
            "🚨 <b>HARD GUARD ACTIVE — 90%+ consumed</b>",
            "• ALL tasks → OpenRouter DeepSeek",
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

def _compute_target_state(pct: float) -> GuardState:
    if pct < THRESH_ROLLBACK:
        return GuardState.ROLLBACK
    if pct < THRESH_WARN:
        return GuardState.NORMAL
    if pct < THRESH_CRIT:
        return GuardState.WARN
    if pct < THRESH_STOP:
        return GuardState.CRIT
    return GuardState.STOP


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
    target     = _compute_target_state(pct)
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

        logger.info("State transition: %s → %s (%.1f%%)", prev_state.value, target.value, pct)

        if send_alerts:
            msg  = _alert_message(target, pct, total, prev_state)
            sent = _send_telegram(msg)
            state_data["last_telegram_sent"] = now_iso if sent else ""

    state_data.update({
        "last_pct":     pct,
        "last_total":   total,
        "last_updated": now_iso,
    })
    save_state(state_data)

    remaining = tokens_remaining(pct)
    return {
        "state":               target.value,
        "prev_state":          prev_state.value,
        "transitioned":        transitioned,
        "weekly_pct":          pct,
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
