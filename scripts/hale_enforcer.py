#!/usr/bin/env python3
"""
hale_enforcer.py — Hale's continuous prod-engine.

Eliminates the Commander's need to manually prod the Wing by running five
inspection loops every OODA cycle. READ-ONLY: never mutates client data.

LOOPS:
  1. readiness()   — CI razor-sharp status (SORTS/DRRS equiv)
  2. taskings()    — Past-due / due-soon alerts & missions (TMT equiv)
  3. push_to_limits() — Where the Wing is operating at X-minus (Stan/Eval equiv)
  4. compliance()  — WF-17 chain + SO adherence signals (IG inspect equiv)
  5. complaints()  — Staff dissents + client complaint signals (IG resolve equiv)

Each loop returns a dict with:
  - "mode":     "LIVE" | "PARTIAL" | "STUB"
  - "source":   what data was read (machine-readable, not prose)
  - "findings": list of finding dicts

run_all() → writes OpsCenter/hale_enforcer_report.json + prints ⚡ summary.

Author: Sterling (A7) · 2026-07-02
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path("/home/john/Thunderbird")
CI_REGISTRY_PATH = ROOT / "config" / "ci_registry.json"
CI_DASHBOARD_PATH = ROOT / "output" / "CI_DASHBOARD.md"
MISSION_BOARD_PATH = ROOT / "OpsCenter" / "mission_board.json"
HALE_STATE_PATH = ROOT / "hale_state.json"
DRAFT_METADATA_PATH = ROOT / "OpsCenter" / "draft_metadata.json"
STAFF_COMMENTS_FEED = ROOT / "OpsCenter" / "staff_comments_live.jsonl"
STAFF_COMMENTS_CURSOR = ROOT / "OpsCenter" / ".staff_comments_feed_cursor.json"
PROTECTIONS_SENTINEL = ROOT / ".protections_lifted"
REPORT_PATH = ROOT / "OpsCenter" / "hale_enforcer_report.json"

PROTECTED_FILES = [
    "OpsCenter/run_commander_directive_sweep.py",
    "OpsCenter/dispatch_and_email.py",
    "OpsCenter/email_task_ingest.py",
    "core/email/thunderbird_commander_inbox.py",
    "OpsCenter/relay_send.py",
    "core/relay/wing_relay.py",
]

# Missions in these statuses are terminal — do not flag as open
TERMINAL_STATUSES = {
    "completed", "archived", "closed", "killed", "done", "cancelled",
    "complete", "cancel", "COMPLETED", "ARCHIVED", "CLOSED", "KILLED",
}

NOW = datetime.now(timezone.utc)


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> Any | None:
    """Return parsed JSON or None on failure (no raises)."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _age_hours(iso: str) -> float:
    """Hours since an ISO-8601 timestamp."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (NOW - dt).total_seconds() / 3600.0
    except Exception:
        return float("inf")


def _days_until(date_str: str) -> float | None:
    """Days until a YYYY-MM-DD date string. Negative = past due."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (target - NOW).total_seconds() / 86400.0
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 1 — readiness()  (LIVE / PARTIAL)
# Sources:
#   - output/CI_DASHBOARD.md  (last persisted sweep — read-only, real statuses)
#   - config/ci_registry.json (last_verified age vs currency_window_hours)
# ci_sweep.py currently crashes (malformed registry entry #48) — that is itself
# a finding.  We read the persisted dashboard instead of re-running the sweep.
# Mode: PARTIAL — dashboard may be stale; ci_sweep down.
# ─────────────────────────────────────────────────────────────────────────────

