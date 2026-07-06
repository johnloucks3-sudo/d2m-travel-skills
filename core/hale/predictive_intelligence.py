#!/usr/bin/env python3
"""
Hale Scan Phase 2 — Predictive Intelligence
Extends the Phase 1 proactive scan (deadline/stale/staff/consistency/conflict)
with five forward-looking signals: vendor contract expirations, insurance
policy renewals, commission reconciliation cadence, client re-engagement
windows, and competitor intel freshness.

Every function accepts injectable paths/`now` for testability and degrades
to an empty finding list when a source has no data — it never fabricates a
deadline or a rebook prediction from data that isn't there (Negative-Space
Rule, SO-PIPELINE-INTEGRITY-20260528).
"""

import json
import re
from datetime import datetime, date
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
DOSSIER_DIR = THUNDERBIRD_ROOT / "dossiers"
MISSION_BOARD_PATH = THUNDERBIRD_ROOT / "OpsCenter" / "mission_board.json"
VENDOR_CONTRACTS_PATH = THUNDERBIRD_ROOT / "config" / "vendor_contracts.json"
INSURANCE_POLICIES_PATH = THUNDERBIRD_ROOT / "config" / "insurance_policies.json"
COMMISSION_STATE_DIR = THUNDERBIRD_ROOT / "OpsCenter" / "state"
INTEL_DIR = THUNDERBIRD_ROOT / "intel"

REENGAGEMENT_THRESHOLD_DAYS = 548  # ~18 months
COMPETITOR_INTEL_STALE_DAYS = 7
RECONCILIATION_GRACE_DAYS = 5

