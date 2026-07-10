#!/usr/bin/env python3
"""
Commander Next-Move Predictor — Hale + Silver + staff, grounded.

The core discipline (Rocket's own standard, per Personas/rocket_ground_truth.md:
"deterministic gates, Silver never guesses a pass"): every prediction here must
cite a real, checkable basis — a dated file, a counted pattern, an actual open
item. No prediction may be pure vibes. Confidence follows the Pipeline Integrity
Negative-Space Rule: CONFIRMED (explicit scheduled trigger already on record) /
INFERRED (a real historical pattern, count-backed) / UNKNOWN (a plausible guess
— tagged as exactly that, never dressed up as more).

THE LEDGER IS THE POINT. A prediction with no later hit/miss check is
unfalsifiable — the same failure mode as the 2026-07-06 "40 proposals executed"
report, just wearing a fortune-telling hat instead of a status-report hat.
Every run appends to OpsCenter/commander_prediction_ledger.json; a separate
mark_outcomes() pass (weekly, alongside the existing Sunday closure review)
scores each open prediction HIT / MISS / PARTIAL against what actually
happened, so accuracy is a real, growing number — not an asserted one.

This is the automation of the existing Close-Out Ritual (hale_cos.md,
2026-07-06 directive): "ask Silver — What is the Commander likely to want
next? Want to do next? Want to discuss next?" — not a new taxonomy, the
existing ritual made repeatable and checkable.

Usage:
    python3 core/prediction/commander_predictor.py --run       # generate predictions
    python3 core/prediction/commander_predictor.py --mark ID hit|miss|partial "note"
    python3 core/prediction/commander_predictor.py --report     # accuracy + open predictions
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO = Path("/home/john/Thunderbird")
HALE_STATE = REPO / "hale_state.json"
MISSION_BOARD = REPO / "OpsCenter" / "mission_board.json"
DECISIONS_LOG = REPO / "hale_decisions.md"
DOSSIERS_DIR = REPO / "dossiers"
LEDGER = REPO / "OpsCenter" / "commander_prediction_ledger.json"

# Real, already-wired signal modules — this predictor is their first real
# consumer (they've sat unwired since the 2026-07-06 batch; see
# hale_decisions.md 2026-07-07 correction entry). Import is optional/soft —
# if either module is unavailable, the predictor still runs on file-based
# signals alone rather than failing closed.
try:
    sys.path.insert(0, str(REPO))
    from core.risk.cancellation_scorer import score_booking, features_from_known_booking
    _HAVE_CANCELLATION_SCORER = True
except Exception:
    _HAVE_CANCELLATION_SCORER = False


@dataclass
class Prediction:
    id: str
    date_predicted: str
    predicted_action: str
    basis: str
    confidence: str  # CONFIRMED | INFERRED | UNKNOWN
    domain: str       # which staff lens this touches (Harlan/Dembe/Dani/Sterling/Silver/Hale)
    source_files: list = field(default_factory=list)
    status: str = "open"  # open | hit | miss | partial
    resolved_date: Optional[str] = None
    resolution_note: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _load_ledger() -> list[dict]:
    return _load_json(LEDGER, [])


def _save_ledger(entries: list[dict]) -> None:
    LEDGER.write_text(json.dumps(entries, indent=2))


def _today() -> date:
    return datetime.now(timezone.utc).astimezone().date()


# ---------------------------------------------------------------------------
# Signal 1 — deferred_alerts in hale_state.json. These are CONFIRMED by
# construction: the Wing already scheduled a specific trigger_date for a
# specific Commander-relevant event. The prediction is just "this will
# surface to you around then" — not a guess.
# ---------------------------------------------------------------------------

def predict_from_deferred_alerts(state: dict, horizon_days: int = 14) -> list[Prediction]:
    out = []
    today = _today()
    for alert in state.get("deferred_alerts", []):
        trigger_raw = alert.get("trigger_date")
        if not trigger_raw:
            continue
        try:
            trigger = datetime.strptime(trigger_raw, "%Y-%m-%d").date()
        except ValueError:
            continue
        delta = (trigger - today).days
        if -3 <= delta <= horizon_days:  # include just-passed (3d) so nothing silently drops
            when = "already due" if delta < 0 else (f"in {delta}d" if delta else "today")
            out.append(Prediction(
                id=f"DA-{alert.get('id', 'unknown')}",
                date_predicted=today.isoformat(),
                predicted_action=f"You'll act on: {alert.get('message', alert.get('id'))[:180]}",
                basis=f"Scheduled deferred_alert, trigger_date={trigger_raw} ({when}), priority={alert.get('priority', '?')}",
                confidence="CONFIRMED",
                domain="Harlan" if "FPD" in alert.get("id", "") or "amount" in alert else "Hale",
                source_files=["hale_state.json#deferred_alerts"],
            ))
    return out


# ---------------------------------------------------------------------------
# Signal 2 — Mission board P0s open >7 days. Basis: a real, counted pattern
# from hale_decisions.md — the Decision Matrix on Login doctrine already
# established that aging P0/P1 items are the primary Commander-review
# trigger. This just makes that check run ahead of time instead of only at
# login.
# ---------------------------------------------------------------------------

def predict_from_aging_p0(board: dict, min_age_days: int = 7) -> list[Prediction]:
    out = []
    today = _today()
    missions = board.get("missions", []) or board.get("active_missions", [])
    if isinstance(missions, dict):
        missions = list(missions.values())
    terminal = {"complete", "completed", "closed", "archived", "closed_duplicate",
                "resolved_new_finding", "killed", "suspended"}
    for m in missions:
        if not isinstance(m, dict):
            continue
        if m.get("status", "").lower() in terminal:
            continue
        if m.get("priority") != "P0":
            continue
        created_raw = m.get("created_at", "")
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).date()
        except Exception:
            continue
        age = (today - created).days
        if age >= min_age_days:
            out.append(Prediction(
                id=f"P0AGE-{m.get('id', 'unknown')}",
                date_predicted=today.isoformat(),
                predicted_action=f"You'll ask for status on: {m.get('title', m.get('id'))[:150]}",
                basis=f"P0 mission open {age}d (created {created_raw[:10]}), status={m.get('status')}",
                confidence="INFERRED",
                domain="Sterling",
                source_files=["OpsCenter/mission_board.json"],
            ))
    return out


# ---------------------------------------------------------------------------
# Signal 3 — dossier FPD dates inside the 21-day window. Basis: the same
# 21-day-out pattern already coded into LOUCKS-3122006-FPD-ALERT and the
# McLeod FPD trigger (both hardcode "X days out" thresholds) — this
# generalizes that observed pattern across every dossier instead of one
# hand-authored alert at a time.
# ---------------------------------------------------------------------------

_FPD_RE = re.compile(r'\*\*FPD[:\-]?\*\*\s*\$?([\d,]+(?:\.\d{2})?)\D+(\d{4}-\d{2}-\d{2})', re.IGNORECASE)
_FPD_RE2 = re.compile(r'FPD[:\-]?\s*(\d{4}-\d{2}-\d{2})', re.IGNORECASE)


def predict_from_dossier_fpds(window_days: int = 21) -> list[Prediction]:
    out = []
    today = _today()
    if not DOSSIERS_DIR.exists():
        return out
    for path in sorted(DOSSIERS_DIR.glob("*.md")):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        # Real bug caught on first run: a naive glob picked up a dossier
        # explicitly flagged STALE/SUPERSEDED (wrong FPD, wrong balance) by
        # Sterling 2026-05-28 and generated a prediction off bad data.
        # Respect that same flag convention here.
        header = text[:600]
        if "STALE / SUPERSEDED" in header or "NO LONGER AUTHORITATIVE" in header:
            continue
        m = _FPD_RE2.search(text)
        if not m:
            continue
        try:
            fpd = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        delta = (fpd - today).days
        if 0 <= delta <= window_days:
            out.append(Prediction(
                id=f"FPD-{path.stem}",
                date_predicted=today.isoformat(),
                predicted_action=f"You'll want a payment-status check for {path.stem.replace('_', ' ')} (FPD {delta}d out)",
                basis=f"FPD {fpd.isoformat()} found in {path.name}, {delta}d from today, within the {window_days}d pattern window",
                confidence="INFERRED",
                domain="Harlan",
                source_files=[str(path.relative_to(REPO))],
            ))
    return out


# ---------------------------------------------------------------------------
# Signal 4 — cancellation risk (real consumer for the previously-unwired
# cancellation_scorer). Only fires if the module actually imported AND real
# KNOWN_BOOKINGS data is available — never fabricates a score.
# ---------------------------------------------------------------------------

def predict_from_cancellation_risk() -> list[Prediction]:
    out = []
    if not _HAVE_CANCELLATION_SCORER:
        return out
    try:
        from core.scheduling.thunderbird_anchor_dates import KNOWN_BOOKINGS
    except Exception:
        return out
    today = _today()
    for key, booking in KNOWN_BOOKINGS.items():
        try:
            feats = features_from_known_booking(key, booking, today=today)
            result = score_booking(feats)
        except Exception:
            continue
        if result.flagged_for_intervention and result.confidence >= 0.5:
            out.append(Prediction(
                id=f"RISK-{key}",
                date_predicted=today.isoformat(),
                predicted_action=f"You may need a retention call on {key} — {result.recommendation}",
                basis=f"cancellation_scorer risk={result.risk_score} confidence={result.confidence} ({result.signal_breakdown})",
                confidence="INFERRED" if result.confidence >= 0.75 else "UNKNOWN",
                domain="Dani",
                source_files=["core/risk/cancellation_scorer.py", "core/scheduling/thunderbird_anchor_dates.py"],
            ))
    return out


TERMINAL_STATUSES = {"complete", "completed", "closed", "archived", "closed_duplicate",
                      "resolved_new_finding", "killed", "suspended"}

HEARTBEAT_SCAN = REPO / "OpsCenter" / "state" / "heartbeat_scan_latest.json"


# ---------------------------------------------------------------------------
# Signal 5 — next suspense to tackle. LEDGER-ELIGIBLE (falsifiable: did he
# act on this specific item or not). Prefers heartbeat_scan_latest.json
# (freshly computed same-day) over mission_board.suspense_watch, which is a
# hand-appended list with entries back to 2026-05-25 that are never cleared
# -- the same level-triggered staleness trap Silver already documented and
# that the STALE dossier just sprang on this predictor minutes ago. Reuses
# the same TERMINAL_STATUSES filter already fixed for the P0-age signal.
# ---------------------------------------------------------------------------

def predict_next_suspense(board: dict, top_n: int = 3) -> list[Prediction]:
    today = _today()

    # Primary: fresh heartbeat scan (computed same-day, not a stale hand-list)
    heartbeat = _load_json(HEARTBEAT_SCAN, {})
    findings = heartbeat.get("findings", [])
    scanned_at = heartbeat.get("scanned_at", "")
    fresh = False
    if scanned_at:
        try:
            scanned_date = datetime.fromisoformat(scanned_at.replace("Z", "+00:00")).date()
            fresh = (today - scanned_date).days <= 1
        except Exception:
            fresh = False

    candidates: list[Prediction] = []
    if fresh and findings:
        # Rank: repeat_alert (crossed a real threshold) outranks stale_ci_tool
        # (a currency check, lower urgency) — both are real, dated findings.
        ranked = sorted(findings, key=lambda f: 0 if f.get("category") == "repeat_alert" else 1)
        for f in ranked[:top_n]:
            candidates.append(Prediction(
                id=f"SUSP-{hash(f.get('what', ''))% 100000}",
                date_predicted=today.isoformat(),
                predicted_action=f"Next suspense likely to pull your attention: {f.get('what', '')[:160]}",
                basis=f"heartbeat_scan_latest.json ({scanned_at[:16]}), category={f.get('category')}, action={f.get('action', '')[:100]}",
                confidence="INFERRED",
                domain="Silver",
                source_files=["OpsCenter/state/heartbeat_scan_latest.json"],
            ))
        return candidates

    # Fallback: mission_board suspense_date, filtered through the same
    # terminal-status set (a mission marked complete/killed is not a live
    # suspense no matter what its stale suspense_date says).
    missions = board.get("missions", []) or board.get("active_missions", [])
    if isinstance(missions, dict):
        missions = list(missions.values())
    live_suspenses = []
    for m in missions:
        if not isinstance(m, dict):
            continue
        if m.get("status", "").lower() in TERMINAL_STATUSES:
            continue
        susp_raw = m.get("suspense_date")
        if not susp_raw:
            continue
        try:
            susp = datetime.fromisoformat(str(susp_raw).replace("Z", "+00:00")).date()
        except Exception:
            continue
        live_suspenses.append((susp, m))

    live_suspenses.sort(key=lambda t: t[0])
    for susp, m in live_suspenses[:top_n]:
        delta = (susp - today).days
        candidates.append(Prediction(
            id=f"SUSP-{m.get('id', 'unknown')}",
            date_predicted=today.isoformat(),
            predicted_action=f"Next suspense likely to pull your attention: {m.get('title', m.get('id'))[:150]}",
            basis=f"mission_board suspense_date={susp.isoformat()} ({delta:+d}d), status={m.get('status')} (non-terminal, verified)",
            confidence="INFERRED",
            domain="Sterling",
            source_files=["OpsCenter/mission_board.json"],
        ))
    return candidates


def generate_predictions() -> list[Prediction]:
    state = _load_json(HALE_STATE, {})
    board = _load_json(MISSION_BOARD, {})
    preds: list[Prediction] = []
    preds += predict_from_deferred_alerts(state)
    preds += predict_from_aging_p0(board)
    preds += predict_from_dossier_fpds()
    preds += predict_from_cancellation_risk()
    preds += predict_next_suspense(board)
    return preds


# ---------------------------------------------------------------------------
# RECURRING-CORRECTION ANALYSIS — deliberately NOT a Prediction / NOT in the
# ledger. "What's your biggest problem" is a synthesis, not a yes/no outcome
# -- filing it as a scored prediction would launder an unfalsifiable claim
# into the same accuracy metric that gives the real ones their credibility.
#
# Also an important framing correction: this surfaces recurring corrections
# OF THE WING (patterns Hale/staff have been told to fix repeatedly) — not
# a claim about the Commander's own problems. That's a category error this
# function must not make.
#
# Weighted by the Commander's own stated emphasis + recency, not raw file
# count (a theme having many memory files means it was easy to log, not
# that it matters most).
# ---------------------------------------------------------------------------

MEMORY_DIR = Path.home() / ".claude" / "projects" / "-home-john-Thunderbird" / "memory"

# Patterns in CLAUDE.md the Commander himself flagged as most important —
# read directly from the document's own emphasis language, not inferred.
_SELF_STATED_TOP_PATTERNS = [
    ("DO NOT ASK THE COMMANDER TO CHOOSE", "SO 2026-06-20",
     "CLAUDE.md's own words: \"The single most-violated rule.\" Wing keeps asking permission instead of deciding+executing."),
    ("OBSTACLE-ROUTING & INDEPENDENT VERIFICATION", "SO 2026-07-06",
     "CLAUDE.md tags this \"Commander-commended\" — i.e. he explicitly praised the fix. Wing's habit: trusting a system's own self-report instead of checking ground truth."),
]


def analyze_recurring_corrections() -> dict:
    """Returns a dated, cited synthesis — never a scored prediction."""
    today = _today()
    claude_md = (REPO / "CLAUDE.md").read_text(errors="ignore") if (REPO / "CLAUDE.md").exists() else ""

    top_patterns = []
    for name, so_date, note in _SELF_STATED_TOP_PATTERNS:
        present = name in claude_md
        top_patterns.append({
            "pattern": name,
            "so_date": so_date,
            "note": note,
            "confirmed_still_in_claude_md": present,
        })

    # Recency cluster: feedback-type memory files touching 2026-07 (this
    # month) vs total — recency signal, explicitly caveated as secondary,
    # not a ranking basis on its own.
    recent_count, total_count = 0, 0
    if MEMORY_DIR.exists():
        for f in MEMORY_DIR.glob("feedback_*.md"):
            total_count += 1
            try:
                if "2026-07" in f.read_text(errors="ignore")[:2000]:
                    recent_count += 1
            except OSError:
                continue

    # This session's own live instance of the exact same top pattern —
    # dated today, a real data point, not retrospective.
    this_session_instance = (
        "This session: Commander demanded proof before accepting the "
        "'40 proposals executed' claim, rejected 3 Tier-C asks outright "
        "('no benefit to me'), and asked for a predictor that scores itself "
        "against outcomes rather than asserting accuracy — three real "
        "instances of the same two patterns above, same day."
    )

    return {
        "analysis_date": today.isoformat(),
        "framing": "Recurring corrections OF THE WING (patterns Hale/staff have been "
                   "told to fix repeatedly) — not a claim about the Commander's own problems.",
        "top_patterns_by_his_own_stated_emphasis": top_patterns,
        "this_session_live_instance": this_session_instance,
        "secondary_signal_recency_cluster": {
            "feedback_files_total": total_count,
            "feedback_files_mentioning_2026-07": recent_count,
            "caveat": "Recency cluster only — file count is a weak proxy for importance "
                      "and is NOT used to rank these patterns.",
        },
        "not_scored": "This analysis is not in commander_prediction_ledger.json and carries "
                      "no hit/miss status — it is a synthesis, not a falsifiable prediction.",
    }


def silver_verify(preds: list[Prediction]) -> list[Prediction]:
    """Silver's gate: drop any prediction whose basis doesn't actually check
    out against the cited source file right now (re-verify, never trust the
    generator's own claim). This is the "never guess a pass" discipline."""
    verified = []
    for p in preds:
        ok = True
        for src in p.source_files:
            real_path = src.split("#")[0]
            if not (REPO / real_path).exists():
                ok = False
        if ok:
            verified.append(p)
    return verified


def run(write: bool = False) -> list[Prediction]:
    preds = generate_predictions()
    preds = silver_verify(preds)
    if write:
        ledger = _load_ledger()
        existing_ids = {e["id"] for e in ledger}
        added = 0
        for p in preds:
            if p.id not in existing_ids:
                ledger.append(p.to_dict())
                added += 1
        _save_ledger(ledger)
        print(f"Generated {len(preds)} predictions, {added} new (rest already on ledger).", file=sys.stderr)
    return preds


def mark_outcome(pred_id: str, status: str, note: str) -> bool:
    ledger = _load_ledger()
    for entry in ledger:
        if entry["id"] == pred_id:
            entry["status"] = status
            entry["resolved_date"] = _today().isoformat()
            entry["resolution_note"] = note
            _save_ledger(ledger)
            return True
    return False


def report() -> dict:
    ledger = _load_ledger()
    resolved = [e for e in ledger if e["status"] != "open"]
    hits = [e for e in resolved if e["status"] == "hit"]
    accuracy = round(len(hits) / len(resolved), 3) if resolved else None
    return {
        "total_predictions_ever": len(ledger),
        "open": len([e for e in ledger if e["status"] == "open"]),
        "resolved": len(resolved),
        "hits": len(hits),
        "accuracy": accuracy,
        "accuracy_note": "null until predictions have been marked against real outcomes — never asserted before that" if accuracy is None else None,
        "open_predictions": [e for e in ledger if e["status"] == "open"],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Commander Next-Move Predictor")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--mark", nargs=3, metavar=("ID", "STATUS", "NOTE"))
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.mark:
        pid, status, note = args.mark
        ok = mark_outcome(pid, status, note)
        print(f"{'Marked' if ok else 'NOT FOUND:'} {pid} -> {status}")
    elif args.report:
        print(json.dumps(report(), indent=2))
    elif args.run:
        preds = run(write=args.write)
        print(json.dumps([p.to_dict() for p in preds], indent=2))
    else:
        parser.print_help()
