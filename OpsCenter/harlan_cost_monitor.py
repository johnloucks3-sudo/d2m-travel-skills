#!/usr/bin/env python3
"""
harlan_cost_monitor.py — A9 Victor "Vic" Harlan Daily Cost Brief
Fires daily at 06:00 per thunderbird-harlan-daily.timer.

Three reporting windows:
  - Weekly rolling (last 7 days)
  - Current calendar month (month-start → now)
  - Prior full calendar month (1st → last day of previous month)

Each window shows provider-split costs:
  - Claude (anthropic providerID)
  - OpenCode native (opencode providerID)
  - OpenRouter (openrouter providerID — paid and free tier)

Usage:
    python3 OpsCenter/harlan_cost_monitor.py           # print + append to hale_decisions.md
    python3 OpsCenter/harlan_cost_monitor.py --telegram # also send to Commander via Telegram
    python3 OpsCenter/harlan_cost_monitor.py --no-append # skip appending to hale_decisions.md

Inputs:
    ~/.local/share/opencode/opencode.db  — OpenCode session costs (SQLite)
    OpsCenter/claude_usage_status.json   — Claude MAX plan message budget
    OPENROUTER_API_KEY from .env         — OpenRouter balance check
"""

import argparse
import calendar
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
THUNDERBIRD = Path("/home/john/Thunderbird")
ENV_FILE = THUNDERBIRD / ".env"
DB_PATH = Path.home() / ".local/share/opencode/opencode.db"
USAGE_STATUS = THUNDERBIRD / "OpsCenter/claude_usage_status.json"
DECISIONS_LOG = THUNDERBIRD / "hale_decisions.md"
COMMANDER_REPORT = THUNDERBIRD / "OpsCenter" / "commander_cost_report.json"
HARLAN_VERDICT = THUNDERBIRD / "OpsCenter" / "harlan_verdict.json"

# ── Commander Cost Report ──────────────────────────────────────────────────────

def read_commander_report() -> dict:
    """Read Commander's uploaded Claude MAX limits (from TG /report-limits)."""
    if COMMANDER_REPORT.exists():
        try:
            return json.loads(COMMANDER_REPORT.read_text())
        except Exception:
            pass
    return {}

# ── Harlan Verdict ─────────────────────────────────────────────────────────────

def write_verdict(
    sonnet_weekly_pct: float = 0.0,
    all_weekly_pct: float = 0.0,
    session_pct: float = 0.0,
    monthly_spent: float = 0.0,
    monthly_limit: float = 100.0,
    flags: list[str] | None = None,
    deepseek_wandering: bool = False,
) -> dict:
    """Write harlan_verdict.json — the single source of truth for budget decisions.
    
    Verdict logic (thresholds set by Commander via SO):
      - Sonnet weekly >= 95% → BLOCK
      - Sonnet weekly >= 80% or all_weekly >= 85% → DEGRADE
      - DeepSeek V4 wandering into banned models → ALARM (DEGRADE)
      - Otherwise → PASS
    """
    flags = flags or []
    alarm = "PASS"
    reason = "All within budget."
    degrade_reason = ""

    # Priority: BLOCK > DEGRADE. DeepSeek wandering is a flag, not a verdict override.
    if sonnet_weekly_pct >= 95:
        alarm = "BLOCK"
        reason = f"Sonnet weekly at {sonnet_weekly_pct:.0f}% — hard block until reset"
    elif sonnet_weekly_pct >= 80:
        alarm = "DEGRADE"
        reason = f"Sonnet weekly at {sonnet_weekly_pct:.0f}% — degrade to free tier"
        degrade_reason = "sonnet_exhausted"
    elif all_weekly_pct >= 85:
        alarm = "DEGRADE"
        reason = f"All-models weekly at {all_weekly_pct:.0f}% — degrade non-urgent tasks"
        degrade_reason = "all_models_high"

    if deepseek_wandering:
        reason += " | DeepSeek V4 wandering — investigate routing"
        degrade_reason = "deepseek_wandering"
        flags.append("DEEPSEEK WANDERING: DeepSeek V4 used banned or high-cost models")
        if alarm == "PASS":
            alarm = "DEGRADE"

    if monthly_spent > 0 and monthly_limit > 0:
        monthly_pct = (monthly_spent / monthly_limit) * 100
        if monthly_pct >= 90:
            if alarm == "PASS":
                alarm = "DEGRADE"
            reason += f" | Monthly spend at ${monthly_spent:.2f}/{monthly_limit:.0f} ({monthly_pct:.0f}%)"

    verdict = {
        "verdict": alarm,
        "sonnet_weekly_pct": sonnet_weekly_pct,
        "all_models_weekly_pct": all_weekly_pct,
        "session_pct": session_pct,
        "monthly_spent_usd": monthly_spent,
        "monthly_limit_usd": monthly_limit,
        "reason": reason,
        "degrade_reason": degrade_reason,
        "flags": flags,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "source": "commander_report" if COMMANDER_REPORT.exists() else "db_fallback",
    }
    HARLAN_VERDICT.write_text(json.dumps(verdict, indent=2))
    return verdict