def readiness() -> dict:
    """
    Loop 1 — CI Razor-Sharp Status (SORTS/DRRS equiv).

    MODE: PARTIAL
    - LIVE source: CI_DASHBOARD.md parsed for last-known status per skill.
    - LIVE source: ci_registry.json last_verified age vs currency_window_hours.
    - FINDING: ci_sweep.py is currently broken (malformed registry entry).
      Real-time probing is unavailable until the registry defect is fixed.
    """
    findings: list[dict] = []
    source_parts: list[str] = []

    # ── read persisted CI dashboard ──────────────────────────────────────────
    dashboard_ts: str | None = None
    dashboard_age_h: float | None = None
    dashboard_statuses: dict[str, str] = {}  # name → status emoji+text

    if CI_DASHBOARD_PATH.exists():
        content = CI_DASHBOARD_PATH.read_text()
        # Extract generation timestamp from first heading
        ts_match = re.search(r"CI DASHBOARD — ([\d\-T:\.+]+)", content)
        if ts_match:
            dashboard_ts = ts_match.group(1)
            dashboard_age_h = _age_hours(dashboard_ts)

        # Parse table rows: | Skill Name | Status | Probe | ...
        for row in content.splitlines():
            cells = [c.strip() for c in row.split("|")]
            if len(cells) >= 4 and cells[1] not in ("Skill", "---", ""):
                name = cells[1]
                status_text = cells[2]
                if status_text and "RAZOR" in status_text.upper() or any(
                    tok in status_text for tok in ["DULL", "RED", "REPLACE", "🟡", "🔴", "🔁", "🟢"]
                ):
                    dashboard_statuses[name] = status_text

        source_parts.append(
            f"CI_DASHBOARD.md (ts={dashboard_ts or 'unknown'}, "
            f"age={round(dashboard_age_h or 0, 1)}h)"
        )

        # Flag dashboard staleness itself
        if dashboard_age_h is not None and dashboard_age_h > 12:
            findings.append({
                "id": "CI-DASHBOARD-STALE",
                "severity": "WARN",
                "title": "CI dashboard is stale",
                "detail": f"Last sweep: {dashboard_ts} ({round(dashboard_age_h,1)}h ago). "
                          "Real-time status unknown until ci_sweep runs.",
                "action": "Run ci_sweep.py once registry defect is fixed.",
            })

        # Report non-sharp skills from dashboard
        for name, status in dashboard_statuses.items():
            if "RAZOR_SHARP" not in status.upper() and "🟢" not in status:
                findings.append({
                    "id": f"CI-DEGRADED-{name.upper()[:30].replace(' ','-')}",
                    "severity": "RED" if ("RED" in status or "🔴" in status or "REPLACE" in status or "🔁" in status) else "WARN",
                    "title": f"CI skill degraded: {name}",
                    "detail": f"Last known status: {status.strip()}",
                    "action": "Check skill registry + probe; page Whetstone if REPLACE.",
                    "source": "CI_DASHBOARD.md (last-known, may be stale)",
                })
    else:
        findings.append({
            "id": "CI-DASHBOARD-MISSING",
            "severity": "RED",
            "title": "CI_DASHBOARD.md missing — no persisted sweep available",
            "detail": str(CI_DASHBOARD_PATH),
            "action": "Run ci_sweep.py to regenerate.",
        })
        source_parts.append("CI_DASHBOARD.md MISSING")

    # ── registry staleness check (always-live) ───────────────────────────────
    registry_data = _load_json(CI_REGISTRY_PATH)
    if registry_data:
        skills = registry_data.get("skills", [])
        required_fields = [
            "id", "name", "ci_tool", "health_probe",
            "currency_window_hours", "reeval_cadence_days", "fallback", "keeper",
        ]
        malformed = [s for s in skills if any(s.get(f) is None for f in required_fields)]
        if malformed:
            findings.append({
                "id": "CI-REGISTRY-MALFORMED",
                "severity": "RED",
                "title": f"ci_sweep broken: {len(malformed)} malformed registry entr{'y' if len(malformed)==1 else 'ies'}",
                "detail": f"Missing required fields. Blocks all real-time probing. "
                          f"Entry IDs: {[s.get('id','?') for s in malformed]}",
                "action": "Fix malformed registry entry so ci_sweep.py can run.",
            })

        clean = [s for s in skills if all(s.get(f) is not None for f in required_fields)]
        stale_skills = []
        for s in clean:
            lv = s.get("last_verified")
            window_h = s.get("currency_window_hours", 24)
            if lv:
                age_h = _age_hours(lv)
                if age_h > window_h:
                    stale_skills.append({
                        "id": s["id"],
                        "name": s["name"],
                        "age_h": round(age_h, 1),
                        "window_h": window_h,
                        "last_verified": lv,
                    })

        if stale_skills:
            findings.append({
                "id": "CI-SKILLS-PAST-CURRENCY-WINDOW",
                "severity": "WARN",
                "title": f"{len(stale_skills)} CI skill(s) past last_verified currency window",
                "detail": stale_skills[:10],  # cap at 10
                "action": "Probe these skills or explain why delayed; update last_verified.",
            })

        source_parts.append(
            f"ci_registry.json ({len(clean)} clean entries, "
            f"{len(malformed)} malformed, {len(stale_skills)} past currency window)"
        )
    else:
        findings.append({
            "id": "CI-REGISTRY-UNREADABLE",
            "severity": "RED",
            "title": "ci_registry.json unreadable",
            "detail": str(CI_REGISTRY_PATH),
            "action": "Fix registry file.",
        })

    return {
        "loop": "readiness",
        "mode": "PARTIAL",
        "mode_note": (
            "PARTIAL: dashboard is last-persisted read (may be stale); "
            "ci_sweep.py is BROKEN (malformed registry entry) so real-time probing is unavailable. "
            "last_verified staleness check is LIVE."
        ),
        "source": "; ".join(source_parts) or "none",
        "findings_count": len(findings),
        "findings": findings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 2 — taskings()  (LIVE)
# Sources:
#   - hale_state.json  → deferred_alerts (trigger_date fields → real due dates)
#   - OpsCenter/mission_board.json → active P0/P1 missions (no due-date field;
#     staleness proxy used for missions with no recent update)
# ─────────────────────────────────────────────────────────────────────────────

def taskings() -> dict:
    """
    Loop 2 — Past-due / due-soon alerts & missions (TMT equiv).

    MODE: LIVE
    - deferred_alerts: trigger_date → real past-due / due-soon (≤7 days).
    - missions: no due-date field; staleness proxy (no update in >14 days) used.
      Labeled as proxy, not due-date logic.
    """
    findings: list[dict] = []
    source_parts: list[str] = []

    # ── deferred_alerts ──────────────────────────────────────────────────────
    hale_state = _load_json(HALE_STATE_PATH)
    if hale_state:
        alerts = hale_state.get("deferred_alerts", [])
        past_due = []
        due_soon = []
        for a in alerts:
            tdate = a.get("trigger_date")
            if not tdate:
                continue
            days = _days_until(tdate)
            if days is None:
                continue
            if days < 0:
                past_due.append({**a, "_days_overdue": round(-days, 1)})
            elif days <= 7:
                due_soon.append({**a, "_days_until": round(days, 1)})

        if past_due:
            findings.append({
                "id": "ALERTS-PAST-DUE",
                "severity": "RED",
                "title": f"{len(past_due)} deferred alert(s) past trigger date",
                "detail": [
                    {
                        "id": a["id"],
                        "priority": a.get("priority"),
                        "trigger_date": a.get("trigger_date"),
                        "days_overdue": a["_days_overdue"],
                        "message": a.get("message", "")[:120],
                    }
                    for a in sorted(past_due, key=lambda x: -x["_days_overdue"])
                ],
                "action": "Hale: action each overdue alert or re-date with commander justification.",
            })
        if due_soon:
            findings.append({
                "id": "ALERTS-DUE-SOON",
                "severity": "WARN",
                "title": f"{len(due_soon)} deferred alert(s) due within 7 days",
                "detail": [
                    {
                        "id": a["id"],
                        "priority": a.get("priority"),
                        "trigger_date": a.get("trigger_date"),
                        "days_until": a["_days_until"],
                        "message": a.get("message", "")[:120],
                    }
                    for a in sorted(due_soon, key=lambda x: x["_days_until"])
                ],
                "action": "Hale: pre-position for these triggers now.",
            })

        source_parts.append(
            f"hale_state.json deferred_alerts ({len(alerts)} total, "
            f"{len(past_due)} past-due, {len(due_soon)} due-soon≤7d)"
        )
    else:
        findings.append({
            "id": "HALE-STATE-UNREADABLE",
            "severity": "WARN",
            "title": "hale_state.json unreadable — deferred alerts unavailable",
            "action": "Fix hale_state.json.",
        })

    # ── mission board P0/P1 ──────────────────────────────────────────────────
    board = _load_json(MISSION_BOARD_PATH)
    if board:
        missions = board.get("missions", [])
        active = [
            m for m in missions
            if m.get("status", "").lower() not in TERMINAL_STATUSES
        ]
        p0 = [m for m in active if m.get("priority") == "P0"]
        p1 = [m for m in active if m.get("priority") == "P1"]

        # Staleness proxy: no update in >14 days (no due-date field exists)
        stale_p0 = []
        for m in p0:
            upd = m.get("updated_at") or m.get("created_at")
            if upd and _age_hours(upd) > 14 * 24:
                stale_p0.append({
                    "id": m["id"],
                    "title": m.get("title", "?")[:80],
                    "status": m.get("status"),
                    "age_days": round(_age_hours(upd) / 24, 1),
                })

        if stale_p0:
            findings.append({
                "id": "MISSIONS-P0-STALE",
                "severity": "WARN",
                "title": f"{len(stale_p0)} P0 mission(s) with no update in >14 days (staleness proxy — no due-date field)",
                "detail": sorted(stale_p0, key=lambda x: -x["age_days"])[:10],
                "action": "Hale: update, close, or kill stale P0 missions. Each unactioned P0 is wasted board space.",
                "mode_note": "PROXY: missions have no due-date; age of last update used as staleness signal.",
            })

        # Always surface count even if no stale
        findings.append({
            "id": "MISSIONS-OPEN-SUMMARY",
            "severity": "INFO",
            "title": f"Mission board: {len(p0)} P0 open, {len(p1)} P1 open ({len(active)} total non-terminal)",
            "detail": {
                "total_missions": len(missions),
                "active": len(active),
                "p0_open": len(p0),
                "p1_open": len(p1),
                "p0_stale_gt14d": len(stale_p0),
            },
            "action": "No action if board is current. Flag if counts are growing uncontrolled.",
        })

        source_parts.append(
            f"mission_board.json ({len(missions)} total, {len(active)} active, "
            f"{len(p0)} P0, {len(p1)} P1)"
        )
    else:
        findings.append({
            "id": "MISSION-BOARD-UNREADABLE",
            "severity": "WARN",
            "title": "mission_board.json unreadable",
            "action": "Fix mission_board.json.",
        })

    return {
        "loop": "taskings",
        "mode": "LIVE",
        "mode_note": (
            "LIVE: deferred_alerts use real trigger_date fields. "
            "Mission staleness is a 14-day-no-update PROXY — missions have no due-date field."
        ),
        "source": "; ".join(source_parts) or "none",
        "findings_count": len(findings),
        "findings": findings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 3 — push_to_limits()  (PARTIAL — dossier freshness LIVE; others STUB)
# Stan/Eval: where is the Wing at X-minus, authorized to go further?
# ─────────────────────────────────────────────────────────────────────────────

def push_to_limits() -> dict:
    """
    Loop 3 — Where is the Wing operating at X-minus? (Stan/Eval equiv)

    MODE: PARTIAL
    - LIVE: dossier freshness (core.ops.dossier_freshness.check_dossier_freshness)
    - LIVE: WF-17 idle drafts (draft_metadata.json age check)
    - STUB: un-actioned staff suggestions (no machine-readable source)
    - STUB: autonomy-band underuse (no metric source)

    Each "push" finding says: "You are authorized to go further — go."
    """
    findings: list[dict] = []
    source_parts: list[str] = []

    # ── LIVE: dossier freshness ───────────────────────────────────────────────
    try:
        sys.path.insert(0, str(ROOT))
        from core.ops.dossier_freshness import check_dossier_freshness
        stale_dossiers = check_dossier_freshness()
        source_parts.append("core.ops.dossier_freshness.check_dossier_freshness()")

        if stale_dossiers:
            findings.append({
                "id": "DOSSIERS-STALE",
                "severity": "WARN",
                "title": f"{len(stale_dossiers)} active client dossier(s) stale (depart within 60d, not updated in 14d)",
                "detail": [
                    {
                        "client": d.get("client") or d.get("name") or str(d)[:80],
                        "days_to_depart": d.get("days_to_depart"),
                        "age_days": d.get("age_days"),
                    }
                    for d in stale_dossiers[:8]
                ],
                "action": (
                    "AUTHORIZED — GO: Hale can update dossiers now without Commander gate. "
                    "Each stale dossier before embark is a client-experience failure."
                ),
            })
        else:
            findings.append({
                "id": "DOSSIERS-CURRENT",
                "severity": "INFO",
                "title": "All active dossiers current (none stale within 60-day departure window)",
                "detail": "check_dossier_freshness() returned 0 stale items.",
            })
    except Exception as e:
        findings.append({
            "id": "DOSSIER-FRESHNESS-ERROR",
            "severity": "WARN",
            "title": f"Could not run dossier freshness check: {e}",
            "action": "Investigate core.ops.dossier_freshness import.",
        })
        source_parts.append(f"dossier_freshness FAILED: {e}")

    # ── LIVE: idle WF-17 drafts (draft_metadata.json age) ────────────────────
    draft_meta = _load_json(DRAFT_METADATA_PATH)
    if draft_meta:
        client_drafts = {
            k: v for k, v in draft_meta.items()
            if isinstance(v, dict) and v.get("template_type") == "client"
        }
        idle_drafts = []
        for draft_id, v in client_drafts.items():
            created = v.get("created_at")
            if created:
                age_h = _age_hours(created)
                if age_h > 48:
                    idle_drafts.append({
                        "draft_id": draft_id,
                        "subject": v.get("subject", "?")[:80],
                        "to": v.get("to", "?"),
                        "created_at": created,
                        "age_h": round(age_h, 1),
                    })
        source_parts.append(
            f"draft_metadata.json ({len(client_drafts)} client drafts, "
            f"{len(idle_drafts)} idle >48h)"
        )
        if idle_drafts:
            findings.append({
                "id": "WF17-DRAFTS-IDLE",
                "severity": "WARN",
                "title": f"{len(idle_drafts)} WF-17 client draft(s) sitting idle >48h",
                "detail": sorted(idle_drafts, key=lambda x: -x["age_h"]),
                "action": (
                    "PUSH: Surface idle drafts to Commander NOW — Commander is the only authorized sender. "
                    "Every hour an idle draft sits, the window for a timely client touch narrows."
                ),
            })
    else:
        findings.append({
            "id": "DRAFT-METADATA-STUB",
            "severity": "INFO",
            "title": "draft_metadata.json missing or unreadable",
            "mode": "STUB",
        })

    # ── STUB: un-actioned staff suggestions ───────────────────────────────────
    findings.append({
        "id": "STAFF-SUGGESTIONS-UNACTIONED",
        "severity": "STUB",
        "title": "[STUB] Un-actioned staff suggestions — no machine-readable source",
        "detail": (
            "There is no structured output file tracking staff-suggestion → action taken. "
            "Hale tracks them in conversation context only."
        ),
        "action": (
            "PENDING SOURCE: Build staff_suggestions.jsonl (append on suggestion, "
            "mark closed on action). Wire here when live."
        ),
        "mode": "STUB",
    })

    # ── STUB: autonomy band underuse ──────────────────────────────────────────
    findings.append({
        "id": "AUTONOMY-BAND-UNDERUSE",
        "severity": "STUB",
        "title": "[STUB] Autonomy band underuse — no metric source",
        "detail": (
            "No metric currently tracks whether Hale is requesting Commander approval "
            "for actions inside her 95% authorized band. Proxy would require parsing "
            "conversation logs for question-marks vs. execute+report patterns."
        ),
        "action": (
            "PENDING SOURCE: Wire to hale_decisions.md gate-type field or "
            "conversation telemetry to detect X-minus behavior automatically."
        ),
        "mode": "STUB",
    })

    return {
        "loop": "push_to_limits",
        "mode": "PARTIAL",
        "mode_note": (
            "PARTIAL: dossier freshness + idle drafts are LIVE. "
            "Staff suggestions + autonomy underuse are STUBS (no source)."
        ),
        "source": "; ".join(source_parts) or "none",
        "findings_count": len(findings),
        "findings": findings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 4 — compliance()  (PARTIAL)
# IG Inspect: WF-17 chain + SO adherence signals
# ─────────────────────────────────────────────────────────────────────────────

def compliance() -> dict:
    """
    Loop 4 — WF-17 chain completion + standing-order adherence (IG inspect equiv).

    MODE: PARTIAL
    - LIVE: git log on 6 protected files (recent changes noted — NOT violations
            when .protections_lifted sentinel exists; labeled accordingly).
    - LIVE: draft_metadata.json template_type check (client drafts should have
            a WF-17 label; any without are surfaced).
    - STUB: creative-chain checklist completion (no checklist data in draft_metadata).
    - STUB: SO text compliance scan (no NLP source).
    """
    findings: list[dict] = []
    source_parts: list[str] = []

    # ── LIVE: protected file change signal ────────────────────────────────────
    protections_suspended = PROTECTIONS_SENTINEL.exists()
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20", "--", *PROTECTED_FILES],
            capture_output=True, text=True, cwd=ROOT, timeout=10,
        )
        commits = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
        source_parts.append(f"git log (6 protected files, last 20 commits → {len(commits)} hits)")

        if commits:
            if protections_suspended:
                findings.append({
                    "id": "PROTECTED-FILES-CHANGES-AUTHORIZED",
                    "severity": "INFO",
                    "title": (
                        f"{len(commits)} recent commit(s) touched protected files — "
                        "AUTHORIZED (.protections_lifted sentinel active, SO 2026-06-21)"
                    ),
                    "detail": {
                        "sentinel": str(PROTECTIONS_SENTINEL),
                        "suspension_note": "Protections suspended by Commander directive 2026-06-21. Commits are authorized. Noted for the record only.",
                        "commits": commits[:10],
                    },
                    "action": (
                        "No action required while protections suspended. "
                        "When sentinel removed, re-check this gate."
                    ),
                })
            else:
                findings.append({
                    "id": "PROTECTED-FILES-CHANGES-ALERT",
                    "severity": "RED",
                    "title": f"{len(commits)} recent commit(s) touched protected files — protections ACTIVE",
                    "detail": {"commits": commits[:10]},
                    "action": (
                        "IG flag: verify each commit was routed through CC per SO 2026-06-08. "
                        "Unauthorized changes to these 6 files require Commander notification."
                    ),
                })
        else:
            findings.append({
                "id": "PROTECTED-FILES-CLEAN",
                "severity": "INFO",
                "title": "No recent commits to 6 protected files (last 20 commits clean)",
                "detail": {"files_checked": PROTECTED_FILES},
            })
    except Exception as e:
        findings.append({
            "id": "GIT-LOG-ERROR",
            "severity": "WARN",
            "title": f"Could not run git log on protected files: {e}",
        })
        source_parts.append(f"git log FAILED: {e}")

    # ── LIVE: draft_metadata WF-17 routing check ─────────────────────────────
    draft_meta = _load_json(DRAFT_METADATA_PATH)
    if draft_meta:
        client_drafts = {
            k: v for k, v in draft_meta.items()
            if isinstance(v, dict) and v.get("template_type") == "client"
        }
        # Drafts addressed to non-wing addresses (not johnloucks3) without WF-17 label
        # are a routing concern
        non_wing = {
            k: v for k, v in client_drafts.items()
            if "johnloucks3" not in str(v.get("to", ""))
            and "d2mconcierge" not in str(v.get("to", ""))
        }
        if non_wing:
            findings.append({
                "id": "WF17-ROUTING-CONCERN",
                "severity": "RED",
                "title": f"{len(non_wing)} client draft(s) addressed outside wing — WF-17 routing concern",
                "detail": [
                    {"draft_id": k, "to": v.get("to"), "subject": v.get("subject","?")[:60]}
                    for k, v in list(non_wing.items())[:5]
                ],
                "action": "IG flag: client drafts must stage in johnloucks3 per SO TP_DRAFT_ROUTING_20260620.",
            })
        else:
            findings.append({
                "id": "WF17-ROUTING-OK",
                "severity": "INFO",
                "title": f"WF-17 routing OK: all {len(client_drafts)} client draft(s) addressed to wing accounts",
            })
        source_parts.append(f"draft_metadata.json ({len(client_drafts)} client drafts checked)")

    # ── STUB: creative-chain checklist ────────────────────────────────────────
    findings.append({
        "id": "CREATIVE-CHAIN-CHECKLIST",
        "severity": "STUB",
        "title": "[STUB] Creative-chain completion checklist — no data source in draft_metadata",
        "detail": (
            "draft_metadata.json has no 'chain_steps_completed' field. "
            "Cannot verify Reyes/Luna/Naia/Dani/TALON/JET sign-off automatically."
        ),
        "action": (
            "PENDING SOURCE: Add chain_steps_completed[] to draft_metadata entries "
            "at creation time. Wire checklist enforcement here."
        ),
        "mode": "STUB",
    })

    # ── STUB: full SO text compliance scan ───────────────────────────────────
    findings.append({
        "id": "SO-TEXT-COMPLIANCE",
        "severity": "STUB",
        "title": "[STUB] SO text compliance scan — no NLP/semantic source",
        "detail": (
            "Standing-order text adherence (e.g., banned phrasing, model routing, "
            "header format) cannot be auto-checked without conversation log ingestion."
        ),
        "action": (
            "PENDING SOURCE: Conversation log export + pattern match on banned phrases "
            "would make this LIVE. Out of scope for this release."
        ),
        "mode": "STUB",
    })

    return {
        "loop": "compliance",
        "mode": "PARTIAL",
        "mode_note": (
            "PARTIAL: git log on 6 protected files + draft routing are LIVE. "
            "Creative-chain checklist + SO text scan are STUBS (no source)."
        ),
        "source": "; ".join(source_parts) or "none",
        "findings_count": len(findings),
        "findings": findings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOOP 5 — complaints()  (PARTIAL)
# IG Resolve: staff dissents + client complaint signals
# ─────────────────────────────────────────────────────────────────────────────

def complaints() -> dict:
    """
    Loop 5 — Staff dissents + client complaint signals (IG resolve equiv).

    MODE: PARTIAL
    - LIVE: staff_comments_live.jsonl — cursor-based; surfaces unread items
            since last cursor position.
    - STUB: client complaint signals — no defined source (no CRM complaint field,
            no email sentiment scan).
    """
    findings: list[dict] = []
    source_parts: list[str] = []

    # ── LIVE: staff comments feed ─────────────────────────────────────────────
    if STAFF_COMMENTS_FEED.exists():
        # Read cursor
        last_read_ts: str | None = None
        if STAFF_COMMENTS_CURSOR.exists():
            cursor = _load_json(STAFF_COMMENTS_CURSOR)
            if cursor:
                last_read_ts = cursor.get("last_read_ts")

        # Parse feed entries
        all_entries: list[dict] = []
        for line in STAFF_COMMENTS_FEED.read_text().strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                all_entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass

        # Entries since cursor
        unread: list[dict] = []
        for entry in all_entries:
            entry_ts = entry.get("ts", "")
            if last_read_ts is None or entry_ts > last_read_ts:
                unread.append(entry)

        source_parts.append(
            f"staff_comments_live.jsonl ({len(all_entries)} total, "
            f"{len(unread)} unread since cursor={last_read_ts or 'never'})"
        )

        # Separate P0 dissents from rest
        p0_dissents = [e for e in unread if e.get("priority") == "P0" or e.get("msg_type") == "dissent"]
        p1_items = [e for e in unread if e not in p0_dissents]

        if p0_dissents:
            findings.append({
                "id": "STAFF-DISSENT-P0",
                "severity": "RED",
                "title": f"{len(p0_dissents)} unread P0 dissent(s) in staff comments feed",
                "detail": [
                    {
                        "ts": e.get("ts"),
                        "author": e.get("author"),
                        "msg_type": e.get("msg_type"),
                        "content": str(e.get("content", e.get("message", "")))[:120],
                    }
                    for e in p0_dissents
                ],
                "action": (
                    "IG flag: P0 dissents require Commander acknowledgment. "
                    "Run staff_comments_handler.py or surface inline."
                ),
            })
        if p1_items:
            findings.append({
                "id": "STAFF-COMMENTS-P1",
                "severity": "WARN",
                "title": f"{len(p1_items)} unread P1 staff comment(s)",
                "detail": [
                    {
                        "ts": e.get("ts"),
                        "author": e.get("author"),
                        "msg_type": e.get("msg_type"),
                        "content": str(e.get("content", e.get("message", "")))[:100],
                    }
                    for e in p1_items[:5]
                ],
                "action": "Review and acknowledge; advance cursor when actioned.",
            })
        if not unread:
            findings.append({
                "id": "STAFF-FEED-CLEAR",
                "severity": "INFO",
                "title": "Staff comments feed clear — no unread items since last cursor",
                "detail": {"cursor": last_read_ts, "total_entries": len(all_entries)},
            })
    else:
        findings.append({
            "id": "STAFF-FEED-MISSING",
            "severity": "WARN",
            "title": "staff_comments_live.jsonl missing — staff comment intake unavailable",
            "action": "Check OpsCenter/staff_comments_feed.py setup.",
        })
        source_parts.append("staff_comments_live.jsonl MISSING")

    # ── STUB: client complaint signals ────────────────────────────────────────
    findings.append({
        "id": "CLIENT-COMPLAINTS-STUB",
        "severity": "STUB",
        "title": "[STUB] Client complaint signals — no defined source",
        "detail": (
            "There is no CRM complaint field, no email sentiment scan, and no "
            "structured complaint log. Client dissatisfaction is currently invisible "
            "to automation. Signals that COULD work: email subject-line scan for "
            "'issue'/'problem'/'unhappy', TESS note fields, dossier flags."
        ),
        "action": (
            "PENDING SOURCE: Add complaint_flag boolean to dossier schema + TESS notes. "
            "Wire scan here to make LIVE."
        ),
        "mode": "STUB",
    })

    return {
        "loop": "complaints",
        "mode": "PARTIAL",
        "mode_note": (
            "PARTIAL: staff_comments_live.jsonl is LIVE (cursor-based). "
            "Client complaint signals are STUB (no source defined)."
        ),
        "source": "; ".join(source_parts) or "none",
        "findings_count": len(findings),
        "findings": findings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# run_all()
# ─────────────────────────────────────────────────────────────────────────────

def run_all(write_report: bool = True) -> dict:
    """
    Execute all five prod-loops and write OpsCenter/hale_enforcer_report.json.
    Prints ⚡ summary to stdout (per-loop: mode + count).
    Returns the report dict.
    """
    run_ts = NOW.isoformat()

    loops = {
        "readiness": readiness,
        "taskings": taskings,
        "push_to_limits": push_to_limits,
        "compliance": compliance,
        "complaints": complaints,
    }

    results: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for name, fn in loops.items():
        try:
            results[name] = fn()
        except Exception as exc:
            errors[name] = str(exc)
            results[name] = {
                "loop": name,
                "mode": "ERROR",
                "source": "exception",
                "findings_count": 0,
                "findings": [{"id": "LOOP-ERROR", "severity": "RED", "title": str(exc)}],
            }

    # Aggregate severity
    all_findings = []
    for r in results.values():
        all_findings.extend(r.get("findings", []))

    red_count = sum(1 for f in all_findings if f.get("severity") == "RED")
    warn_count = sum(1 for f in all_findings if f.get("severity") == "WARN")
    stub_count = sum(1 for f in all_findings if f.get("severity") == "STUB")
    info_count = sum(1 for f in all_findings if f.get("severity") == "INFO")

    report = {
        "generated_at": run_ts,
        "summary": {
            "total_findings": len(all_findings),
            "red": red_count,
            "warn": warn_count,
            "stub": stub_count,
            "info": info_count,
        },
        "loops": results,
        "errors": errors,
        "meta": {
            "author": "Sterling (A7)",
            "version": "1.0.0",
            "date": "2026-07-02",
        },
    }

    if write_report:
        REPORT_PATH.write_text(json.dumps(report, indent=2, default=str))

    # ── ⚡ summary ────────────────────────────────────────────────────────────
    print()
    print("⚡ HALE ENFORCER — 5-LOOP PROD REPORT")
    print(f"   Generated: {run_ts}")
    print()

    _SEVERITY_ICON = {"RED": "🔴", "WARN": "🟡", "STUB": "📋", "INFO": "✅", "ERROR": "💥"}

    for name, r in results.items():
        mode = r.get("mode", "?")
        fc = r.get("findings_count", 0)
        loop_findings = r.get("findings", [])
        red = sum(1 for f in loop_findings if f.get("severity") == "RED")
        warn = sum(1 for f in loop_findings if f.get("severity") == "WARN")

        status_icon = "🔴" if red else ("🟡" if warn else "✅")
        print(f"  {status_icon} [{mode:8s}] {name:<20s}  {fc} finding(s)  "
              f"({red} RED, {warn} WARN)")

        # Print RED finding titles inline
        for f in loop_findings:
            if f.get("severity") == "RED":
                print(f"          └─ 🔴 {f.get('id')}: {f.get('title','?')[:80]}")

    print()
    print(f"  TOTALS: 🔴 {red_count} RED | 🟡 {warn_count} WARN | "
          f"📋 {stub_count} STUB | ✅ {info_count} INFO")

    if errors:
        print(f"\n  ⚠️  Loop errors: {list(errors.keys())}")

    if write_report:
        print(f"\n  Report: {REPORT_PATH}")

    print()

    return report


# ─────────────────────────────────────────────────────────────────────────────
# __main__
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Hale Enforcer — 5-loop prod engine")
    ap.add_argument("--no-write", action="store_true", help="Skip writing report JSON")
    ap.add_argument("--loop", choices=["readiness", "taskings", "push_to_limits",
                                        "compliance", "complaints"],
                    help="Run a single loop only")
    args = ap.parse_args()

    if args.loop:
        loop_fns = {
            "readiness": readiness,
            "taskings": taskings,
            "push_to_limits": push_to_limits,
            "compliance": compliance,
            "complaints": complaints,
        }
        result = loop_fns[args.loop]()
        print(json.dumps(result, indent=2, default=str))
    else:
        run_all(write_report=not args.no_write)
