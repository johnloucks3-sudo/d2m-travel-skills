"""
Thunderbird Usage Monitor
==========================
Dreams2Memories Travel, LLC

Tracks TWO independent Claude Max plan limits:
  1. SESSION limit  — 5-hour rolling block (~59.8M tokens)
  2. WEEKLY limit   — rolling 7-day window (estimated ~680M tokens all-models)

Sonnet has a SEPARATE weekly quota from Opus/all-models.
Strategy: default to Sonnet (preserves all-models budget), Opus only when essential.

Thresholds (both session and weekly):
  WARN  (70%) — heads-up
  CRIT  (85%) — slow down / switch model
  STOP  (95%) — hard cap approaching

Run:
  python3 thunderbird_usage_monitor.py            # check both limits, print status
  python3 thunderbird_usage_monitor.py --alert    # check + Telegram if threshold hit
  python3 thunderbird_usage_monitor.py --weekly   # weekly report only
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger("thunderbird_usage_monitor")

THUNDERBIRD_DIR  = Path.home() / "Thunderbird"
POE_ENV_FILE     = THUNDERBIRD_DIR / "config" / "poe.env"
TELEGRAM_BOT_ENV = THUNDERBIRD_DIR / "config" / "d2mc2c_bot.env"

# One-and-done dedup (2026-07-04, Silver/A7): --alert runs on a 20-min timer and
# re-sent every run while usage stayed in the WARN/CRIT/STOP band (hours at a
# time). Key on (scope, level) — session|CRIT, weekly|WARN, etc. An unchanged
# band stays silent, an escalation (WARN→CRIT) re-fires, and dropping out of the
# band clears the key so the next entry pages fresh.
DEDUP_STATE = THUNDERBIRD_DIR / "OpsCenter" / "state" / "thunderbird_usage_monitor_alert_dedup.json"

def _dedup_new_keys(active_keys):
    state = {}
    if DEDUP_STATE.exists():
        try:
            state = json.loads(DEDUP_STATE.read_text())
        except Exception:
            state = {}
    active_set = set(active_keys)
    state = {k: v for k, v in state.items() if k in active_set}
    new_keys = []
    for k in active_keys:
        if k not in state:
            new_keys.append(k)
            state[k] = datetime.now(timezone.utc).isoformat()
    DEDUP_STATE.parent.mkdir(parents=True, exist_ok=True)
    DEDUP_STATE.write_text(json.dumps(state, indent=2))
    return new_keys

# ── Limits ────────────────────────────────────────────────────────────────────
# Session: 5-hour block (from ccusage historical data)
SESSION_LIMIT = 59_826_434

# Weekly all-models: derived from UI (33% = 224M tokens → ~680M/week)
# This is an estimate — Anthropic doesn't publish the exact number
WEEKLY_LIMIT_ALL = 680_000_000

# Weekly Sonnet-only: separate budget, exact limit unknown — estimate conservatively
# Sonnet is ~5x cheaper than Opus so likely a larger token budget
WEEKLY_LIMIT_SONNET = 1_500_000_000   # conservative estimate, update if UI shows otherwise

WARN_PCT = 70
CRIT_PCT = 85
STOP_PCT = 95

# ── ccusage readers ───────────────────────────────────────────────────────────

def get_active_block() -> dict | None:
    """Return the currently active 5-hour billing block."""
    try:
        result = subprocess.run(
            ["ccusage", "blocks", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None
        blocks = json.loads(result.stdout).get("blocks", [])
        for b in reversed(blocks):
            if b.get("isActive") and not b.get("isGap"):
                return b
        for b in reversed(blocks):
            if not b.get("isGap"):
                return b
        return None
    except Exception as e:
        logger.error("get_active_block: %s", e)
        return None


def get_weekly_data() -> dict:
    """Return this week's token usage from ccusage weekly --json.

    Returns dict with keys: total_tokens, opus_tokens, sonnet_tokens,
    haiku_tokens, cost_usd, opus_pct_of_weekly, sonnet_pct_of_weekly
    """
    try:
        result = subprocess.run(
            ["ccusage", "weekly", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return {}

        data = json.loads(result.stdout)
        weeks = data.get("weekly", [])
        if not weeks:
            return {}

        # Current week is the last entry
        current = weeks[-1]
        total   = current.get("totalTokens", 0)
        cost    = current.get("totalCost", 0)

        # Per-model breakdown
        opus_tk   = 0
        sonnet_tk = 0
        haiku_tk  = 0
        for m in current.get("modelBreakdowns", []):
            name = m.get("modelName", "")
            tok  = (m.get("inputTokens", 0) + m.get("outputTokens", 0) +
                    m.get("cacheCreationTokens", 0) + m.get("cacheReadTokens", 0))
            if "opus"   in name: opus_tk   += tok
            elif "sonnet" in name: sonnet_tk += tok
            elif "haiku"  in name: haiku_tk  += tok

        return {
            "week":              current.get("week", "?"),
            "total_tokens":      total,
            "opus_tokens":       opus_tk,
            "sonnet_tokens":     sonnet_tk,
            "haiku_tokens":      haiku_tk,
            "cost_usd":          round(cost, 2),
            "all_pct":           round(total / WEEKLY_LIMIT_ALL * 100, 1),
            "sonnet_pct":        round(sonnet_tk / WEEKLY_LIMIT_SONNET * 100, 1),
            "opus_share_pct":    round(opus_tk / total * 100, 1) if total else 0,
            "sonnet_share_pct":  round(sonnet_tk / total * 100, 1) if total else 0,
        }
    except Exception as e:
        logger.error("get_weekly_data: %s", e)
        return {}

# ── Telegram ──────────────────────────────────────────────────────────────────

def _get_bot_token() -> str:
    for env_file in [POE_ENV_FILE, TELEGRAM_BOT_ENV]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            if "TELEGRAM_BOT_TOKEN=" in line:
                return line.split("=", 1)[1].strip()
    return ""

def _get_commander_chat_id() -> str:
    if not POE_ENV_FILE.exists():
        return ""
    for line in POE_ENV_FILE.read_text().splitlines():
        if line.strip().startswith("TELEGRAM_COMMANDER_ID="):
            return line.strip().split("=", 1)[1]
    return ""

def send_telegram_alert(message: str) -> bool:
    import urllib.request
    token   = _get_bot_token()
    chat_id = _get_commander_chat_id()
    if not token or not chat_id:
        print(f"[ALERT — no Telegram] {message}")
        return False
    try:
        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
        req     = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False

# ── Core check ────────────────────────────────────────────────────────────────

def _bar(pct: float, width: int = 20) -> str:
    filled = min(int(pct / (100 / width)), width)
    return "█" * filled + "░" * (width - filled)

def _level(pct: float) -> str:
    if pct >= STOP_PCT: return "STOP"
    if pct >= CRIT_PCT: return "CRIT"
    if pct >= WARN_PCT: return "WARN"
    return "ok"

def _emoji(level: str) -> str:
    return {"ok": "✅", "WARN": "⚠️", "CRIT": "🔴", "STOP": "🚨"}.get(level, "ℹ️")


def check_usage(send_alert: bool = False) -> dict:
    block  = get_active_block()
    weekly = get_weekly_data()

    alert_items = []  # (dedup_key, message)
    status = {}

    # ── SESSION block ──────────────────────────────────────────────────────────
    if block:
        total    = block.get("totalTokens", 0)
        proj     = block.get("projection", {}) or {}
        proj_tk  = proj.get("totalTokens", total)
        pct      = round(total / SESSION_LIMIT * 100, 1)
        proj_pct = round(proj_tk / SESSION_LIMIT * 100, 1)
        burn     = block.get("burnRate", {}) or {}
        burn_rpm = round(burn.get("tokensPerMinute", 0) / 1000, 1)
        remain   = round(proj.get("remainingMinutes", 0))
        cost     = round(block.get("costUSD", 0), 2)
        slevel   = _level(proj_pct)

        status["session"] = {
            "level": slevel, "used_pct": pct, "proj_pct": proj_pct,
            "burn_k_tpm": burn_rpm, "remain_min": remain, "cost_usd": cost,
        }

        s_msg = (
            f"{_emoji(slevel)} <b>Session Block</b>\n"
            f"[{_bar(proj_pct)}] {proj_pct}% projected\n"
            f"Used: {pct}% ({total/1e6:.1f}M / {SESSION_LIMIT/1e6:.0f}M)\n"
            f"Burn: {burn_rpm}K tok/min | ${cost:.2f} equiv | ~{remain}min left\n"
        )

        if slevel in ("CRIT", "STOP"):
            s_msg += "⚠️ <b>Switch to Sonnet or start fresh session</b>\n"

        print(s_msg.replace("<b>", "").replace("</b>", ""))
        if send_alert and slevel in ("WARN", "CRIT", "STOP"):
            alert_items.append((f"session|{slevel}", s_msg))

    # ── WEEKLY limits ─────────────────────────────────────────────────────────
    if weekly:
        all_pct     = weekly.get("all_pct", 0)
        sonnet_pct  = weekly.get("sonnet_pct", 0)
        opus_share  = weekly.get("opus_share_pct", 0)
        sonnet_share= weekly.get("sonnet_share_pct", 0)
        total_tok   = weekly.get("total_tokens", 0)
        cost_wk     = weekly.get("cost_usd", 0)
        wlevel      = _level(all_pct)

        status["weekly"] = {
            "level": wlevel, "all_pct": all_pct, "sonnet_pct": sonnet_pct,
            "opus_share": opus_share, "total_tokens": total_tok, "cost_usd": cost_wk,
        }

        w_msg = (
            f"{_emoji(wlevel)} <b>Weekly — All Models</b>\n"
            f"[{_bar(all_pct)}] {all_pct}% of weekly budget\n"
            f"Tokens: {total_tok/1e6:.0f}M | ${cost_wk:.2f} API equiv\n"
            f"Mix: Opus {opus_share}% | Sonnet {sonnet_share}% | "
            f"Haiku {100-opus_share-sonnet_share:.0f}%\n"
            f"\n"
            f"📊 <b>Weekly — Sonnet Only</b>\n"
            f"[{_bar(sonnet_pct)}] {sonnet_pct}% of Sonnet budget\n"
        )

        # Model switch recommendation
        if all_pct >= CRIT_PCT and opus_share > 50:
            w_msg += (
                "\n🔴 <b>Weekly budget critical — Opus is the culprit</b>\n"
                "Switch Claude Code to Sonnet:\n"
                "<code>Settings → model: claude-sonnet-4-6</code>\n"
            )
        elif all_pct >= WARN_PCT and opus_share > 70:
            w_msg += (
                f"\n⚠️ Opus is {opus_share}% of weekly spend. "
                "Default to Sonnet for routine work.\n"
            )
        elif all_pct < 50 and sonnet_pct < 30:
            w_msg += "\n✅ Healthy. Use Sonnet as default — Sonnet budget has plenty of room.\n"

        print(w_msg.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""))
        if send_alert and wlevel in ("WARN", "CRIT", "STOP"):
            alert_items.append((f"weekly|{wlevel}", w_msg))

    # ── Send combined Telegram alert (one-and-done dedup gate) ─────────────────
    if send_alert:
        new_keys = _dedup_new_keys([k for k, _ in alert_items])
        new_msgs = [m for k, m in alert_items if k in new_keys]
        if new_msgs:
            full_alert = (
                "⚡ <b>Claude Max Plan — Usage Alert</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                + "\n".join(new_msgs)
            )
            sent = send_telegram_alert(full_alert)
            status["telegram_sent"] = sent

    return status


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    send_alert = "--alert" in sys.argv
    weekly_only = "--weekly" in sys.argv

    if weekly_only:
        w = get_weekly_data()
        print(json.dumps(w, indent=2))
    else:
        result = check_usage(send_alert=send_alert)
        if "--json" in sys.argv:
            print(json.dumps(result, indent=2))