# ── Provider buckets ───────────────────────────────────────────────────────────
PROVIDER_CLAUDE    = "anthropic"
PROVIDER_OPENCODE  = "opencode"
PROVIDER_OR        = "openrouter"

# ── Free model markers ────────────────────────────────────────────────────────
FREE_SUFFIXES = {":free"}
FREE_IDS = {
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
    "google/gemini-3.1-flash-lite-preview",
    "deepseek/deepseek-chat-v3.1",
    "anthropic/claude-3-haiku",
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4o",
}


# ── Time windows ──────────────────────────────────────────────────────────────

def get_window_bounds() -> dict:
    """Return epoch-millisecond boundaries for the three reporting windows."""
    now = datetime.now(timezone.utc)
    today = now.date()

    # Weekly: last 7 rolling days
    week_start = now - timedelta(days=7)
    week_start_ms = int(week_start.timestamp() * 1000)

    # Current calendar month: 1st of this month → now
    cur_month_start = date(today.year, today.month, 1)
    cur_month_start_dt = datetime(
        cur_month_start.year, cur_month_start.month, cur_month_start.day,
        tzinfo=timezone.utc
    )
    cur_month_start_ms = int(cur_month_start_dt.timestamp() * 1000)
    now_ms = int(now.timestamp() * 1000)

    # Prior full calendar month
    if today.month == 1:
        prior_year, prior_month = today.year - 1, 12
    else:
        prior_year, prior_month = today.year, today.month - 1

    prior_month_start = date(prior_year, prior_month, 1)
    prior_month_end_day = calendar.monthrange(prior_year, prior_month)[1]
    prior_month_end = date(prior_year, prior_month, prior_month_end_day)

    prior_start_dt = datetime(
        prior_month_start.year, prior_month_start.month, prior_month_start.day,
        tzinfo=timezone.utc
    )
    prior_end_dt = datetime(
        prior_month_end.year, prior_month_end.month, prior_month_end.day,
        23, 59, 59, tzinfo=timezone.utc
    )
    prior_start_ms = int(prior_start_dt.timestamp() * 1000)
    prior_end_ms   = int(prior_end_dt.timestamp() * 1000)

    return {
        "weekly": {
            "label": f"Weekly (last 7 days — {week_start.strftime('%b %d')} → now)",
            "start_ms": week_start_ms,
            "end_ms": now_ms,
        },
        "cur_month": {
            "label": f"Current Month ({cur_month_start.strftime('%B %Y')})",
            "start_ms": cur_month_start_ms,
            "end_ms": now_ms,
        },
        "prior_month": {
            "label": f"Prior Month ({prior_month_start.strftime('%B %Y')})",
            "start_ms": prior_start_ms,
            "end_ms": prior_end_ms,
        },
    }


# ── Model parsing ─────────────────────────────────────────────────────────────

def _parse_model(raw_model: str) -> dict:
    """Parse the JSON model column from opencode.db."""
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

    model_id   = m.get("id", "unknown")
    provider_id = m.get("providerID", "unknown")
    variant    = m.get("variant", "default")

    is_native = provider_id == PROVIDER_OPENCODE
    is_free = (
        is_native
        or any(model_id.endswith(s) for s in FREE_SUFFIXES)
        or model_id in FREE_IDS
    )

    # High-variant native models bill a reasoning surcharge
    if is_native and variant == "high":
        is_free = False

    display = model_id
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


# ── DB queries ────────────────────────────────────────────────────────────────

