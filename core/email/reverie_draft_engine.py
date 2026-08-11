#!/usr/bin/env python3
"""
reverie_draft_engine.py — REVERIE integration point for the client creative chain.

Given a client's REVERIE profile (from scripts/reverie_client_profile.py) and
basic destination/itinerary data, this module:

  1. Selects the matching opening-paragraph seed from
     templates/reverie_emotional_openings.md
  2. Builds a routing ticket for the existing creative chain (Reyes -> Luna ->
     Naia -> Dani -> TALON/JET -> WF-17) per CLAUDE.md's mandatory sequence.
  3. Logs the chosen pillar/traveler/evidence to the client dossier so the
     read persists across future touchpoints instead of being re-derived
     from scratch every time.

This module does NOT execute Luna/Naia/Dani. Per Failure A / Failure D in
Personas/hale_cos.md, routing and content generation in another domain
expert's lane are different jobs. The seed opening is a first input to the
narrative pass, not finished client copy — it must not go out unreviewed.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
from reverie_client_profile import profile_client, find_dossier_files  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OPENINGS_TEMPLATE = REPO_ROOT / "templates" / "reverie_emotional_openings.md"

# Matches "**PILLAR + Type**" entry headers in the openings template, capturing
# the pillar name, traveler type, and the paragraph that follows (up to the
# next "**" header or "---" section break).
ENTRY_RE = re.compile(
    r"\*\*(?:★\s*)?([A-Z][A-Z \'\.]+?)\s*\+\s*([A-Za-z]+)\s*(?:\(CANONICAL\))?\*\*\s*\n>\s*(.+?)(?=\n\n|\n---|\Z)",
    re.DOTALL,
)


def load_opening_library():
    """Parse templates/reverie_emotional_openings.md into {(pillar, type): paragraph}."""
    text = OPENINGS_TEMPLATE.read_text()
    library = {}
    for m in ENTRY_RE.finditer(text):
        pillar_raw, ttype_raw, paragraph = m.groups()
        pillar = pillar_raw.strip()
        ttype = ttype_raw.strip()
        paragraph = " ".join(line.strip().lstrip(">").strip() for line in paragraph.splitlines()).strip()
        library[(pillar, ttype)] = paragraph
    return library


def select_opening(pillar: str, traveler_type: str, library=None):
    """
    Return (paragraph, is_canonical, source_key) for a pillar/type pair.
    Falls back to a Negative-Space-compliant placeholder if either is UNKNOWN —
    it does not fabricate an emotional opening from nothing.
    """
    if library is None:
        library = load_opening_library()

    if pillar == "UNKNOWN" or traveler_type == "UNKNOWN":
        return (
            "[NO EMOTIONAL BRIEF AVAILABLE — dossier carried no confirmable pillar/traveler "
            "signal. Route an intake question to Dani before Reyes starts the chain; do not "
            "open with a generic register.]",
            False,
            None,
        )

    key = (pillar.upper(), traveler_type)
    if key in library:
        canonical_text = OPENINGS_TEMPLATE.read_text()
        entry_pos = canonical_text.find(f"{pillar.upper()} + {traveler_type}")
        is_canonical = "(CANONICAL)" in canonical_text[entry_pos:entry_pos + 200] if entry_pos != -1 else False
        return library[key], is_canonical, f"{pillar.upper()} + {traveler_type}"

    return (
        f"[No template entry found for {pillar} + {traveler_type} — check "
        f"templates/reverie_emotional_openings.md for a typo in pillar/type naming.]",
        False,
        None,
    )


def build_creative_chain_ticket(client_label: str, profile: dict, opening: str, destination_data: dict):
    """
    Construct the routing ticket that hands this off to the existing creative
    chain (Reyes -> Luna -> Naia -> Dani -> TALON/JET -> WF-17). This function
    stages the ticket; it does not invoke the domain-expert agents itself.
    """
    ticket = {
        "ticket_type": "REVERIE_CREATIVE_CHAIN_HANDOFF",
        "client": client_label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reverie_profile": {
            "primary_pillar": profile["primary_pillar"],
            "primary_confidence": profile["primary_confidence"],
            "secondary_pillar": profile["secondary_pillar"],
            "traveler_type": profile["traveler_type"],
            "traveler_confidence": profile["traveler_confidence"],
        },
        "destination_data": destination_data,
        "opening_seed": opening,
        "chain_steps": [
            {"step": 1, "owner": "Reyes (A8)", "action": "Experience layer — excursions, dining, accessibility, upsell flags. STAGED, awaiting execution.", "status": "PENDING"},
            {"step": 2, "owner": "Luna (A6)", "action": "Narrative pass. Receives opening_seed as first input, not finished copy — rewrite to client specifics.", "status": "PENDING"},
            {"step": 3, "owner": "Naia (EXEC)", "action": "Brand pass — tone, D2M markers, structure, language flags.", "status": "PENDING"},
            {"step": 4, "owner": "Dani (A3)", "action": "Client voice — final language pass.", "status": "PENDING"},
            {"step": 5, "owner": "TALON + JET", "action": "Quality gate — reader impact + fact/$$ verification on finished draft.", "status": "PENDING"},
            {"step": 6, "owner": "Hale (COS)", "action": "WF-17 routing review — draft to Gmail, Commander review label. Hale does not send.", "status": "PENDING"},
        ],
    }
    return ticket


DOSSIER_LOG_MARKER = "### REVERIE PROFILE LOG"


def log_pillar_to_dossier(dossier_path: Path, profile: dict, dry_run=False):
    """
    Append a dated REVERIE profile entry to the dossier body so the read
    persists for future touchpoints instead of being re-derived from scratch.
    Never overwrites prior entries — appends, so drift over time is visible.
    """
    text = dossier_path.read_text()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    evidence_lines = "\n".join(f"  - {e}" for e in profile["primary_evidence"][:2])
    entry = (
        f"\n\n{DOSSIER_LOG_MARKER} ({stamp})\n"
        f"- Primary: {profile['primary_pillar']} ({profile['primary_confidence']})\n"
        f"- Secondary: {profile['secondary_pillar']} ({profile['secondary_confidence']})\n"
        f"- Traveler type: {profile['traveler_type']} ({profile['traveler_confidence']})\n"
        f"- Evidence:\n{evidence_lines}\n"
        f"- Source: reverie_draft_engine.py automated read; Luna/Dani may override with direct client signal.\n"
    )

    if DOSSIER_LOG_MARKER in text:
        # Append a new dated entry after the last existing log block rather
        # than duplicating the marker section header every time.
        idx = text.rfind(DOSSIER_LOG_MARKER)
        end_of_block = text.find("\n\n", idx)
        end_of_block = end_of_block if end_of_block != -1 else len(text)
        new_text = text[:end_of_block] + "\n\n" + entry.strip() + "\n" + text[end_of_block:]
    else:
        new_text = text.rstrip() + entry + "\n"

    if dry_run:
        return entry
    dossier_path.write_text(new_text)
    return entry


def run(client_query: str, destination_data: dict = None, write_dossier=False, output_path: Path = None):
    destination_data = destination_data or {}
    paths = find_dossier_files(client_query)
    if not paths:
        raise SystemExit(f"No dossier files matched '{client_query}'")

    profile = profile_client(paths)
    opening, is_canonical, template_key = select_opening(
        profile["primary_pillar"], profile["traveler_type"]
    )
    ticket = build_creative_chain_ticket(client_query, profile, opening, destination_data)
    ticket["opening_is_canonical_template"] = is_canonical
    ticket["opening_template_key"] = template_key

    dossier_log_entry = None
    if write_dossier:
        primary_dossier = paths[0]
        dossier_log_entry = log_pillar_to_dossier(primary_dossier, profile)

    result = {
        "profile": profile,
        "ticket": ticket,
        "dossier_log_entry": dossier_log_entry,
    }

    if output_path:
        output_path.write_text(json.dumps(result, indent=2))

    # Post signal to staff_signal_bus for creative chain tracking
    try:
        from core.ai_infra.staff_signal_bus import post as post_signal
        pillar = profile.get("primary_pillar", "UNKNOWN")
        ttype = profile.get("traveler_type", "UNKNOWN")
        post_signal(
            from_persona="reyes",
            type="OPINE",
            subject=f"Creative Chain Staged: {client_query} — {pillar} / {ttype}",
            detail=f"Ticket generated for creative chain (Reyes -> Luna -> Naia -> Dani -> COS). Seed opening: {opening[:120]}...",
            priority="med",
        )
    except Exception:
        pass

    return result



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True, help="Client name substring to look up under dossiers/")
    ap.add_argument("--destination-json", help="Path to a JSON file of destination/itinerary data")
    ap.add_argument("--write-dossier", action="store_true", help="Append the profile log to the dossier file")
    ap.add_argument("--out", help="Write full result JSON to this path")
    args = ap.parse_args()

    destination_data = {}
    if args.destination_json:
        destination_data = json.loads(Path(args.destination_json).read_text())

    result = run(
        args.client,
        destination_data=destination_data,
        write_dossier=args.write_dossier,
        output_path=Path(args.out) if args.out else None,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
