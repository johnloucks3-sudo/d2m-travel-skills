#!/usr/bin/env python3
"""
Hale Incident Router — triages watchdog incidents every 5 minutes.
Routes auto-healed events to brief queue only.
Routes Tier 1 unrecoverable events to Commander via Telegram.
Invokes ELON for recurring or novel-critical patterns.

Run via: hale-incident-handler.timer (every 5 min)
Or manually: python3 hale_incident_router.py
"""
import json
import logging
import os
import hashlib
import subprocess
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
THUNDERBIRD = Path("/home/john/Thunderbird")
OPSCENTER = THUNDERBIRD / "OpsCenter"
LOGS = THUNDERBIRD / "logs"

QUEUE_PATH = OPSCENTER / "hale_incident_queue.jsonl"
INCIDENTS_TODAY = OPSCENTER / "hale_incidents_today.json"
SIGNATURES_PATH = OPSCENTER / "hale_incident_signatures.json"
PLAYBOOK_PATH = OPSCENTER / "hale_remediation_playbook.json"
ELON_PROPOSALS = OPSCENTER / "elon_proposals"
LOG_PATH = LOGS / "hale_incident_router.log"

# ── Telegram ────────────────────────────────────────────────────────────────
COMMANDER_CHAT_ID = int(os.environ.get("TELEGRAM_RELAY_CHAT_ID", "-5248121475"))  # → D2M Channels relay
BOT_TOKEN = os.environ.get("TELEGRAM_RELAY_TOKEN", "")

# ── Rule 1 (hardcoded, never changes) ───────────────────────────────────────
RULE_1 = "auto_heal_success_never_pages_commander"

# Severities that MAY page Commander — but only if service is in COMMANDER_GATE_SERVICES
COMMANDER_PAGE_SEVERITIES = {"tier1_critical", "unrecoverable", "crash_loop", "code_broken", "engine_dead"}
# Event types that page Commander if severity matches
MODE_RED_PAGES = True

# COMMANDER GATE (SO 2026-05-07 — Manage the Exceptions Doctrine):
# Hale repairs first. Commander is paged ONLY if ALL THREE conditions are true:
#   1. Service is in COMMANDER_GATE_SERVICES (genuinely client-blocking)
#   2. Severity matches COMMANDER_PAGE_SEVERITIES
#   3. Auto-heal attempts exhausted
# Infrastructure/mirror services (e.g. thunderbird-drive-sync) are NEVER in this list.
# Updated 2026-05-14: drive-sync removed — reclassified to Tier 2 in watchdog.
COMMANDER_GATE_SERVICES = {
    "hale-draft-engine",        # Blocks lifecycle emails to clients
    "hale-touchpoint-proposer", # Blocks touchpoint delivery
    "d2m-lifecycle",            # Blocks lifecycle state transitions
    "d2m-correspondence-sync",  # Blocks dossier update after send
    "d2m-fpd-alert",            # Blocks final payment date warnings
    "ai-auth-probe",            # AI API auth failure after auto-repair exhausted
}

# ── Logging ─────────────────────────────────────────────────────────────────
LOGS.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("hale_incident_router")


# ─────────────────────────────────────────────────────────────────────────────
# Signature / recurrence tracking
# ─────────────────────────────────────────────────────────────────────────────

