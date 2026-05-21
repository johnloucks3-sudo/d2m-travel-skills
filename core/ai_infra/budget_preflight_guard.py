"""
budget_preflight_guard.py — Runtime budget guard that checks ALL cost pools
before authorizing a model call.

Decision hierarchy (highest authority first):
  1. harlan_verdict.json  — A9 Harlan's VETO authority. If BLOCK → hard stop.
  2. commander_cost_report.json — Commander's verbally uploaded Claude MAX stats.
  3. claude_usage_status.json — Claude MAX session % (stale, fallback only).
  4. claude_usage_reports (DB) — Sonnet weekly % (fallback if no Commander report).
  5. ZEN usage (DB) — OpenCode free-tier headroom.

Commander Standing Orders (2026-05-21):
  - NO OpenRouter models. Zero. Hard block at registration.
  - Sonnet leakage = unacceptable. Guard must strip Claude MAX at 80% Sonnet weekly.
  - DeepSeek V4 is the fallback — Harlan watches for wandering.
"""
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

log = logging.getLogger("budget_preflight_guard")

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")

# ── Sources ────────────────────────────────────────────────────────────────────
CLAUD_STATUS = THUNDERBIRD_DIR / "OpsCenter" / "claude_usage_status.json"
COST_DB = THUNDERBIRD_DIR / "storage" / "ai_costs.db"
HARLAN_VERDICT = THUNDERBIRD_DIR / "OpsCenter" / "harlan_verdict.json"
COMMANDER_REPORT = THUNDERBIRD_DIR / "OpsCenter" / "commander_cost_report.json"


class GuardVerdict(str, Enum):
    PASS = "PASS"
    DEGRADE = "DEGRADE"
    BLOCK = "BLOCK"


@dataclass
class PoolSnapshot:
    """Current headroom for one cost dimension."""
    pool: str
    pct_used: float
    limit: float
    remaining: float
    verdict: GuardVerdict
    reason: str = ""


@dataclass
class PreFlightResult:
    """Aggregate pre-flight result — all pools checked."""
    verdict: GuardVerdict
    pools: list[PoolSnapshot] = field(default_factory=list)
    degraded_model_hint: str = ""
    checked_at: float = 0.0

    @property
    def ok(self) -> bool:
        return self.verdict != GuardVerdict.BLOCK

    @property
    def should_degrade(self) -> bool:
        return self.verdict == GuardVerdict.DEGRADE


_CLAUDE_CACHE: dict | None = None
_CLAUDE_CACHE_TS: float = 0
_CLAUDE_CACHE_TTL = 15  # seconds
_LOCK = threading.Lock()


# ── Claude MAX session reader ─────────────────────────────────────────────────

def _read_claude_usage() -> dict:
    """Read claude_usage_status.json with TTL cache."""
    global _CLAUDE_CACHE, _CLAUDE_CACHE_TS
    now = time.monotonic()
    if _CLAUDE_CACHE is not None and (now - _CLAUDE_CACHE_TS) < _CLAUDE_CACHE_TTL:
        return _CLAUDE_CACHE
    try:
        data = json.loads(CLAUD_STATUS.read_text())
        _CLAUDE_CACHE = data
        _CLAUDE_CACHE_TS = now
        return data
    except Exception as e:
        log.warning("Cannot read claude_usage_status.json: %s", e)
        return {}


def check_claude_session() -> PoolSnapshot:
    """Check Claude MAX session % against tight thresholds.
    Commander's MAX plan has 5 concurrent sessions. At 59% (3 used), we DEGRADE.
    """
    usage = _read_claude_usage()
    eff = usage.get("effective_messages", 0)
    limit = usage.get("session_limit", 225)
    pct = (eff / limit) * 100 if limit > 0 else 0

    if pct >= 75:
        return PoolSnapshot(
            pool="claude_max_session", pct_used=pct, limit=limit,
            remaining=max(0, limit - eff),
            verdict=GuardVerdict.BLOCK,
            reason=f"Claude MAX session at {pct:.0f}% — hard block (5-session plan)",
        )
    if pct >= 50:
        return PoolSnapshot(
            pool="claude_max_session", pct_used=pct, limit=limit,
            remaining=max(0, limit - eff),
            verdict=GuardVerdict.DEGRADE,
            reason=f"Claude MAX session at {pct:.0f}% — degrade (preserve 5-session plan)",
        )
    return PoolSnapshot(
        pool="claude_max_session", pct_used=pct, limit=limit,
        remaining=max(0, limit - eff),
        verdict=GuardVerdict.PASS,
        reason=f"Claude MAX session at {pct:.0f}% — OK",
    )