_MONTH_NAME_RE = (
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)"
)
_QUARTER_OF_MONTH = {m: (m - 1) // 3 + 1 for m in range(1, 13)}


def _today(now):
    if now is None:
        return date.today()
    if isinstance(now, datetime):
        return now.date()
    return now


def _load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _parse_date(value):
    """Accepts ISO (YYYY-MM-DD) or 'Month D, YYYY' strings."""
    if not value:
        return None
    value = value.strip()
    try:
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        pass
    m = re.search(_MONTH_NAME_RE + r"\s+(\d{1,2}),?\s+(\d{4})", value)
    if m:
        try:
            return datetime.strptime(
                f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y"
            ).date()
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# 1. Vendor contract expirations
# ---------------------------------------------------------------------------
def scan_vendor_contract_expirations(
    registry_path=VENDOR_CONTRACTS_PATH, now=None, warn_days=45
):
    """Vendor/supplier agreements nearing expiration.

    Reads config/vendor_contracts.json (mirrors Drive/Thunderbird_Commercial_Ops
    once synced). Empty/missing registry -> no findings, not an alarm.
    """
    today = _today(now)
    registry = _load_json(registry_path)
    contracts = registry.get("contracts", []) if isinstance(registry, dict) else []

    results = []
    for c in contracts:
        expires = _parse_date(c.get("expires"))
        if not expires:
            continue
        days_out = (expires - today).days
        if days_out <= warn_days:
            results.append(
                {
                    "type": "vendor_contract_expiration",
                    "vendor": c.get("vendor", "unknown"),
                    "contract_type": c.get("contract_type", "unknown"),
                    "expires": expires.isoformat(),
                    "days_out": days_out,
                    "priority": "HIGH" if days_out <= 14 else "MEDIUM",
                }
            )
    return results


# ---------------------------------------------------------------------------
# 2. Insurance policy renewals
# ---------------------------------------------------------------------------
def scan_insurance_policy_renewals(
    registry_path=INSURANCE_POLICIES_PATH, now=None, warn_days=45
):
    """Insurance/underwriter policy renewals nearing expiration.

    Reads config/insurance_policies.json (mirrors Drive/Thunderbird_Shield_Logistics
    once synced). Empty/missing registry -> no findings, not an alarm.
    """
    today = _today(now)
    registry = _load_json(registry_path)
    policies = registry.get("policies", []) if isinstance(registry, dict) else []

    results = []
    for p in policies:
        expires = _parse_date(p.get("expires"))
        if not expires:
            continue
        days_out = (expires - today).days
        if days_out <= warn_days:
            results.append(
                {
                    "type": "insurance_policy_renewal",
                    "policy": p.get("policy", "unknown"),
                    "carrier": p.get("carrier", "unknown"),
                    "expires": expires.isoformat(),
                    "days_out": days_out,
                    "priority": "HIGH" if days_out <= 14 else "MEDIUM",
                }
            )
    return results


# ---------------------------------------------------------------------------
# 3. Commission reconciliation cycle (1st-of-month marker)
# ---------------------------------------------------------------------------
_RECON_FILENAME_RE = re.compile(r"commission_reconciliation_(\d{8})")


def scan_commission_reconciliation_cycle(
    state_dir=COMMISSION_STATE_DIR, now=None, grace_days=RECONCILIATION_GRACE_DAYS
):
    """Flags when the monthly commission reconciliation hasn't been filed
    within `grace_days` of the 1st of the current month."""
    today = _today(now)
    if today.day <= grace_days:
        return []  # still inside the grace window, nothing to flag yet

    month_start = today.replace(day=1)
    filed_this_month = False

    state_dir = Path(state_dir)
    if state_dir.is_dir():
        for f in state_dir.iterdir():
            m = _RECON_FILENAME_RE.search(f.name)
            if not m:
                continue
            try:
                filed_date = datetime.strptime(m.group(1), "%Y%m%d").date()
            except ValueError:
                continue
            if filed_date >= month_start:
                filed_this_month = True
                break

    if filed_this_month:
        return []

    days_overdue = (today - month_start).days - grace_days
    return [
        {
            "type": "commission_reconciliation_cycle",
            "issue": f"No commission reconciliation filed for {month_start.strftime('%B %Y')} "
            f"({days_overdue}d past the {grace_days}-day grace window)",
            "period": month_start.strftime("%Y-%m"),
            "days_overdue": days_overdue,
            "priority": "HIGH" if days_overdue > grace_days else "MEDIUM",
        }
    ]


# ---------------------------------------------------------------------------
# 4. Client re-engagement windows
# ---------------------------------------------------------------------------
_DEPARTURE_PATTERNS = [
    re.compile(r"departure:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    re.compile(r"Embarkation:?\s*" + _MONTH_NAME_RE + r"\s+(\d{1,2}),?\s+(\d{4})"),
    re.compile(r"EMB[:\-]?\s*(\d{4}-\d{2}-\d{2})"),
]


def _client_key_from_filename(stem):
    key = re.sub(r"^DOSSIER_", "", stem)
    key = re.split(r"_\d{4}$|_[A-Za-z]{3,9}\d{4}$", key)[0]
    return key


def _extract_departures(content):
    dates = set()
    for pat in _DEPARTURE_PATTERNS:
        for m in pat.finditer(content):
            groups = m.groups()
            if len(groups) == 1:
                d = _parse_date(groups[0])
            else:
                d = _parse_date(" ".join(g for g in groups if g))
            if d:
                dates.add(d)
    return dates


def _quarter_label(d):
    q = _QUARTER_OF_MONTH[d.month]
    return f"Q{q} {d.year}"


def _next_occurrence_of_quarter(quarter, from_date):
    year = from_date.year
    q_start_month = (quarter - 1) * 3 + 1
    candidate = date(year, q_start_month, 1)
    if candidate < from_date:
        candidate = date(year + 1, q_start_month, 1)
    return candidate


def scan_client_reengagement_windows(
    dossier_dir=DOSSIER_DIR,
    mission_board_path=MISSION_BOARD_PATH,
    now=None,
    threshold_days=REENGAGEMENT_THRESHOLD_DAYS,
):
    """Flags clients whose most recent completed voyage is >= threshold_days
    ago with no active follow-on booking, and annotates a predicted rebook
    window using the client's (or the repeat-client cohort's) historical
    quarter distribution — "similar clients rebook in Q3" style signal.
    """
    today = _today(now)
    dossier_dir = Path(dossier_dir)

    client_departures = {}
    if dossier_dir.is_dir():
        for f in dossier_dir.glob("*.md"):
            try:
                content = f.read_text()
            except OSError:
                continue
            client = _client_key_from_filename(f.stem)
            dates = _extract_departures(content)
            if dates:
                client_departures.setdefault(client, set()).update(dates)

    # Cohort quarter pattern across repeat clients (>=2 historical departures)
    quarter_counts = {}
    for client, dates in client_departures.items():
        if len(dates) >= 2:
            for d in dates:
                quarter_counts[_QUARTER_OF_MONTH[d.month]] = (
                    quarter_counts.get(_QUARTER_OF_MONTH[d.month], 0) + 1
                )
    cohort_quarter = max(quarter_counts, key=quarter_counts.get) if quarter_counts else None
    cohort_repeat_clients = sum(1 for d in client_departures.values() if len(d) >= 2)

    mission_board = _load_json(mission_board_path)
    active_titles = " ".join(
        m.get("title", "") for m in mission_board.get("missions", [])
        if m.get("status") in ("active", "in_progress")
    ).lower()

    results = []
    for client, dates in client_departures.items():
        past_dates = [d for d in dates if d <= today]
        if not past_dates:
            continue
        last_departure = max(past_dates)
        days_since = (today - last_departure).days
        if days_since < threshold_days:
            continue
        if client.lower() in active_titles:
            continue  # already has a follow-on mission in flight

        predicted_quarter = cohort_quarter or _QUARTER_OF_MONTH[last_departure.month]
        predicted_window_start = _next_occurrence_of_quarter(predicted_quarter, today)

        finding = {
            "type": "client_reengagement_window",
            "client": client,
            "last_departure": last_departure.isoformat(),
            "days_since_last_departure": days_since,
            "predicted_rebook_window": f"Q{predicted_quarter} {predicted_window_start.year}",
            "priority": "HIGH" if days_since >= threshold_days * 1.5 else "MEDIUM",
        }
        if cohort_quarter and cohort_repeat_clients >= 2:
            finding["cohort_signal"] = (
                f"{cohort_repeat_clients} repeat-booking clients cluster in Q{cohort_quarter} — "
                f"{client} is overdue against that pattern"
            )
        results.append(finding)

    return results


# ---------------------------------------------------------------------------
# 5. Competitor intelligence freshness
# ---------------------------------------------------------------------------
def scan_competitor_intel_freshness(
    intel_dir=INTEL_DIR, now=None, stale_days=COMPETITOR_INTEL_STALE_DAYS
):
    """Flags when the most recent competitor-intel artifact is stale."""
    today_dt = now if isinstance(now, datetime) else datetime.combine(_today(now), datetime.min.time())
    intel_dir = Path(intel_dir)
    if not intel_dir.is_dir():
        return []

    candidates = [
        f for f in intel_dir.rglob("*")
        if f.is_file() and "competitor" in f.name.lower()
    ]
    if not candidates:
        return []

    newest = max(candidates, key=lambda f: f.stat().st_mtime)
    mtime = datetime.fromtimestamp(newest.stat().st_mtime)
    days_stale = (today_dt - mtime).days

    if days_stale <= stale_days:
        return []

    return [
        {
            "type": "competitor_intel_freshness",
            "issue": f"Most recent competitor intel ({newest.name}) is {days_stale}d old",
            "file": str(newest),
            "days_stale": days_stale,
            "priority": "HIGH" if days_stale > 21 else "MEDIUM",
        }
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_all(now=None):
    """Run all 5 Phase 2 predictive signals, return dict keyed like Phase 1's
    scan_results["scans"] so it can be merged directly."""
    return {
        "vendor_contract_expirations": scan_vendor_contract_expirations(now=now),
        "insurance_policy_renewals": scan_insurance_policy_renewals(now=now),
        "commission_reconciliation_cycle": scan_commission_reconciliation_cycle(now=now),
        "client_reengagement_windows": scan_client_reengagement_windows(now=now),
        "competitor_intel_freshness": scan_competitor_intel_freshness(now=now),
    }


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2))