def query_window(start_ms: int, end_ms: int) -> list[dict]:
    """Return per-model stats for a given millisecond window."""
    if not DB_PATH.exists():
        return []

    rows = []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """SELECT model, SUM(cost), COUNT(*), SUM(tokens_input), SUM(tokens_output)
               FROM session
               WHERE time_created >= ? AND time_created < ? AND model IS NOT NULL
               GROUP BY model
               ORDER BY SUM(cost) DESC""",
            (start_ms, end_ms),
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
    return rows


def split_by_provider(rows: list[dict]) -> dict:
    """Split rows into three provider buckets."""
    buckets = {
        PROVIDER_CLAUDE:   [],
        PROVIDER_OPENCODE: [],
        PROVIDER_OR:       [],
        "other":           [],
    }
    for r in rows:
        pid = r["provider_id"]
        if pid in buckets:
            buckets[pid].append(r)
        else:
            buckets["other"].append(r)
    return buckets


# ── OR balance ────────────────────────────────────────────────────────────────

def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def query_or_balance(api_key: str) -> dict:
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


# ── Flags ─────────────────────────────────────────────────────────────────────

def detect_flags(all_rows: list[dict], or_data: dict) -> list[str]:
    """Detect cost anomalies across all rows (window-agnostic)."""
    flags = []
    seen = set()

    for r in all_rows:
        mid = r["model_id"]
        cost = r["cost"]
        key = (mid, r["variant"])
        if key in seen:
            continue
        seen.add(key)

        if r["is_native"] and r["variant"] != "high" and cost > 0.001:
            flags.append(
                f"NATIVE BILLING: {r['display']} charged ${cost:.4f} — "
                f"native provider should be $0"
            )

        if r["is_native"] and r["variant"] == "high" and cost > 1.0:
            flags.append(
                f"HIGH-VARIANT COST: {r['display']} ${cost:.4f} "
                f"({r['sessions']} sessions, {r['tokens_in']:,} in tokens) — "
                f"consider default variant for ops tasks"
            )

        if mid in BANNED_PAID and cost > 0:
            flags.append(
                f"BANNED MODEL ACTIVE: {mid} billed ${cost:.4f} "
                f"— replace with native/free alternative"
            )

        if r["is_free"] and not r["is_native"] and cost > 0.01:
            flags.append(
                f"FREE-TIER BILLING: {r['display']} charged ${cost:.4f} "
                f"— check OR rate limits or variant"
            )

        if r["tokens_in"] > 5_000_000 and r["sessions"] <= 5:
            avg_in = r["tokens_in"] // r["sessions"]
            flags.append(
                f"CONTEXT BLOAT: {r['display']} avg {avg_in:,} in tokens/session "
                f"({r['sessions']} sessions) — review prompt compression"
            )

    balance = or_data.get("limit", 0) or 0
    usage   = or_data.get("usage", 0) or 0
    remaining = max(balance - usage, 0)
    if "error" not in or_data:
        if remaining == 0:
            flags.append("OR BALANCE ZERO: OpenRouter credits exhausted — native/free-tier only")
        elif remaining < 5:
            flags.append(f"OR BALANCE LOW: ${remaining:.2f} remaining — replenish or migrate paid calls")

    return flags


# ── Recommendation ────────────────────────────────────────────────────────────

def pick_recommendation(weekly_rows: list[dict], flags: list[str]) -> str:
    if not weekly_rows:
        return "No OpenCode sessions recorded this week — check if OpenCode is running."

    banned_active = [r for r in weekly_rows if r["model_id"] in BANNED_PAID and r["cost"] > 0]
    if banned_active:
        worst = max(banned_active, key=lambda r: r["cost"])
        return (
            f"Eliminate {worst['model_id']} calls (${worst['cost']:.4f} this week). "
            f"Replace with opencode/big-pickle — same capability, $0 cost."
        )

    high_native = [r for r in weekly_rows if r["is_native"] and r["variant"] == "high" and r["cost"] > 1]
    if high_native:
        worst = max(high_native, key=lambda r: r["cost"])
        return (
            f"Switch {worst['model_id']} [high] → [default] for routine ops. "
            f"Reserve 'high' for complex reasoning only — saves ~${worst['cost']:.2f}/week."
        )

    total = sum(r["cost"] for r in weekly_rows)
    if total < 0.50:
        return "Cost profile optimal — all key tasks routing to native/free models."

    paid = [r for r in weekly_rows if not r["is_free"]]
    if paid:
        worst = max(paid, key=lambda r: r["cost"])
        return (
            f"Weekly paid spend ${total:.2f}. Primary: {worst['display']} (${worst['cost']:.2f}). "
            f"Confirm this model is justified for those {worst['sessions']} sessions."
        )

    return f"Weekly cost ${total:.2f} — cost profile acceptable."


