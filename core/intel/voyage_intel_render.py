#!/usr/bin/env python3
"""
Voyage Intelligence Digest — shared collectors + renderer.

Aggregates 5 categories from EXISTING data sources only:
  1. New itineraries released     -> intel/cruise_intel/cruise_line_intel_*.json
  2. Price changes (tracked)      -> core/travel/data/fare_watches.json + fare_watch_history.json
  3. Competitor offerings         -> local competitor-intel cache (none as of build; reported STALE, never fabricated)
  4. Port condition alerts        -> OpsCenter/logs/weather_disruption.jsonl
  5. Partner/commission updates   -> intel/cruise_intel/cruise_line_intel_*.json (same file as #1, different keyword bucket)

Hard rule (Negative-Space): this module NEVER triggers a scan (no Perplexity/Serper/
scrape calls). It only reads what the existing scanners already wrote and reports
freshness honestly. A missing or stale source is a flagged status, not a blank
section — a silent zero is a failure mode, not "all clear."
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path("/home/john/Thunderbird")
DOSSIERS_DIR = ROOT / "dossiers"
FARE_WATCHES = ROOT / "core" / "travel" / "data" / "fare_watches.json"
FARE_HISTORY = ROOT / "core" / "travel" / "data" / "fare_watch_history.json"
WEATHER_LOG = ROOT / "OpsCenter" / "logs" / "weather_disruption.jsonl"
CRUISE_INTEL_DIR = ROOT / "intel" / "cruise_intel"
COMPETITOR_INTEL_DIR = ROOT / "output" / "competitive_intel"
VOYAGE_INTEL_DIR = ROOT / "OpsCenter" / "state" / "voyage_intel"

MARKER_START = "<!-- VOYAGE_INTEL_START -->"
MARKER_END = "<!-- VOYAGE_INTEL_END -->"

PRICE_DROP_HIGH_PCT = 15.0        # spec: HIGH if price drop >15%
WEATHER_FRESH_HOURS = 24.0
CRUISE_INTEL_FRESH_DAYS = 35.0    # cruise_line_intel_sweep runs monthly by design

ITINERARY_KEYWORDS = re.compile(
    r"itinerary|deployment|new ship|fleet|redeploy|cancell?ation|schedule change|new route|new voyage",
    re.IGNORECASE,
)
PARTNER_KEYWORDS = re.compile(
    r"commission|advisor|agent|co-?op|fam trip|incentive|override|promo(?:tion)?",
    re.IGNORECASE,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        t = ts.rstrip("Z")
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _age_hours(ts: str | None) -> float | None:
    dt = _parse_ts(ts)
    if dt is None:
        return None
    return (_now() - dt).total_seconds() / 3600.0


def _empty_result(source_file: Path, status: str, note: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "confidence": "none",
        "source_file": str(source_file),
        "age_hours": None,
        "data": [],
        "high_count": 0,
        "note": note or f"{status}: {source_file.name} not found",
    }


# ---------------------------------------------------------------------------
# Active client roster (for HIGH-severity matching — never fabricated data,
# just cross-reference against what's already on file)
# ---------------------------------------------------------------------------

def load_active_clients() -> list[dict[str, Any]]:
    clients: list[dict[str, Any]] = []
    if not DOSSIERS_DIR.exists():
        return clients
    for fp in DOSSIERS_DIR.glob("*.md"):
        if fp.name.upper() == "CLAUDE.MD":
            continue
        try:
            text = fp.read_text(errors="ignore")
        except Exception:
            continue
        if not text.startswith("---"):
            continue
        try:
            end = text.index("---", 3)
            fm = yaml.safe_load(text[3:end]) or {}
        except Exception:
            continue
        if not isinstance(fm, dict):
            continue
        if fm.get("status") not in ("active", None):
            continue
        ship = fm.get("ship")
        if not ship:
            continue
        clients.append(
            {
                "client": fm.get("full_name") or fm.get("client"),
                "ship": str(ship),
                "cruise_line": str(fm.get("cruise_line") or ""),
                "voyage": fm.get("voyage"),
                "departure": fm.get("departure"),
                "booking": fm.get("booking"),
                "dossier": fp.name,
            }
        )
    return clients


# ---------------------------------------------------------------------------
# Collector 1 — Price changes on tracked routes
# ---------------------------------------------------------------------------

def collect_price_changes(active_clients: list[dict] | None = None) -> dict[str, Any]:
    active_clients = active_clients or []
    if not FARE_WATCHES.exists():
        return _empty_result(FARE_WATCHES, "MISSING")

    try:
        watches = json.loads(FARE_WATCHES.read_text())
    except Exception as e:
        return {**_empty_result(FARE_WATCHES, "ERROR"), "note": f"parse error: {e}"}

    if not isinstance(watches, dict):
        return {**_empty_result(FARE_WATCHES, "ERROR"), "note": "unexpected schema (expected dict of watches)"}

    trends: dict[str, Any] = {}
    trend_age_hours = None
    if FARE_HISTORY.exists():
        try:
            hist = json.loads(FARE_HISTORY.read_text())
            trends = hist.get("_trends", {}) or {}
            scans = hist.get("scans", []) or []
            if scans:
                trend_age_hours = _age_hours(scans[-1].get("scanned_at"))
        except Exception:
            pass

    active_ship_names = {c["ship"].lower() for c in active_clients if c.get("ship")}

    changes = []
    for wid, w in watches.items():
        if not isinstance(w, dict) or not w.get("active", True):
            continue
        baseline = w.get("baseline_price_pp")
        current = w.get("current_price_pp")
        if not baseline or not current:
            continue
        pct = (current - baseline) / baseline * 100.0

        prices = (trends.get(wid) or {}).get("prices") or []
        delta_recent_pct = None
        if len(prices) >= 2 and prices[-2]:
            delta_recent_pct = (prices[-1] - prices[-2]) / prices[-2] * 100.0

        route = (w.get("route") or "").lower()
        label = (w.get("label") or "").lower()
        matches_client = any(name in route or name in label for name in active_ship_names)

        drop_pct = min(pct, delta_recent_pct if delta_recent_pct is not None else 0.0)
        if drop_pct <= -PRICE_DROP_HIGH_PCT:
            severity = "HIGH" if matches_client else "MEDIUM"
        elif abs(pct) >= 5.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        changes.append(
            {
                "watch_id": wid,
                "label": w.get("label"),
                "route": w.get("route"),
                "provider": w.get("provider"),
                "baseline_price_pp": baseline,
                "current_price_pp": current,
                "pct_change_vs_baseline": round(pct, 1),
                "pct_change_recent_scan": round(delta_recent_pct, 1) if delta_recent_pct is not None else None,
                "matches_active_client": matches_client,
                "severity": severity,
            }
        )

    changes.sort(key=lambda c: c["pct_change_vs_baseline"])
    high = [c for c in changes if c["severity"] == "HIGH"]
    status = "OK" if (trend_age_hours is None or trend_age_hours <= 48) else "STALE"
    return {
        "status": status,
        "confidence": "high" if trends else "medium",
        "source_file": str(FARE_WATCHES),
        "age_hours": trend_age_hours,
        "data": changes,
        "high_count": len(high),
        "note": "" if status == "OK" else f"last fare scan {trend_age_hours:.0f}h ago",
    }


# ---------------------------------------------------------------------------
# Collector 4 — Port condition alerts (weather / strikes / disruption)
# ---------------------------------------------------------------------------

def collect_port_alerts() -> dict[str, Any]:
    if not WEATHER_LOG.exists():
        return _empty_result(WEATHER_LOG, "MISSING")

    try:
        lines = [l for l in WEATHER_LOG.read_text().strip().splitlines() if l.strip()]
    except Exception as e:
        return {**_empty_result(WEATHER_LOG, "ERROR"), "note": f"read error: {e}"}

    if not lines:
        return _empty_result(WEATHER_LOG, "EMPTY", "log file present but no entries")

    try:
        last = json.loads(lines[-1])
    except Exception as e:
        return {**_empty_result(WEATHER_LOG, "ERROR"), "note": f"parse error: {e}"}

    age = _age_hours(last.get("ts"))
    alerts = last.get("detail", []) or []
    fresh = age is not None and age <= WEATHER_FRESH_HOURS
    status = "OK" if fresh else "STALE"

    items = [{**a, "severity": "HIGH"} for a in alerts] if fresh else []
    note = "" if fresh else (
        f"last scan {age:.0f}h ago (>{WEATHER_FRESH_HOURS:.0f}h stale window) — "
        f"disruption status unknown, not asserted clear" if age is not None else "no timestamp on last scan"
    )

    return {
        "status": status,
        "confidence": "high" if fresh else "low",
        "source_file": str(WEATHER_LOG),
        "age_hours": age,
        "data": items,
        "high_count": len(items),
        "note": note,
    }


# ---------------------------------------------------------------------------
# Collectors 3/5 support — cruise_line_intel_*.json (shared source file)
# ---------------------------------------------------------------------------

def _latest_cruise_line_intel() -> Path | None:
    if not CRUISE_INTEL_DIR.exists():
        return None
    files = sorted(CRUISE_INTEL_DIR.glob("cruise_line_intel_*.json"))
    return files[-1] if files else None


def _bucket_cruise_line_intel(keyword_re: re.Pattern, active_clients: list[dict]) -> dict[str, Any]:
    fp = _latest_cruise_line_intel()
    if fp is None:
        return _empty_result(CRUISE_INTEL_DIR / "cruise_line_intel_*.json", "MISSING")

    try:
        payload = json.loads(fp.read_text())
    except Exception as e:
        return {**_empty_result(fp, "ERROR"), "note": f"parse error: {e}"}

    file_date = payload.get("date")
    age_hours = None
    if file_date:
        age_hours = _age_hours(f"{file_date}T00:00:00+00:00")

    lines = payload.get("lines", {}) or {}
    active_line_names = {c["cruise_line"].lower() for c in active_clients if c.get("cruise_line")}

    fresh = age_hours is None or age_hours <= CRUISE_INTEL_FRESH_DAYS * 24
    items = []
    if fresh and isinstance(lines, dict):
        for line_name, payload_for_line in lines.items():
            summary = ""
            if isinstance(payload_for_line, dict):
                summary = payload_for_line.get("summary", "") or ""
            elif isinstance(payload_for_line, str):
                summary = payload_for_line
            if not summary or summary.startswith("[WARN]") or summary.startswith("[ERROR]"):
                continue
            matched_sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", summary)
                if s.strip() and keyword_re.search(s)
            ]
            if not matched_sentences:
                continue
            matches_client = line_name.lower() in active_line_names
            items.append(
                {
                    "cruise_line": line_name,
                    "summary": " ".join(matched_sentences)[:500],
                    "matches_active_client": matches_client,
                    "severity": "HIGH" if matches_client else "LOW",
                }
            )

    status = "OK" if fresh else "STALE"
    high = [i for i in items if i["severity"] == "HIGH"]
    return {
        "status": status,
        "confidence": "medium" if fresh else "low",
        "source_file": str(fp),
        "age_hours": age_hours,
        "data": items,
        "high_count": len(high),
        "note": "" if fresh else f"last cruise-line intel sweep {age_hours / 24:.0f}d ago (>{CRUISE_INTEL_FRESH_DAYS:.0f}d window) — treated as informational only",
    }


def collect_new_itineraries(active_clients: list[dict] | None = None) -> dict[str, Any]:
    return _bucket_cruise_line_intel(ITINERARY_KEYWORDS, active_clients or [])


def collect_partner_updates(active_clients: list[dict] | None = None) -> dict[str, Any]:
    return _bucket_cruise_line_intel(PARTNER_KEYWORDS, active_clients or [])


# ---------------------------------------------------------------------------
# Collector 3 — Competitor offerings
# NOTE: as of this build there is no local cache of travel-agency competitor
# scrapes (thunderbird_competitive_surveillance.py writes to Google Sheets +
# persona memory only, not a local file). We check for one and report its
# absence honestly rather than fabricate a "clear" result.
# ---------------------------------------------------------------------------

def collect_competitor_offerings() -> dict[str, Any]:
    if not COMPETITOR_INTEL_DIR.exists():
        return _empty_result(
            COMPETITOR_INTEL_DIR,
            "MISSING",
            "no local competitor-intel cache directory — thunderbird_competitive_surveillance.py "
            "writes to Google Sheets/persona memory only; nothing to read locally",
        )

    files = sorted(COMPETITOR_INTEL_DIR.glob("*.json"))
    if not files:
        return _empty_result(COMPETITOR_INTEL_DIR, "EMPTY", "competitor-intel directory exists but has no scan output")

    fp = files[-1]
    try:
        payload = json.loads(fp.read_text())
    except Exception as e:
        return {**_empty_result(fp, "ERROR"), "note": f"parse error: {e}"}

    ts = payload.get("timestamp") or payload.get("date")
    age_hours = _age_hours(ts) if ts else None
    fresh = age_hours is not None and age_hours <= 7 * 24
    status = "OK" if fresh else "STALE"
    data = payload.get("competitors", payload.get("data", [])) if fresh else []
    return {
        "status": status,
        "confidence": "medium" if fresh else "low",
        "source_file": str(fp),
        "age_hours": age_hours,
        "data": data,
        "high_count": 0,  # competitor moves are informational only — never auto-HIGH
        "note": "" if fresh else (f"last competitor scan {age_hours / 24:.0f}d ago (>7d window)" if age_hours else "no timestamp on scan"),
    }


# ---------------------------------------------------------------------------
# Digest assembly
# ---------------------------------------------------------------------------

CATEGORY_ORDER = [
    ("new_itineraries", "New Itineraries Released"),
    ("price_changes", "Price Changes — Tracked Routes"),
    ("competitor_offerings", "Competitor Offerings"),
    ("port_alerts", "Port Condition Alerts"),
    ("partner_updates", "Partner / Commission Updates"),
]


def build_digest(run_date: str | None = None) -> dict[str, Any]:
    run_date = run_date or _now().strftime("%Y-%m-%d")
    active_clients = load_active_clients()

    categories = {
        "new_itineraries": collect_new_itineraries(active_clients),
        "price_changes": collect_price_changes(active_clients),
        "competitor_offerings": collect_competitor_offerings(),
        "port_alerts": collect_port_alerts(),
        "partner_updates": collect_partner_updates(active_clients),
    }

    total_high = sum(c.get("high_count", 0) for c in categories.values())
    stale_categories = [k for k, c in categories.items() if c.get("status") in ("STALE", "MISSING", "EMPTY", "ERROR")]

    return {
        "date": run_date,
        "generated_at": _now().isoformat(timespec="seconds"),
        "active_clients_checked": len(active_clients),
        "categories": categories,
        "total_high_count": total_high,
        "stale_categories": stale_categories,
        "overall_status": "HIGH_ALERT" if total_high else ("PARTIAL_DATA" if stale_categories else "CLEAR"),
    }


# ---------------------------------------------------------------------------
# Markdown rendering (single shared renderer — called from both the digest
# CLI and morning_brief_engine.py so there is exactly one rendering path)
# ---------------------------------------------------------------------------

def render_markdown(digest: dict[str, Any]) -> str:
    lines = [MARKER_START]
    lines.append(f"### 📡 VOYAGE INTELLIGENCE DIGEST — {digest['date']}")
    lines.append(
        f"*Generated {digest['generated_at']} · {digest['active_clients_checked']} active client(s) checked "
        f"vs profile · overall: {digest['overall_status']}*\n"
    )

    cats = digest["categories"]
    for key, title in CATEGORY_ORDER:
        c = cats.get(key, {})
        status = c.get("status", "UNKNOWN")
        age = c.get("age_hours")
        age_str = f"{age:.0f}h" if isinstance(age, (int, float)) else "n/a"
        icon = {"OK": "✅", "STALE": "🟡", "MISSING": "⚪", "EMPTY": "⚪", "ERROR": "🔴"}.get(status, "⚪")

        lines.append(f"**{icon} {title}** — {status} (age: {age_str})")
        data = c.get("data", [])
        if not data:
            note = c.get("note") or "no items"
            lines.append(f"  _{note}_")
        else:
            for item in data[:8]:
                sev = item.get("severity", "LOW")
                sev_icon = "🔴" if sev == "HIGH" else ("🟡" if sev == "MEDIUM" else "⚪")
                if key == "price_changes":
                    lines.append(
                        f"  {sev_icon} {item.get('label') or item.get('watch_id')}: "
                        f"${item.get('current_price_pp'):,.0f}pp ({item.get('pct_change_vs_baseline')}% vs baseline)"
                        + (" — MATCHES ACTIVE CLIENT" if item.get("matches_active_client") else "")
                    )
                elif key == "port_alerts":
                    lines.append(f"  {sev_icon} {item.get('destination', item.get('client', 'alert'))}: {item.get('note', item)}")
                else:
                    lines.append(
                        f"  {sev_icon} {item.get('cruise_line', item.get('name', ''))}: "
                        f"{str(item.get('summary', item))[:200]}"
                    )
        lines.append("")

    lines.append(MARKER_END)
    return "\n".join(lines)


def inject_into_brief(brief_path: Path, digest: dict[str, Any]) -> None:
    """Idempotent, marker-delimited insert/replace into hale_brief.md."""
    block = render_markdown(digest)
    if not brief_path.exists():
        brief_path.write_text(block + "\n", encoding="utf-8")
        return

    text = brief_path.read_text(encoding="utf-8")
    if MARKER_START in text and MARKER_END in text:
        start = text.index(MARKER_START)
        end = text.index(MARKER_END) + len(MARKER_END)
        new_text = text[:start] + block + text[end:]
    elif "### 0. OVERNIGHT OPS" in text:
        anchor = text.index("### 0. OVERNIGHT OPS")
        new_text = text[:anchor] + block + "\n\n---\n\n" + text[anchor:]
    else:
        new_text = text.rstrip() + "\n\n---\n\n" + block + "\n"

    brief_path.write_text(new_text, encoding="utf-8")


def latest_digest_json() -> dict[str, Any] | None:
    """Read the most recent Voyage_Intel_*.json (used by morning_brief_engine on regen)."""
    if not VOYAGE_INTEL_DIR.exists():
        return None
    files = sorted(VOYAGE_INTEL_DIR.glob("Voyage_Intel_*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text())
    except Exception:
        return None