# ── ZEN headroom reader ───────────────────────────────────────────────────────

def _db_conn() -> sqlite3.Connection | None:
    if not COST_DB.exists():
        return None
    try:
        conn = sqlite3.connect(str(COST_DB), timeout=3)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        log.warning("Cannot open %s: %s", COST_DB, e)
        return None


def check_zen_usage() -> PoolSnapshot:
    """Check ZEN calls/hr and calls/day against limits from ai_costs.db."""
    conn = _db_conn()
    if conn is None:
        return PoolSnapshot(
            pool="zen_opencode", pct_used=0, limit=-1, remaining=-1,
            verdict=GuardVerdict.PASS,
            reason="No cost DB — ZEN check skipped",
        )
    try:
        # ZEN usage and limits are in separate tables
        usage_row = conn.execute(
            "SELECT calls_per_hour, calls_per_day FROM zen_usage ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        limits_rows = conn.execute(
            "SELECT requests_per_hour, requests_per_day FROM zen_limits "
            "WHERE model LIKE '%big-pickle' ORDER BY ts DESC LIMIT 1"
        ).fetchall()
        conn.close()
    except Exception:
        conn.close()
        return PoolSnapshot(
            pool="zen_opencode", pct_used=0, limit=-1, remaining=-1,
            verdict=GuardVerdict.PASS,
            reason="No ZEN data yet",
        )

    # Defaults: Big Pickle limits from ZEN_LIMITS in zen_check.py
    hr_limit = 50
    day_limit = 200
    for r in limits_rows:
        hr_limit = r["requests_per_hour"] or 50
        day_limit = r["requests_per_day"] or 200

    hr_used = usage_row["calls_per_hour"] if usage_row else 0
    day_used = usage_row["calls_per_day"] if usage_row else 0

    hr_pct = (hr_used / hr_limit) * 100 if hr_limit > 0 else 0
    day_pct = (day_used / day_limit) * 100 if day_limit > 0 else 0
    max_pct = max(hr_pct, day_pct)

    if max_pct >= 95:
        return PoolSnapshot(
            pool="zen_opencode", pct_used=max_pct, limit=min(hr_limit, day_limit),
            remaining=min(hr_limit - hr_used, day_limit - day_used),
            verdict=GuardVerdict.BLOCK,
            reason=f"ZEN at {max_pct:.0f}% (hr={hr_used}/{hr_limit}, day={day_used}/{day_limit})",
        )
    if max_pct >= 80:
        return PoolSnapshot(
            pool="zen_opencode", pct_used=max_pct, limit=min(hr_limit, day_limit),
            remaining=min(hr_limit - hr_used, day_limit - day_used),
            verdict=GuardVerdict.DEGRADE,
            reason=f"ZEN at {max_pct:.0f}% — degrade to alternate free model",
        )
    return PoolSnapshot(
        pool="zen_opencode", pct_used=max_pct, limit=min(hr_limit, day_limit),
        remaining=min(hr_limit - hr_used, day_limit - day_used),
        verdict=GuardVerdict.PASS,
        reason=f"ZEN at {max_pct:.0f}% — OK",
    )


# ── Claude MAX Sonnet weekly reader ────────────────────────────────────────────