# ── Brief builder ─────────────────────────────────────────────────────────────

def _fmt_provider_block(label: str, rows: list[dict]) -> list[str]:
    """Render one provider block for a window."""
    lines = [f"  [{label}]"]
    if not rows:
        lines.append("    No sessions recorded.")
        return lines

    total_cost = sum(r["cost"] for r in rows)
    total_sessions = sum(r["sessions"] for r in rows)
    lines.append(f"    Total: ${total_cost:.4f} | {total_sessions} sessions")

    for r in rows:
        tags = []
        if r["is_native"] and r["variant"] != "high":
            tags.append("NATIVE $0")
        if r["is_free"] and not r["is_native"]:
            tags.append("FREE")
        if r["model_id"] in BANNED_PAID:
            tags.append("⚠ BANNED")
        if r["is_native"] and r["variant"] == "high":
            tags.append("HIGH-VARIANT $")
        tag_str = f" [{', '.join(tags)}]" if tags else ""

        avg_in  = r["tokens_in"]  // r["sessions"] if r["sessions"] else 0
        avg_out = r["tokens_out"] // r["sessions"] if r["sessions"] else 0
        lines.append(
            f"    • {r['display']}{tag_str}"
        )
        lines.append(
            f"      ${r['cost']:.4f} | {r['sessions']} sess | "
            f"avg {avg_in:,} in / {avg_out:,} out"
        )
    return lines


def _fmt_window_section(window_label: str, rows: list[dict]) -> list[str]:
    """Render one full window section with provider subsections."""
    buckets = split_by_provider(rows)
    total_cost = sum(r["cost"] for r in rows)
    total_sessions = sum(r["sessions"] for r in rows)

    lines = [
        f"── {window_label} ──",
        f"  TOTAL: ${total_cost:.4f} | {total_sessions} sessions",
        "",
    ]
    lines += _fmt_provider_block("Claude (anthropic)", buckets[PROVIDER_CLAUDE])
    lines.append("")
    lines += _fmt_provider_block("OpenCode native", buckets[PROVIDER_OPENCODE])
    lines.append("")
    lines += _fmt_provider_block("OpenRouter", buckets[PROVIDER_OR])
    if buckets["other"]:
        lines.append("")
        lines += _fmt_provider_block("Other", buckets["other"])
    return lines


def build_brief(
    windows: dict,
    claude_usage: dict,
    commander_report: dict,
    verdict: dict,
) -> str:
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    weekly_rows = windows["weekly"]["rows"]
    cur_rows = windows["cur_month"]["rows"]
    all_rows = weekly_rows + cur_rows + windows["prior_month"]["rows"]

    weekly_total = sum(r["cost"] for r in weekly_rows)
    cur_total = sum(r["cost"] for r in cur_rows)

    sonnet_wk = verdict.get("sonnet_weekly_pct", claude_usage.get("sonnet_weekly_pct", 0))
    all_wk = verdict.get("all_models_weekly_pct", claude_usage.get("all_models_weekly_pct", 0))
    monthly = verdict.get("monthly_spent_usd", 0)
    monthly_limit = verdict.get("monthly_limit_usd", 100)

    # DeepSeek V4 wander check
    deepseek_models = [r for r in all_rows if "deepseek" in r.get("model_id", "").lower()]
    banned_deepseek = [r for r in deepseek_models if r.get("model_id") in BANNED_PAID]

    v_icon = {"PASS": "✅", "DEGRADE": "🟡", "BLOCK": "🔴"}.get(verdict["verdict"], "❓")

    lines = [
        f"HARLAN AM BRIEF — {today_str}",
        f"{v_icon} Verdict: {verdict['verdict']} | {verdict['reason']}",
        f"───" if verdict["verdict"] == "PASS" else f"═══",
        f"Sonnet weekly: {sonnet_wk:.0f}% | All weekly: {all_wk:.0f}%",
        f"Monthly: ${monthly:.2f}/{monthly_limit:.0f}",
        f"OpenCode 7d: ${weekly_total:.4f} | Month: ${cur_total:.4f}",
    ]

    if banned_deepseek:
        for r in banned_deepseek:
            lines.append(f"⚠ DEEPSEEK WANDER: {r['model_id']} ${r['cost']:.4f}")

    if deepseek_models:
        ds_total = sum(r["cost"] for r in deepseek_models)
        ds_sessions = sum(r["sessions"] for r in deepseek_models)
        lines.append(f"DeepSeek V4: {ds_sessions} sessions, ${ds_total:.4f}")

    if verdict.get("flags"):
        for f in verdict["flags"][:3]:
            lines.append(f"  ⚠ {f}")

    lines.append("— A9 Harlan | Thunderbird Wing")
    return "\n".join(lines)


