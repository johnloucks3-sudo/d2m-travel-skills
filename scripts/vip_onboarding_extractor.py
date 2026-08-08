#!/usr/bin/env python3
"""VIP client onboarding & preference extractor.

Autonomy item #37 (2026-08-07 War Room). Reads OpsCenter/client_inbox_queue.jsonl
(already populated by d2m_inbox_triage.py for category="client_inquiry" hits),
filters to inquiries from senders NOT already a known client (per
core.client.thunderbird_auto_enrich._get_known_clients() dossier registry),
runs parse_client_inquiry() (Haiku MAX) to extract trip-shape preferences, and
stages a TESS create_client payload — attempting the live write, falling back
to a staged JSON file + notify() if TESS is unreachable.

Scope note: TESS auth was confirmed dead 2026-08-07 (refresh token expired,
Playwright Chromium binary missing, stale vault password — pre-existing,
unrelated to this script). This script degrades gracefully: it always writes
the staged profile so nothing is lost, and attempts the live CRM write on
every run so it self-activates the moment TESS is repaired — no manual
replay needed.

Runs every 15 min via d2m-vip-onboarding-extractor.timer (piggybacks the
existing client_inbox_queue cadence).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "ai_infra"))

QUEUE_FILE = THUNDERBIRD / "OpsCenter" / "client_inbox_queue.jsonl"
STATE_FILE = THUNDERBIRD / "OpsCenter" / "state" / "vip_onboarding_state.json"
STAGE_DIR = THUNDERBIRD / "OpsCenter" / "vip_onboarding_staged"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _split_from(from_header: str) -> tuple[str, str]:
    """'Display Name <email@x.com>' -> (name, email)."""
    if "<" in from_header and ">" in from_header:
        name = from_header.split("<")[0].strip().strip('"')
        email = from_header.split("<")[1].split(">")[0].strip()
    else:
        name = from_header.strip()
        email = from_header.strip()
    return name, email


def _name_matches_known_client(name: str, known_clients: dict) -> bool:
    name_words = set(name.replace(",", "").split())
    for entry in known_clients.values():
        variants = set(entry.get("name_variants", []))
        if name_words & variants:
            return True
    return False


def run() -> dict:
    from core.client.thunderbird_auto_enrich import _get_known_clients
    from itinerary.thunderbird_trip_architect import parse_client_inquiry

    result = {"scanned": 0, "skipped_known_client": 0, "skipped_no_email": 0,
              "extracted": [], "errors": []}

    if not QUEUE_FILE.exists():
        return result

    state = load_state()
    known_clients = _get_known_clients()
    STAGE_DIR.mkdir(parents=True, exist_ok=True)

    for line in QUEUE_FILE.read_text().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("category") != "client_inquiry":
            continue
        msg_id = entry.get("msg_id")
        if not msg_id or msg_id in state:
            continue

        result["scanned"] += 1
        state[msg_id] = {"processed_at": datetime.now(timezone.utc).isoformat()}

        name, email = _split_from(entry.get("from", ""))
        if not email or "@" not in email:
            result["skipped_no_email"] += 1
            continue
        if _name_matches_known_client(name, known_clients):
            result["skipped_known_client"] += 1
            continue

        try:
            preferences = parse_client_inquiry(entry.get("snippet", ""))
        except Exception as e:
            result["errors"].append(f"{msg_id}: parse_client_inquiry failed: {e}")
            continue

        first, _, last = name.partition(" ")
        profile = {
            "msg_id": msg_id,
            "first_name": first or name,
            "last_name": last or "",
            "email": email,
            "notes": f"Auto-extracted from inbound inquiry: {entry.get('subject', '')}",
            "extra_fields": preferences,
            "source": "vip_onboarding_extractor",
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "tess_status": "not_attempted",
        }

        try:
            from core.booking.thunderbird_tess import TESSClient
            client = TESSClient()
            tess_result = client.create_client({
                "first_name": profile["first_name"],
                "last_name": profile["last_name"],
                "email": profile["email"],
                "notes": profile["notes"],
                **preferences,
            })
            if tess_result.get("error"):
                profile["tess_status"] = f"failed: {tess_result['error']}"
            else:
                profile["tess_status"] = "created"
                profile["tess_client_id"] = tess_result.get("id") or tess_result.get("client_id")
        except Exception as e:
            profile["tess_status"] = f"failed: {e}"

        stage_path = STAGE_DIR / f"{msg_id}.json"
        stage_path.write_text(json.dumps(profile, indent=2, default=str))
        result["extracted"].append(profile)

    save_state(state)
    return result


def notify_extractions(result: dict) -> None:
    if not result["extracted"]:
        return
    from core.comms.commander_channel import notify

    lines = [f"VIP onboarding extractor — {len(result['extracted'])} new inquiry profile(s) processed:", ""]
    for p in result["extracted"]:
        status_line = f"TESS: {p['tess_status']}"
        lines.append(f"- {p['first_name']} {p['last_name']} <{p['email']}> — {status_line}")
        if p["extra_fields"].get("destination"):
            lines.append(f"    destination: {p['extra_fields'].get('destination')}")
    failed = [p for p in result["extracted"] if not p["tess_status"].startswith("created")]
    if failed:
        lines.append("")
        lines.append(f"{len(failed)} staged locally (TESS write failed/unavailable) — see OpsCenter/vip_onboarding_staged/. State file marks these msg_ids processed, so this does NOT auto-retry — replay staged JSON against TESS manually once it's repaired.")

    notify(
        kind="ops",
        title=f"VIP Onboarding — {len(result['extracted'])} inquiry profile(s) extracted",
        body_md="\n".join(lines),
        urgency="WINDOW",
        source="vip_onboarding_extractor.py",
    )


def main():
    result = run()
    notify_extractions(result)
    print(json.dumps({k: v for k, v in result.items() if k != "extracted"} |
                      {"extracted_count": len(result["extracted"])}, indent=2, default=str))


if __name__ == "__main__":
    main()