def check_claude_sonnet_weekly() -> PoolSnapshot:
    """Check Claude MAX Sonnet weekly % from claude_usage_reports table.
    This catches the Sonnet-specific weekly cap (separate from all-models).
    Falls back to plan_snapshots if claude_usage_reports is unavailable.
    """
    conn = _db_conn()
    if conn is None:
        return PoolSnapshot(
            pool="claude_max_sonnet_weekly", pct_used=0, limit=-1, remaining=-1,
            verdict=GuardVerdict.PASS,
            reason="No cost DB — Sonnet weekly check skipped",
        )
    try:
        row = conn.execute(
            "SELECT sonnet_weekly_pct, all_models_weekly_pct, ts "
            "FROM claude_usage_reports ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        # Fallback: plan_snapshots also has weekly_all_pct
        if row is None or row["sonnet_weekly_pct"] is None:
            row2 = conn.execute(
                "SELECT monthly_pct, ts FROM plan_snapshots ORDER BY ts DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if row2 is not None and row2["monthly_pct"] is not None:
                pct = row2["monthly_pct"]
            else:
                return PoolSnapshot(
                    pool="claude_max_sonnet_weekly", pct_used=0, limit=-1, remaining=-1,
                    verdict=GuardVerdict.PASS,
                    reason="No Claude usage data yet",
                )
        else:
            pct = row["sonnet_weekly_pct"]
        conn.close()
    except Exception:
        conn.close()
        return PoolSnapshot(
            pool="claude_max_sonnet_weekly", pct_used=0, limit=-1, remaining=-1,
            verdict=GuardVerdict.PASS,
            reason="Claude usage query failed",
        )

    if pct >= 95:
        return PoolSnapshot(
            pool="claude_max_sonnet_weekly", pct_used=pct, limit=100,
            remaining=max(0.0, 100.0 - pct),
            verdict=GuardVerdict.BLOCK,
            reason=f"Sonnet weekly at {pct:.0f}% — hard block",
        )
    if pct >= 80:
        return PoolSnapshot(
            pool="claude_max_sonnet_weekly", pct_used=pct, limit=100,
            remaining=max(0.0, 100.0 - pct),
            verdict=GuardVerdict.DEGRADE,
            reason=f"Sonnet weekly at {pct:.0f}% — degrade to free tier",
        )
    return PoolSnapshot(
        pool="claude_max_sonnet_weekly", pct_used=pct, limit=100,
        remaining=max(0.0, 100.0 - pct),
        verdict=GuardVerdict.PASS,
        reason=f"Sonnet weekly at {pct:.0f}% — OK",
    )


# ── Pre-flight engine ──────────────────────────────────────────────────────────

def run_preflight() -> PreFlightResult:
    """Check all cost pools and return aggregate verdict.

    Decision hierarchy:
      1. Harlan's veto (harlan_verdict.json) — highest authority
      2. Commander's report (commander_cost_report.json) — uploaded stats
      3. Local checks (session JSON, DB tables) — fallback
    """
    pools: list[PoolSnapshot] = []
    pool_results: dict[str, GuardVerdict] = {}
    hint = ""

    # ── 1. Harlan's veto ──────────────────────────────────────────────────────
    harlan = read_harlan_verdict()
    if harlan is not None:
        hv = harlan.get("verdict", "PASS")
        reason = harlan.get("reason", "Harlan verdict — see harlan_verdict.json")

        if hv == "BLOCK":
            pools.append(PoolSnapshot(
                pool="harlan_veto", pct_used=100, limit=100,
                remaining=0, verdict=GuardVerdict.BLOCK, reason=reason,
            ))
            sonnet_pct = harlan.get("sonnet_weekly_pct", 0)
            if sonnet_pct >= 80:
                hint = "opencode/deepseek-v4-flash-free"
            return PreFlightResult(
                verdict=GuardVerdict.BLOCK, pools=pools,
                degraded_model_hint=hint, checked_at=time.time(),
            )

        if hv == "DEGRADE":
            pools.append(PoolSnapshot(
                pool="harlan_veto", pct_used=80, limit=100,
                remaining=20, verdict=GuardVerdict.DEGRADE, reason=reason,
            ))
            degrade_reason = harlan.get("degrade_reason", "")
            if "sonnet" in degrade_reason or "deepseek" in degrade_reason:
                hint = "opencode/deepseek-v4-flash-free"
            else:
                hint = "opencode/big-pickle"
            pool_results["harlan_veto"] = GuardVerdict.DEGRADE

    # ── 2. Commander's report ────────────────────────────────────────────────
    cmdr = read_commander_report()
    if cmdr is not None:
        sonnet_wk = cmdr.get("sonnet_weekly_pct")
        if sonnet_wk is not None:
            if sonnet_wk >= 95:
                pools.append(PoolSnapshot(
                    pool="claude_max_sonnet_weekly", pct_used=sonnet_wk, limit=100,
                    remaining=max(0.0, 100.0 - sonnet_wk),
                    verdict=GuardVerdict.BLOCK,
                    reason=f"Commander report: Sonnet weekly at {sonnet_wk:.0f}%",
                ))
                pool_results["claude_max_sonnet_weekly"] = GuardVerdict.BLOCK
                hint = hint or "opencode/deepseek-v4-flash-free"
            elif sonnet_wk >= 80:
                pools.append(PoolSnapshot(
                    pool="claude_max_sonnet_weekly", pct_used=sonnet_wk, limit=100,
                    remaining=max(0.0, 100.0 - sonnet_wk),
                    verdict=GuardVerdict.DEGRADE,
                    reason=f"Commander report: Sonnet weekly at {sonnet_wk:.0f}%",
                ))
                pool_results["claude_max_sonnet_weekly"] = GuardVerdict.DEGRADE
                hint = hint or "opencode/deepseek-v4-flash-free"
            else:
                pools.append(PoolSnapshot(
                    pool="claude_max_sonnet_weekly", pct_used=sonnet_wk, limit=100,
                    remaining=max(0.0, 100.0 - sonnet_wk),
                    verdict=GuardVerdict.PASS,
                    reason=f"Commander report: Sonnet weekly at {sonnet_wk:.0f}% — OK",
                ))
                pool_results["claude_max_sonnet_weekly"] = GuardVerdict.PASS

        all_wk = cmdr.get("all_models_weekly_pct")
        if all_wk is not None:
            if all_wk >= 85:
                pools.append(PoolSnapshot(
                    pool="claude_max_all_weekly", pct_used=all_wk, limit=100,
                    remaining=max(0.0, 100.0 - all_wk),
                    verdict=GuardVerdict.BLOCK,
                    reason=f"Commander report: All models weekly at {all_wk:.0f}%",
                ))
                pool_results["claude_max_all_weekly"] = GuardVerdict.BLOCK
                hint = hint or "opencode/deepseek-v4-flash-free"
            elif all_wk >= 70:
                pools.append(PoolSnapshot(
                    pool="claude_max_all_weekly", pct_used=all_wk, limit=100,
                    remaining=max(0.0, 100.0 - all_wk),
                    verdict=GuardVerdict.DEGRADE,
                    reason=f"Commander report: All models weekly at {all_wk:.0f}%",
                ))
                pool_results["claude_max_all_weekly"] = GuardVerdict.DEGRADE
                hint = hint or "opencode/deepseek-v4-flash-free"
            else:
                pools.append(PoolSnapshot(
                    pool="claude_max_all_weekly", pct_used=all_wk, limit=100,
                    remaining=max(0.0, 100.0 - all_wk),
                    verdict=GuardVerdict.PASS,
                    reason=f"Commander report: All models weekly at {all_wk:.0f}% — OK",
                ))
                pool_results["claude_max_all_weekly"] = GuardVerdict.PASS

        session = cmdr.get("session_pct")
        if session is not None:
            if session >= 95:
                pools.append(PoolSnapshot(
                    pool="claude_max_session", pct_used=session, limit=100,
                    remaining=max(0.0, 100.0 - session),
                    verdict=GuardVerdict.BLOCK,
                    reason=f"Commander report: Session at {session:.0f}%",
                ))
                pool_results["claude_max_session"] = GuardVerdict.BLOCK
                hint = hint or "opencode/deepseek-v4-flash-free"
            elif session >= 80:
                pools.append(PoolSnapshot(
                    pool="claude_max_session", pct_used=session, limit=100,
                    remaining=max(0.0, 100.0 - session),
                    verdict=GuardVerdict.DEGRADE,
                    reason=f"Commander report: Session at {session:.0f}%",
                ))
                pool_results["claude_max_session"] = GuardVerdict.DEGRADE
                hint = hint or "opencode/deepseek-v4-flash-free"
            else:
                pools.append(PoolSnapshot(
                    pool="claude_max_session", pct_used=session, limit=100,
                    remaining=max(0.0, 100.0 - session),
                    verdict=GuardVerdict.PASS,
                    reason=f"Commander report: Session at {session:.0f}% — OK",
                ))
                pool_results["claude_max_session"] = GuardVerdict.PASS
        monthly = cmdr.get("monthly_spent_usd")
        monthly_limit = cmdr.get("monthly_limit_usd", 100.0)
        if monthly is not None and monthly_limit > 0:
            monthly_pct = (monthly / monthly_limit) * 100
            if monthly_pct >= 90:
                pools.append(PoolSnapshot(
                    pool="monthly_spend", pct_used=monthly_pct,
                    limit=monthly_limit, remaining=monthly_limit - monthly,
                    verdict=GuardVerdict.BLOCK,
                    reason=f"Monthly spend ${monthly:.2f}/{monthly_limit:.0f} ({monthly_pct:.0f}%)",
                ))
                pool_results["monthly_spend"] = GuardVerdict.BLOCK
                hint = hint or "opencode/deepseek-v4-flash-free"
            elif monthly_pct >= 80:
                pools.append(PoolSnapshot(
                    pool="monthly_spend", pct_used=monthly_pct,
                    limit=monthly_limit, remaining=monthly_limit - monthly,
                    verdict=GuardVerdict.DEGRADE,
                    reason=f"Monthly spend ${monthly:.2f}/{monthly_limit:.0f} ({monthly_pct:.0f}%)",
                ))
                pool_results["monthly_spend"] = GuardVerdict.DEGRADE
                hint = hint or "opencode/deepseek-v4-flash-free"
            else:
                pools.append(PoolSnapshot(
                    pool="monthly_spend", pct_used=monthly_pct,
                    limit=monthly_limit, remaining=monthly_limit - monthly,
                    verdict=GuardVerdict.PASS,
                    reason=f"Monthly spend ${monthly:.2f}/{monthly_limit:.0f} ({monthly_pct:.0f}%) — OK",
                ))
                pool_results["monthly_spend"] = GuardVerdict.PASS

    else:
        # ── 3. Fallback: local checks ────────────────────────────────────────
        claude = check_claude_session()
        pools.append(claude)
        pool_results["claude_max_session"] = claude.verdict

        sonnet_wk = check_claude_sonnet_weekly()
        pools.append(sonnet_wk)
        pool_results["claude_max_sonnet_weekly"] = sonnet_wk.verdict

    # ── 4. ZEN check (always runs — independent of Claude) ───────────────────
    zen = check_zen_usage()
    pools.append(zen)
    pool_results["zen_opencode"] = zen.verdict

    # ── Aggregate ────────────────────────────────────────────────────────────
    verdicts = set(pool_results.values())
    if GuardVerdict.BLOCK in verdicts:
        final_verdict = GuardVerdict.BLOCK
    elif GuardVerdict.DEGRADE in verdicts:
        final_verdict = GuardVerdict.DEGRADE
    else:
        final_verdict = GuardVerdict.PASS

    # If Harlan already set a verdict, respect it even if local checks disagree
    if harlan is not None and harlan.get("verdict") == "DEGRADE" and final_verdict == GuardVerdict.PASS:
        final_verdict = GuardVerdict.DEGRADE

    return PreFlightResult(
        verdict=final_verdict,
        pools=pools,
        degraded_model_hint=hint,
        checked_at=time.time(),
    )


# ── Harlan Verdict Reader (highest authority) ─────────────────────────────────

def read_harlan_verdict() -> dict | None:
    """Read A9 Harlan's verdict. If present, this overrides all local checks."""
    if HARLAN_VERDICT.exists():
        try:
            return json.loads(HARLAN_VERDICT.read_text())
        except Exception as e:
            log.warning("Cannot read harlan_verdict.json: %s", e)
    return None


def read_commander_report() -> dict | None:
    """Read Commander's uploaded Claude MAX stats (TG /report-limits)."""
    if COMMANDER_REPORT.exists():
        try:
            return json.loads(COMMANDER_REPORT.read_text())
        except Exception as e:
            log.warning("Cannot read commander_cost_report.json: %s", e)
    return None


# ── Invalidation ───────────────────────────────────────────────────────────────

def invalidate_claude_cache():
    """Force re-read on next check_claude_session() call."""
    global _CLAUDE_CACHE
    with _LOCK:
        _CLAUDE_CACHE = None


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = run_preflight()
    print(f"Verdict: {result.verdict.value}")
    print(f"Degrade hint: {result.degraded_model_hint or '(none)'}")
    print()
    for p in result.pools:
        icon = {"PASS": "✅", "DEGRADE": "🟡", "BLOCK": "🔴"}.get(p.verdict.value, "❓")
        print(f"  {icon} {p.pool}: {p.pct_used:.0f}% used — {p.verdict.value}")
        print(f"     {p.reason}")
    print()
    print("Gate OK" if result.ok else "Gate BLOCKED")
