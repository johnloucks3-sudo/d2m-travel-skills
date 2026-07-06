"""AgentMail quota guard — free tier caps: 100 emails/day, 3,000/month, 3 inboxes.

Tracks sends in a local JSON ledger and refuses (loud, not silent) before a send
would blow the daily/monthly ceiling. Buffer kept at 90/day, 2800/month so a
burst doesn't hard-fail mid-conversation. A second, unconditional hard stop at
95/day sits between the buffer and the real 100 ceiling — it is checked
independently of DAILY_BUFFER so a future change to the buffer constant can't
silently remove the belt-and-suspenders stop (SO: AgentMail Austerity Measures
2026-07-06, post CI-probe quota-burn incident).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[2] / "OpsCenter" / "state" / "agentmail_quota.json"
DAILY_LIMIT = 100
DAILY_BUFFER = 90
DAILY_HARD_STOP = 95  # absolute floor, checked independently of DAILY_BUFFER
MONTHLY_LIMIT = 3000
MONTHLY_BUFFER = 2800


class QuotaExceeded(RuntimeError):
    pass


def _load():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"day": None, "day_count": 0, "month": None, "month_count": 0}


def _save(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def check_and_record(n: int = 1) -> dict:
    """Raise QuotaExceeded if sending n more would cross the buffer; else record and return status."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")

    state = _load()
    if state.get("day") != today:
        state["day"] = today
        state["day_count"] = 0
    if state.get("month") != month:
        state["month"] = month
        state["month_count"] = 0

    if state["day_count"] + n > DAILY_HARD_STOP:
        raise QuotaExceeded(
            f"AgentMail daily HARD STOP hit: {state['day_count']}/{DAILY_HARD_STOP} "
            f"(hard cap {DAILY_LIMIT}/day on free tier). Holding this send unconditionally."
        )
    if state["day_count"] + n > DAILY_BUFFER:
        raise QuotaExceeded(
            f"AgentMail daily buffer hit: {state['day_count']}/{DAILY_BUFFER} "
            f"(hard cap {DAILY_LIMIT}/day on free tier). Holding this send."
        )
    if state["month_count"] + n > MONTHLY_BUFFER:
        raise QuotaExceeded(
            f"AgentMail monthly buffer hit: {state['month_count']}/{MONTHLY_BUFFER} "
            f"(hard cap {MONTHLY_LIMIT}/month on free tier). Holding this send."
        )

    state["day_count"] += n
    state["month_count"] += n
    _save(state)
    _refresh_hale_state(state)
    return {
        "day_count": state["day_count"], "day_limit": DAILY_LIMIT,
        "month_count": state["month_count"], "month_limit": MONTHLY_LIMIT,
    }


HALE_STATE_PATH = Path(__file__).resolve().parents[2] / "hale_state.json"


def _refresh_hale_state(state: dict) -> None:
    """Best-effort refresh of hale_state.json's agentmail_quota_status on every send.

    Read-modify-write scoped to a single top-level key so a concurrently
    running daemon updating other keys (e.g. wing_health) isn't clobbered.
    Never raises — a monitoring-field write failure must not block a send.
    """
    try:
        now = datetime.now(timezone.utc)
        day_count = state.get("day_count", 0)
        hale_state = json.loads(HALE_STATE_PATH.read_text())
        hale_state["agentmail_quota_status"] = {
            "last_checked": now.isoformat(),
            "sends_used_today": day_count,
            "sends_available_today": max(0, DAILY_BUFFER - day_count),
            "pct_used": round(100 * day_count / DAILY_LIMIT, 1) if DAILY_LIMIT else 0,
        }
        HALE_STATE_PATH.write_text(json.dumps(hale_state, indent=2))
    except Exception:
        pass


def status() -> dict:
    state = _load()
    day_count = state.get("day_count", 0)
    return {
        "today": state.get("day"), "day_count": day_count, "day_limit": DAILY_LIMIT,
        "day_buffer": DAILY_BUFFER, "day_hard_stop": DAILY_HARD_STOP,
        "pct_used": round(100 * day_count / DAILY_LIMIT, 1) if DAILY_LIMIT else 0,
        "month": state.get("month"), "month_count": state.get("month_count", 0), "month_limit": MONTHLY_LIMIT,
    }