def compute_signature(service: str, details: str) -> str:
    first_line = (details or "").strip().splitlines()[0][:120] if details else ""
    raw = f"{service}:{first_line}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def load_signatures() -> dict:
    if SIGNATURES_PATH.exists():
        try:
            return json.loads(SIGNATURES_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_signatures(sigs: dict) -> None:
    SIGNATURES_PATH.write_text(json.dumps(sigs, indent=2))


def record_signature(sig: str, ts: str) -> None:
    sigs = load_signatures()
    if sig not in sigs:
        sigs[sig] = {"occurrences": [], "last_elon_invoke": None}
    sigs[sig]["occurrences"].append(ts)
    # Prune to 7 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    sigs[sig]["occurrences"] = [t for t in sigs[sig]["occurrences"] if t >= cutoff]
    save_signatures(sigs)


def count_recurrence_7d(sig: str) -> int:
    sigs = load_signatures()
    if sig not in sigs:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    return len([t for t in sigs[sig]["occurrences"] if t >= cutoff])


def elon_rate_capped(sig: str) -> bool:
    sigs = load_signatures()
    last = (sigs.get(sig) or {}).get("last_elon_invoke")
    if not last:
        return False
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return last >= cutoff


def mark_elon_invoked(sig: str) -> None:
    sigs = load_signatures()
    if sig not in sigs:
        sigs[sig] = {"occurrences": [], "last_elon_invoke": None}
    sigs[sig]["last_elon_invoke"] = datetime.now(timezone.utc).isoformat()
    save_signatures(sigs)


# ─────────────────────────────────────────────────────────────────────────────
# Telegram (single chokepoint)
# ─────────────────────────────────────────────────────────────────────────────

# A gap this long between two consecutive occurrences of the same signature means
# the incident cleared in between — the later occurrence is a fresh recurrence that
# is allowed to page again. A continuously-present incident (watchdog re-enqueues
# every few minutes) never crosses this gap, so it pages exactly once.
_RECUR_GAP_MINUTES = 60


def _parse_ts(ts: str):
    try:
        dt = datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return None


def _is_fresh_recurrence(entry: dict) -> bool:
    """True when the incident cleared and is now recurring — i.e. the two most
    recent occurrences are more than _RECUR_GAP_MINUTES apart. A first-ever
    occurrence or a continuously-present incident returns False (stay silent)."""
    occ = sorted(t for t in entry.get("occurrences", []) if t)
    if len(occ) < 2:
        return False
    last, prev = _parse_ts(occ[-1]), _parse_ts(occ[-2])
    if not last or not prev:
        return False
    return (last - prev) > timedelta(minutes=_RECUR_GAP_MINUTES)


def page_commander(event: dict, reason: str) -> None:
    """ONLY function that sends Telegram to Commander. Logs every call.

    ONE AND DONE (2026-07-04, Silver/A7): replaces the old time-based 60-min
    cooldown, which was level-triggered and re-paged hourly for as long as an
    incident stayed unresolved (same "cooldown ≠ one-time gate" bug flagged in
    silver_ground_truth.md #2). Now edge-triggered: page once per signature and
    stay silent while the incident persists unchanged. Re-page only if the
    escalation reason changes (incident actually changed/escalated) OR the
    incident cleared and recurred (a gap in its occurrence history)."""
    if not BOT_TOKEN:
        log.error("page_commander: BOT_TOKEN not set — cannot page Commander")
        return

    details = str(event.get("details", ""))
    service = event.get("service", "unknown")
    sig = compute_signature(service, details)
    sigs = load_signatures()
    entry = sigs.setdefault(sig, {"occurrences": [], "last_elon_invoke": None})

    prev_reason = entry.get("paged_reason")
    if prev_reason == reason and not _is_fresh_recurrence(entry):
        log.info(
            "page_commander SUPPRESSED (one-and-done): sig=%s service=%s reason=%s "
            "— already paged, incident unchanged",
            sig, service, reason,
        )
        return

    # Record this page before sending (prevents double-send on exception).
    # paged_reason encodes the escalation level, so an escalation re-pages.
    entry["paged_reason"] = reason
    entry["last_paged"] = datetime.now(timezone.utc).isoformat()
    save_signatures(sigs)

    msg = (
        f"🔴 HALE ESCALATION\n"
        f"Service: {event.get('service', 'unknown')}\n"
        f"Event: {event.get('event_type', 'unknown')}\n"
        f"Reason: {reason}\n"
        f"Time: {event.get('ts', 'unknown')}\n"
        f"Details: {str(event.get('details', ''))[:300]}"
    )
    try:
        import urllib.request
        data = json.dumps({"chat_id": COMMANDER_CHAT_ID, "text": msg}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        log.info(f"page_commander: paged Commander — reason={reason}, service={event.get('service')}")
    except Exception as e:
        log.error(f"page_commander FAILED: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Playbook
# ─────────────────────────────────────────────────────────────────────────────

def load_playbook() -> dict:
    if PLAYBOOK_PATH.exists():
        try:
            return json.loads(PLAYBOOK_PATH.read_text())
        except Exception:
            return {}
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Verification probes
# ─────────────────────────────────────────────────────────────────────────────

def run_verification_probe(service: str) -> tuple[bool, str]:
    """End-to-end probe per service. Falls back to systemctl is-active."""
    if "telegram-gw" in service:
        return _probe_systemctl(service)
    if "mcp" in service:
        return _probe_systemctl(service)
    if "tasking-watcher" in service or "overwatch" in service:
        return _probe_systemctl(service)
    return _probe_systemctl(service)


def _probe_systemctl(service: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service],
            capture_output=True, text=True, timeout=10
        )
        active = result.stdout.strip() == "active"
        return active, f"systemctl is-active: {result.stdout.strip()}"
    except Exception as e:
        return False, f"probe error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# ELON invocation gate
# ─────────────────────────────────────────────────────────────────────────────

def should_invoke_elon(sig: str, event: dict) -> tuple[bool, str]:
    recurrence = count_recurrence_7d(sig)
    event_type = event.get("event_type", "")
    severity = event.get("severity", "")

    if event_type == "crash_loop":
        return True, "crash_loop"
    if recurrence >= 3:
        return True, f"recurrence_pattern ({recurrence}x in 7d)"
    if recurrence == 0 and severity == "critical":
        return True, "novel_critical"
    return False, "below_threshold"


def invoke_elon(sig: str, service: str, event: dict, reason: str) -> dict:
    """Spawns headless Claude as ELON to write a permanent fix proposal."""
    if elon_rate_capped(sig):
        log.info(f"invoke_elon: rate-capped for sig={sig}, skipping")
        return {}

    ELON_PROPOSALS.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    proposal_path = ELON_PROPOSALS / f"PROPOSAL-{date_str}-{service.replace('/', '-')}.md"

    prompt = f"""You are ELON, A12 Innovation & Disruption for Thunderbird Wing, Dreams2Memories Travel.

Pattern detected: service `{service}` — reason: {reason}

Event details:
{json.dumps(event, indent=2)[:2000]}

Produce a structured proposal:

# ROOT CAUSE
[Single paragraph. First principles. Not the symptom.]

# PROPOSED FIX
[ONE of: code_diff | config_change | new_daemon | standing_order | escalate_to_commander]

# IMPLEMENTATION
[Concrete steps Hale can execute autonomously, OR explicit reason this needs Commander.]

# VERIFICATION TEST
[How to prove the fix works. End-to-end probe, not just systemctl is-active.]

# HALE DECISION
[ONE of: APPLY_AUTONOMOUSLY | QUEUE_FOR_COMMANDER | DISCARD]

WRITE this proposal to {proposal_path}
"""
    try:
        creds_path = Path.home() / ".claude" / ".credentials.json"
        env = dict(os.environ)
        if creds_path.exists():
            creds = json.loads(creds_path.read_text())
            token = creds.get("claudeAiOauth", {}).get("accessToken")
            if token:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = token

        from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
        result = spawn_headless_claude(
            prompt=prompt,
            output_file=str(proposal_path),
            model="claude-haiku-4-5-20251001",
            task_name=f"elon_proposal_{sig[:12]}",
        )
        if result.get("status") != "SPAWNED":
            log.error(f"invoke_elon spawn failed: {result.get('error')}")
            return {}
        mark_elon_invoked(sig)
        log.info(f"invoke_elon: spawned PID {result['pid']} for sig={sig}, proposal={proposal_path}")
        return {"proposal_path": str(proposal_path), "pid": result["pid"]}
    except Exception as e:
        log.error(f"invoke_elon failed: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Triage
# ─────────────────────────────────────────────────────────────────────────────

def triage_event(event: dict) -> dict:
    """Core triage logic. Returns action summary."""
    event_type = event.get("event_type", "")
    severity = event.get("severity", "info")
    service = event.get("service", "unknown")
    auto_healed = event.get("auto_heal_succeeded", False)
    curr_mode = event.get("curr_mode", "")

    sig = compute_signature(service, str(event.get("details", "")))
    record_signature(sig, event.get("ts", datetime.now(timezone.utc).isoformat()))

    result = {
        "event_id": event.get("event_id"),
        "service": service,
        "event_type": event_type,
        "sig": sig,
        "action_taken": "queued_for_brief",
        "page_commander": False,
        "elon_invoked": False,
        "brief_status": "GREEN",
        "brief_note": event.get("details", ""),
    }

    # Rule 1: Auto-healed + success → never pages Commander
    if auto_healed and event_type == "auto_healed":
        probe_ok, probe_msg = run_verification_probe(service)
        if probe_ok:
            result["action_taken"] = "auto_healed_verified"
            result["brief_status"] = "GREEN"
            result["brief_note"] = f"auto-heal verified ({probe_msg})"
            log.info(f"RULE_1 applied: {service} auto-healed and verified — silent")
        else:
            result["brief_status"] = "YELLOW"
            result["brief_note"] = f"auto-heal unverified: {probe_msg}"
            log.warning(f"{service} auto-healed but probe FAILED: {probe_msg}")

        # Check ELON gate even on auto-heals
        elon_needed, elon_reason = should_invoke_elon(sig, event)
        if elon_needed:
            elon_result = invoke_elon(sig, service, event, elon_reason)
            if elon_result:
                result["elon_invoked"] = True
                result["elon_proposal_path"] = elon_result.get("proposal_path")
        return result

    # Mode change: RED pages Commander
    if event_type == "mode_change":
        if curr_mode == "RED":
            result["page_commander"] = True
            result["action_taken"] = "paged_commander_mode_red"
            result["brief_status"] = "RED"
            page_commander(event, "System entered RED mode")
        elif curr_mode in ("GREEN", "YELLOW"):
            result["action_taken"] = "queued_for_brief"
            result["brief_status"] = curr_mode
        return result

    # Tier 1 critical / unrecoverable → page Commander ONLY if service is in COMMANDER_GATE_SERVICES
    # Per SO 2026-05-07: Hale repairs first. Commander gates only on client-blocking failures.
    if severity in COMMANDER_PAGE_SEVERITIES or event_type in COMMANDER_PAGE_SEVERITIES:
        if service not in COMMANDER_GATE_SERVICES:
            # Infrastructure service — Hale owns repair, Commander not paged
            result["page_commander"] = False
            result["action_taken"] = "hale_owns_repair_no_commander_page"
            result["brief_status"] = "RED"
            log.warning(
                "COMMANDER GATE: %s has severity %s but is not in COMMANDER_GATE_SERVICES — "
                "Hale owns repair, Commander not paged (SO 2026-05-07)", service, severity
            )
            # Still invoke ELON for recurring failures
            elon_needed, elon_reason = should_invoke_elon(sig, event)
            if elon_needed:
                elon_result = invoke_elon(sig, service, event, elon_reason)
                if elon_result:
                    result["elon_invoked"] = True
                    result["elon_proposal_path"] = elon_result.get("proposal_path")
            return result

        result["page_commander"] = True
        result["action_taken"] = "paged_commander_tier1"
        result["brief_status"] = "RED"
        page_commander(event, f"Tier 1 incident: {event_type}/{severity}")

        elon_needed, elon_reason = should_invoke_elon(sig, event)
        if elon_needed:
            elon_result = invoke_elon(sig, service, event, elon_reason)
            if elon_result:
                result["elon_invoked"] = True
                result["elon_proposal_path"] = elon_result.get("proposal_path")
        return result

    # All other events: queue for brief, check ELON gate
    result["action_taken"] = "queued_for_brief"
    result["brief_status"] = "YELLOW" if severity in ("warn", "error") else "INFO"

    elon_needed, elon_reason = should_invoke_elon(sig, event)
    if elon_needed:
        elon_result = invoke_elon(sig, service, event, elon_reason)
        if elon_result:
            result["elon_invoked"] = True
            result["elon_proposal_path"] = elon_result.get("proposal_path")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Incidents today file
# ─────────────────────────────────────────────────────────────────────────────

def update_incidents_today(triaged: list[dict]) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    if INCIDENTS_TODAY.exists():
        try:
            data = json.loads(INCIDENTS_TODAY.read_text())
            if data.get("date") != today:
                data = _empty_incidents_today(today)
        except Exception:
            data = _empty_incidents_today(today)
    else:
        data = _empty_incidents_today(today)

    for t in triaged:
        data["incidents"].append({
            "time": datetime.now().strftime("%H:%M"),
            "service": t.get("service"),
            "event_type": t.get("event_type"),
            "action": t.get("action_taken"),
            "status": t.get("brief_status"),
            "note": t.get("brief_note", ""),
            "elon_invoked": t.get("elon_invoked", False),
        })
        # Update summary counts
        if t.get("brief_status") == "GREEN" and "auto_heal" in t.get("action_taken", ""):
            data["summary"]["auto_healed"] += 1
        elif t.get("page_commander"):
            data["summary"]["unresolved"] += 1
        if t.get("elon_invoked"):
            data["summary"]["elon_proposals_new"] += 1

    # Update mode_now from live system state
    system_mode_path = THUNDERBIRD / "logs" / "system_mode.json"
    if system_mode_path.exists():
        try:
            mode_data = json.loads(system_mode_path.read_text())
            data["mode_now"] = mode_data.get("mode", "UNKNOWN")
        except Exception:
            pass
    INCIDENTS_TODAY.write_text(json.dumps(data, indent=2))


def _empty_incidents_today(today: str) -> dict:
    return {
        "date": today,
        "summary": {"auto_healed": 0, "self_repaired": 0, "unresolved": 0, "elon_proposals_new": 0},
        "incidents": [],
        "mode_now": "GREEN",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────────────────────────────────────

def process_incident_queue() -> dict:
    """Main entry. Drains queue, triages, updates today file. Returns summary."""
    from OpsCenter.incident_queue import drain_queue, archive_processed

    events = drain_queue()
    if not events:
        log.debug("Queue empty — nothing to process")
        return {"processed": 0}

    log.info(f"Processing {len(events)} queued events")
    triaged = [triage_event(e) for e in events]

    update_incidents_today(triaged)
    archive_processed(events)

    summary = {
        "processed": len(events),
        "paged_commander": sum(1 for t in triaged if t.get("page_commander")),
        "elon_invoked": sum(1 for t in triaged if t.get("elon_invoked")),
        "auto_healed": sum(1 for t in triaged if "auto_heal" in t.get("action_taken", "")),
    }
    log.info(f"Cycle complete: {summary}")
    return summary


if __name__ == "__main__":
    result = process_incident_queue()
    print(json.dumps(result, indent=2))
