#!/usr/bin/env python3
"""
harlan_cost_monitor.py — A9 Victor "Vic" Harlan Weekly Cost Brief
Fires Monday per standing hook in hale_state.json.

Usage:
    python3 OpsCenter/harlan_cost_monitor.py           # generate brief, print + append to hale_decisions.md
    python3 OpsCenter/harlan_cost_monitor.py --telegram # also send to Commander via Telegram
    python3 OpsCenter/harlan_cost_monitor.py --days 14  # change lookback window (default 7)

Inputs:
    ~/.local/share/opencode/opencode.db  — OpenCode session costs (SQLite)
    OpsCenter/claude_usage_status.json   — Claude MAX plan message budget
    OPENROUTER_API_KEY from .env         — OpenRouter balance check
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD = Path("/home/john/Thunderbird")
ENV_FILE = THUNDERBIRD / ".env"
DB_PATH = Path.home() / ".local/share/opencode/opencode.db"
USAGE_STATUS = THUNDERBIRD / "OpsCenter/claude_usage_status.json"
DECISIONS_LOG = THUNDERBIRD / "hale_decisions.md"

# ── Free model markers (should cost $0 or near-$0) ───────────────────────────
FREE_PROVIDERS = {"opencode"}           # native = always $0 unless variant="high"
FREE_SUFFIXES  = {":free"}             # OR `:free` tier
FREE_IDS = {                            # known explicitly-free model IDs
    "opencode/big-pickle",
    "opencode/deepseek-v4-flash-free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
}

# Known paid models that should no longer be used
BANNED_PAID = {
    "x-ai/grok-4.1-fast",
    "openai/gpt-4o-mini",
    "openai/gpt-4.1-mini",
    "google/gemini-3.1-flash-lite-preview",   # paid OR path — use native instead
    "deepseek/deepseek-chat-v3.1",             # paid OR — use native instead
    "anthropic/claude-3-haiku",
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4o",
}


def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _parse_model(raw_model: str) -> dict:
    """Parse the JSON model column from opencode.db.
    Returns dict with keys: display, provider_id, model_id, variant, is_free, is_native
    """
    try:
        m = json.loads(raw_model)
    except (json.JSONDecodeError, TypeError):
        return {
            "display": str(raw_model),
            "provider_id": "unknown",
            "model_id": str(raw_model),
            "variant": "",
            "is_free": False,
            "is_native": False,
        }

    model_id = m.get("id", "unknown")
    provider_id = m.get("providerID", "unknown")
    variant = m.get("variant", "default")

    is_native = provider_id in FREE_PROVIDERS
    is_free = (
        is_native
        or any(model_id.endswith(s) for s in FREE_SUFFIXES)
        or model_id in FREE_IDS
    )

    # High-variant native models may still bill (e.g., reasoning surcharge)
    if is_native and variant == "high":
        is_free = False

    display = f"{model_id}"
    if variant and variant not in ("default", ""):
        display += f" [{variant}]"

    return {
        "display": display,
        "provider_id": provider_id,
        "model_id": model_id,
        "variant": variant,
        "is_free": is_free,
        "is_native": is_native,
    }


def query_opencode_db(days: int) -> list[dict]:
    """Return per-model stats for the last N days."""
    if not DB_PATH.exists():
        return []

    cutoff_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    prior_cutoff_ms = int((datetime.now(timezone.utc) - timedelta(days=days * 2)).timestamp() * 1000)

    rows = []
    with sqlite3.connect(DB_PATH) as conn:
        # Current window
        cur = conn.execute(
            """SELECT model, SUM(cost), COUNT(*), SUM(tokens_input), SUM(tokens_output)
               FROM session
               WHERE time_created > ? AND model IS NOT NULL
               GROUP BY model
               ORDER BY SUM(cost) DESC""",
            (cutoff_ms,),
        )
        for raw_model, cost, sessions, tok_in, tok_out in cur.fetchall():
            m = _parse_model(raw_model)
            rows.append({
                **m,
                "cost": round(cost or 0.0, 6),
                "sessions": sessions,
                "tokens_in": tok_in or 0,
                "tokens_out": tok_out or 0,
            })

        # Prior window (for trend)
        prior_cur = conn.execute(
            """SELECT SUM(cost) FROM session
               WHERE time_created > ? AND time_created <= ? AND model IS NOT NULL""",
            (prior_cutoff_ms, cutoff_ms),
        )
        prior_total = (prior_cur.fetchone() or [0])[0] or 0.0

    return rows, round(prior_total, 4)


def query_or_balance(api_key: str) -> dict:
    """Check OpenRouter API key for balance. Returns dict with credit info."""
    if not api_key:
        return {"error": "no API key"}
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data.get("data", data)
    except Exception as e:
        return {"error": str(e)}


def read_claude_usage() -> dict:
    if USAGE_STATUS.exists():
        try:
            return json.loads(USAGE_STATUS.read_text())
        except Exception:
            pass
    return {}


def detect_flags(rows: list[dict], or_data: dict) -> list[str]:
    """Return list of flag strings for Harlan to surface."""
    flags = []

    for r in rows:
        mid = r["model_id"]
        cost = r["cost"]

        # Native opencode model billing unexpectedly (not high variant)
        if r["is_native"] and r["variant"] != "high" and cost > 0.001:
            flags.append(
                f"NATIVE MODEL BILLING: {r['display']} charged ${cost:.4f} — "
                f"native provider should be $0"
            )

        # High-variant native — note it, not a hard flag
        if r["is_native"] and r["variant"] == "high" and cost > 1.0:
            flags.append(
                f"HIGH-VARIANT COST: {r['display']} cost ${cost:.4f} "
                f"({r['sessions']} sessions, {r['tokens_in']:,} input tokens) — "
                f"consider default variant for ops tasks"
            )

        # Banned paid model still running
        if mid in BANNED_PAID and cost > 0:
            flags.append(
                f"BANNED MODEL ACTIVE: {mid} billed ${cost:.4f} "
                f"— should be replaced with native/free alternative"
            )

        # Free-labelled model charging
        if r["is_free"] and not r["is_native"] and cost > 0.01:
            flags.append(
                f"FREE-TIER BILLING: {r['display']} charged ${cost:.4f} "
                f"— check OR rate limits or variant"
            )

        # Large input token sessions (possible context bloat)
        if r["tokens_in"] > 5_000_000 and r["sessions"] <= 5:
            avg_in = r["tokens_in"] // r["sessions"]
            flags.append(
                f"CONTEXT BLOAT: {r['display']} averaging {avg_in:,} input tokens/session "
                f"({r['sessions']} sessions) — review prompt compression"
            )

    # OR balance warning
    credit = or_data.get("limit_requests") or or_data.get("usage")
    balance = or_data.get("limit") or 0
    if "error" not in or_data and balance == 0:
        flags.append("OR BALANCE ZERO: OpenRouter paid credits exhausted — use native/free-tier only")
    elif "error" not in or_data and isinstance(balance, (int, float)) and balance < 5:
        flags.append(f"OR BALANCE LOW: ${balance:.2f} remaining — replenish or migrate remaining paid calls")

    return flags


def pick_recommendation(rows: list[dict], flags: list[str], prior_total: float) -> str:
    current_total = sum(r["cost"] for r in rows)

    if not rows:
        return "No OpenCode sessions recorded this period — check if OpenCode is running."

    # Check if banned models are active
    banned_active = [r for r in rows if r["model_id"] in BANNED_PAID and r["cost"] > 0]
    if banned_active:
        worst = max(banned_active, key=lambda r: r["cost"])
        return (
            f"Eliminate {worst['model_id']} calls (${worst['cost']:.4f} this week). "
            f"Replace with opencode/big-pickle — same capability, $0 cost."
        )

    # High variant native billing large
    high_native = [r for r in rows if r["is_native"] and r["variant"] == "high" and r["cost"] > 1]
    if high_native:
        worst = max(high_native, key=lambda r: r["cost"])
        return (
            f"Switch {worst['model_id']} from 'high' to 'default' variant for routine ops. "
            f"Reserve 'high' for complex reasoning tasks only — saves ~${worst['cost']:.2f}/week."
        )

    # Cost trending up
    if prior_total > 0 and current_total > prior_total * 1.25:
        pct = int((current_total / prior_total - 1) * 100)
        return (
            f"Weekly cost up {pct}% vs prior period (${prior_total:.2f} → ${current_total:.2f}). "
            f"Audit new model usage — check for new paid model introductions."
        )

    if current_total < 1.0:
        return "Cost profile optimal — all key tasks routing to native/free models."

    return (
        f"Total cost ${current_total:.2f} this week. "
        f"Primary spend: {rows[0]['display']} (${rows[0]['cost']:.2f}). "
        f"Confirm this model is the right tool for those {rows[0]['sessions']} sessions."
    )


def build_brief(rows: list[dict], prior_total: float, or_data: dict, claude_usage: dict, days: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    total_cost = sum(r["cost"] for r in rows)
    total_sessions = sum(r["sessions"] for r in rows)
    flags = detect_flags(rows, or_data)
    recommendation = pick_recommendation(rows, flags, prior_total)

    lines = [
        f"HARLAN WEEKLY COST BRIEF — {today} (last {days} days)",
        "=" * 60,
        f"Total spend: ${total_cost:.4f} | Sessions: {total_sessions} | Prior period: ${prior_total:.4f}",
        "",
    ]

    # OpenCode sessions table
    lines.append("OPENCODE SESSIONS BY MODEL:")
    if rows:
        for r in rows:
            free_tag = " [FREE]" if r["is_free"] and not r["is_native"] else ""
            native_tag = " [NATIVE $0]" if r["is_native"] and r["variant"] != "high" else ""
            flag_tag = " ⚠" if r["model_id"] in BANNED_PAID else ""
            avg_tok = r["tokens_in"] // r["sessions"] if r["sessions"] else 0
            lines.append(
                f"  {r['display']}{free_tag}{native_tag}{flag_tag}"
            )
            lines.append(
                f"    ${r['cost']:.4f} | {r['sessions']} sessions | "
                f"avg {avg_tok:,} in / {r['tokens_out']//max(r['sessions'],1):,} out tokens"
            )
    else:
        lines.append("  No session data found.")

    lines.append("")

    # OR balance
    lines.append("OPENROUTER BALANCE:")
    if "error" in or_data:
        lines.append(f"  Could not retrieve: {or_data['error']}")
    else:
        limit = or_data.get("limit", 0)
        usage = or_data.get("usage", 0)
        lines.append(f"  Credits: ${limit:.2f} limit | ${usage:.2f} used | ${max(limit-usage,0):.2f} remaining")

    lines.append("")

    # MAX plan usage
    lines.append("CLAUDE MAX PLAN:")
    if claude_usage:
        session_msgs = claude_usage.get("session_messages", "?")
        session_limit = claude_usage.get("session_limit", "?")
        weekly_msgs = claude_usage.get("weekly_messages", "?")
        weekly_limit = claude_usage.get("weekly_limit", "?")
        budget = claude_usage.get("budget_status", "UNKNOWN")
        lines.append(f"  Session: {session_msgs}/{session_limit} messages | Weekly: {weekly_msgs}/{weekly_limit}")
        lines.append(f"  Budget status: {budget}")
    else:
        lines.append("  claude_usage_status.json not found.")

    lines.append("")

    # Flags
    lines.append("OPTIMIZATION FLAGS:")
    if flags:
        for f in flags:
            lines.append(f"  ⚠ {f}")
    else:
        lines.append("  None — cost profile clean.")

    lines.append("")
    lines.append(f"RECOMMENDATION: {recommendation}")
    lines.append("")
    lines.append("— A9 Victor 'Vic' Harlan | Thunderbird Wing")

    return "\n".join(lines)


def append_to_decisions(brief: str) -> None:
    """Append the brief to hale_decisions.md under a dated section."""
    today = datetime.now().strftime("%Y-%m-%d")
    section = f"\n\n---\n## Harlan Cost Brief — {today}\n```\n{brief}\n```\n"
    try:
        with open(DECISIONS_LOG, "a") as f:
            f.write(section)
    except Exception as e:
        print(f"[harlan] Could not append to {DECISIONS_LOG}: {e}", file=sys.stderr)


def send_telegram(brief: str, env: dict) -> None:
    """Send the brief to Commander via Telegram. Best-effort."""
    token = env.get("TELEGRAM_C2_BOT_TOKEN") or os.environ.get("TELEGRAM_C2_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_COMMANDER_ID") or os.environ.get("TELEGRAM_COMMANDER_ID")
    if not token or not chat_id:
        print("[harlan] Telegram creds not found — skipping send.", file=sys.stderr)
        return
    try:
        import urllib.request
        import urllib.parse
        # Telegram has 4096 char limit — truncate if needed
        msg = brief[:4000] + ("\n[truncated]" if len(brief) > 4000 else "")
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            print("[harlan] Brief sent to Commander via Telegram.")
        else:
            print(f"[harlan] Telegram send failed: {result}", file=sys.stderr)
    except Exception as e:
        print(f"[harlan] Telegram send error: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="A9 Harlan — Weekly Cost Brief")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    parser.add_argument("--telegram", action="store_true", help="Send brief to Commander via Telegram")
    parser.add_argument("--no-append", action="store_true", help="Skip appending to hale_decisions.md")
    args = parser.parse_args()

    env = _load_env()

    # Gather data
    result = query_opencode_db(args.days)
    if isinstance(result, tuple):
        rows, prior_total = result
    else:
        rows, prior_total = result, 0.0

    or_api_key = env.get("OPENROUTER_API_KEY", "")
    or_data = query_or_balance(or_api_key)
    claude_usage = read_claude_usage()

    # Build brief
    brief = build_brief(rows, prior_total, or_data, claude_usage, args.days)

    # Output
    print(brief)

    if not args.no_append:
        append_to_decisions(brief)
        print(f"\n[harlan] Brief appended to {DECISIONS_LOG}")

    if args.telegram:
        # Only send if Monday OR forced
        today_weekday = datetime.now().weekday()  # 0=Monday
        if today_weekday == 0 or args.telegram:
            send_telegram(brief, env)


if __name__ == "__main__":
    main()