# ── Persistence ───────────────────────────────────────────────────────────────

def append_to_decisions(brief: str) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    section = f"\n\n---\n## Harlan Cost Brief — {today}\n```\n{brief}\n```\n"
    try:
        with open(DECISIONS_LOG, "a") as f:
            f.write(section)
    except Exception as e:
        print(f"[harlan] Could not append to {DECISIONS_LOG}: {e}", file=sys.stderr)


def send_telegram(brief: str, env: dict) -> None:
    token   = env.get("TELEGRAM_C2_BOT_TOKEN") or os.environ.get("TELEGRAM_C2_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_COMMANDER_ID") or os.environ.get("TELEGRAM_COMMANDER_ID")
    if not token or not chat_id:
        print("[harlan] Telegram creds not found — skipping send.", file=sys.stderr)
        return
    try:
        import urllib.request, urllib.parse
        msg  = brief[:4000] + ("\n[truncated]" if len(brief) > 4000 else "")
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
        req  = urllib.request.Request(
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="A9 Harlan — Daily Cost Brief")
    parser.add_argument("--telegram",   action="store_true", help="Send brief to Commander via Telegram")
    parser.add_argument("--no-append",  action="store_true", help="Skip appending to hale_decisions.md")
    args = parser.parse_args()

    env = _load_env()

    # Build time windows
    bounds = get_window_bounds()

    # Query each window
    windows = {}
    for key, meta in bounds.items():
        windows[key] = {
            "label":   meta["label"],
            "rows":    query_window(meta["start_ms"], meta["end_ms"]),
        }

    all_rows = windows["weekly"]["rows"] + windows["cur_month"]["rows"] + windows["prior_month"]["rows"]

    claude_usage = read_claude_usage()
    commander_report = read_commander_report()

    # Sonnet weekly: Commander's report > claude_usage_reports > claude_usage_status > 0
    sonnet_wk = commander_report.get("sonnet_weekly_pct")
    if sonnet_wk is None:
        sonnet_wk = claude_usage.get("sonnet_weekly_pct", 0)
    all_wk = commander_report.get("all_models_weekly_pct", 0)
    session = commander_report.get("session_pct", 0)
    monthly = commander_report.get("monthly_spent_usd", 0)
    monthly_limit = commander_report.get("monthly_limit_usd", 100)

    # DeepSeek V4 wander check
    deepseek_models = [r for r in all_rows if "deepseek" in r.get("model_id", "").lower()]
    banned_deepseek = [r for r in deepseek_models if r.get("model_id") in BANNED_PAID]
    deepseek_wandering = len(banned_deepseek) > 0

    # Build flags
    flags = detect_flags(all_rows, {})

    # Write verdict — single source of truth for the budget guard
    verdict = write_verdict(
        sonnet_weekly_pct=sonnet_wk,
        all_weekly_pct=all_wk,
        session_pct=session,
        monthly_spent=monthly,
        monthly_limit=monthly_limit,
        flags=flags,
        deepseek_wandering=deepseek_wandering,
    )

    brief = build_brief(windows, claude_usage, commander_report, verdict)
    print(brief)
    print(f"\n[harlan] Verdict: {verdict['verdict']} — written to {HARLAN_VERDICT}")

    if not args.no_append:
        append_to_decisions(brief)
        print(f"[harlan] Brief appended to {DECISIONS_LOG}")

    if args.telegram:
        send_telegram(brief, env)


if __name__ == "__main__":
    main()
