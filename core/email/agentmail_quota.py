"""AgentMail quota guard — free tier caps: 100 emails/day, 3,000/month, 3 inboxes.

Tracks sends in a local JSON ledger and refuses (loud, not silent) before a send
would blow the daily/monthly ceiling. Buffer kept at 90/day, 2800/month so a
burst doesn't hard-fail mid-conversation.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parents[2] / "OpsCenter" / "state" / "agentmail_quota.json"
DAILY_LIMIT = 100
DAILY_BUFFER = 90
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
    return {
        "day_count": state["day_count"], "day_limit": DAILY_LIMIT,
        "month_count": state["month_count"], "month_limit": MONTHLY_LIMIT,
    }


def status() -> dict:
    state = _load()
    return {
        "today": state.get("day"), "day_count": state.get("day_count", 0), "day_limit": DAILY_LIMIT,
        "month": state.get("month"), "month_count": state.get("month_count", 0), "month_limit": MONTHLY_LIMIT,
    }
