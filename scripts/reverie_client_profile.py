#!/usr/bin/env python3
"""
reverie_client_profile.py — REVERIE pillar/traveler-type profiler for a client dossier.

Determines the dominant REVERIE emotional pillar, secondary pillar, and traveler
type for a client at a specific moment, reading only what the dossier actually
contains. Honors SO-PIPELINE-INTEGRITY-20260528:

  - Every claim is tagged CONFIRMED / INFERRED / UNKNOWN (Rule 2).
  - If the dossier carries no emotional signal for a category, the profiler
    emits UNKNOWN and says so — it does not confabulate a pillar (Rule 1,
    Negative-Space Rule).
  - Every pillar/type pick carries the dossier evidence (quoted line + file)
    that drove it, so the pick is demonstrably defensible, not asserted.

This is a heuristic reader (keyword + structural signal scoring), not an LLM
classifier — it stays fast, deterministic, and PII-safe to run locally. Wire a
Sonnet pass in front of it later if freeform client correspondence needs
deeper reading; that pass must stay on the PII-cleared path (never OpenCode/
DeepSeek — see CLAUDE.md PII Fence).

Usage:
    python3 scripts/reverie_client_profile.py dossiers/Furlow_Regent_3071222.md
    python3 scripts/reverie_client_profile.py --client Kuklinski
    python3 scripts/reverie_client_profile.py dossiers/*.md --json
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

DOSSIERS_DIR = Path(__file__).resolve().parent.parent / "dossiers"

PILLARS = [
    "THE RETURN",
    "HELD",
    "WITNESSED",
    "EARNED",
    "THE DREAM THAT HAS A DATE",
    "DEPTH",
    "TOGETHER",
]

TRAVELER_TYPES = ["Achiever", "Curator", "Connector", "Escapist", "Witness", "Celebrant"]

# ---------------------------------------------------------------------------
# Keyword lexicons. Each entry: (compiled regex, weight, label for evidence)
# Weight 1 = soft textual tell. Structural signals are scored separately at
# weight 3 (see structural_signals()) because a dossier FACT (e.g. "3 couples
# booked as one group") is more defensible than a loose keyword match.
# ---------------------------------------------------------------------------

PILLAR_KEYWORDS = {
    "THE RETURN": [
        r"who (?:we|i|they) used to be",
        r"before (?:life|work|the kids)",
        r"haven'?t (?:traveled|been) like this in years",
        r"remember when",
        r"back to (?:who|the person)",
    ],
    "HELD": [
        r"trust you",
        r"whatever you think(?:'s| is)? best",
        r"book it",
        r"don'?t want to think about (?:any of )?(?:it|this|logistics)",
        r"handle (?:it|everything|all of it)",
        r"just need (?:to )?(?:not think|a break|to disconnect)",
    ],
    "WITNESSED": [
        r"life milestone",
        r"milestone (?:trip|voyage|celebration|birthday|anniversary)",
        r"we'?ve always wanted",
        r"deserve(?:s)? (?:this|it)",
        r"special[- ]occasion",
        r"one of a kind",
    ],
    "EARNED": [
        r"retir(?:e|ed|ement)",
        r"reward(?:ing)? (?:ourselves|myself|yourself)",
        r"saved (?:for|up) (?:years|this)",
        r"finally (?:doing|going|happening)",
        r"after years of",
        r"earned (?:this|it)",
    ],
    "THE DREAM THAT HAS A DATE": [
        r"someday",
        r"always wanted to",
        r"dream trip",
        r"one day,? (?:we|i)'?ll",
        r"countdown",
        r"finally (?:has|got|has a) date",
    ],
    "DEPTH": [
        r"not (?:the|just a) tourist",
        r"off[- ]the[- ]beaten[- ]path",
        r"authentic",
        r"real(?:ly)? (?:local|understand)",
        r"more than (?:the|a) (?:highlights|guidebook)",
    ],
    "TOGETHER": [
        r"reunion",
        r"grandchildren",
        r"family trip",
        r"friends? (?:group|celebrating)",
        r"time together",
    ],
}

TRAVELER_KEYWORDS = {
    "Achiever": [
        r"never (?:really )?traveled like this",
        r"is this too much",
        r"first time (?:doing|traveling) (?:this|like this)",
    ],
    "Curator": [
        r"40\+? countries",
        r"named a specific hotel",
        r"opinion about cruise lines",
        r"cabin categor(?:y|ies)",
    ],
    "Connector": [
        r"my (?:husband|wife|mother-in-law|father-in-law)",
        r"kids have never",
        r"the group (?:needs|wants)",
        r"everyone (?:happy|comfortable)",
    ],
    "Escapist": [
        r"just need to (?:not think|escape|get away)",
        r"whatever you think is best",
        r"book it,? i trust you",
    ],
    "Witness": [
        r"before it (?:changes|goes|disappears)",
        r"conservation",
        r"climate",
        r"last chance to see",
    ],
    "Celebrant": [
        r"anniversary",
        r"retir(?:ed|ement)",
        r"we made it",
        r"recovery",
        r"this is our \d",
    ],
}

CONFIRMED_OCCASION_RE = re.compile(
    r"(\d{1,3}(?:st|nd|rd|th)\s+anniversary|honeymoon|retirement (?:trip|voyage|cruise))",
    re.IGNORECASE,
)


def load_dossier(path: Path):
    """Split frontmatter (YAML) from markdown body. Tolerant of missing yaml lib."""
    text = path.read_text(errors="ignore")
    frontmatter = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text, body = parts[1], parts[2]
            if yaml:
                try:
                    frontmatter = yaml.safe_load(fm_text) or {}
                except yaml.YAMLError:
                    frontmatter = {}
    return frontmatter, body, text


def find_dossier_files(client_query: str):
    pattern = f"*{client_query}*"
    matches = sorted(DOSSIERS_DIR.glob(pattern + ".md"))
    return matches


def structural_signals(frontmatter: dict, body: str, filename: str):
    """
    Facts derivable from dossier STRUCTURE (not prose sentiment). Scored at
    weight 3 — a booking-count fact is more defensible than a keyword hit.
    Returns list of (pillar_or_type, weight, evidence_string).
    """
    signals = []

    # Multi-booking / repeat-client signal -> Curator (DEPTH+WITNESSED per architecture doc)
    booking_ship_keys = [k for k in frontmatter if re.match(r"booking_\d+_ship$", k)]
    if len(booking_ship_keys) >= 3:
        ships = ", ".join(str(frontmatter[k]) for k in sorted(booking_ship_keys))
        ev = f"{len(booking_ship_keys)} active bookings across cruise lines ({ships}) — {filename} frontmatter"
        signals.append(("DEPTH", 3, ev))
        signals.append(("WITNESSED", 2, ev))
        signals.append(("Curator", 3, ev))
    elif len(booking_ship_keys) == 2:
        ev = f"2 active bookings on file — {filename} frontmatter"
        signals.append(("Curator", 1, ev))

    note = str(frontmatter.get("note", ""))
    if re.search(r"best client", note, re.IGNORECASE):
        signals.append(("WITNESSED", 1, f'frontmatter note: "{note}" — {filename}'))

    # Group / multi-couple booking -> TOGETHER + Connector
    couple_rows = re.findall(
        r"^\|\s*\*\*([^*|]+&[^*|]+)\*\*\s*\|", body, re.MULTILINE
    )
    if len(couple_rows) >= 2:
        names = "; ".join(c.strip() for c in couple_rows)
        ev = f"{len(couple_rows)} couples booked as one group ({names}) — {filename} COUPLES table"
        signals.append(("TOGETHER", 3, ev))
        signals.append(("Connector", 3, ev))

    group_field = str(frontmatter.get("group", ""))
    if re.search(r"\d+\s+couples", group_field, re.IGNORECASE):
        signals.append(("TOGETHER", 2, f'frontmatter group: "{group_field}" — {filename}'))
        signals.append(("Connector", 2, f'frontmatter group: "{group_field}" — {filename}'))

    # Explicit special-occasion request logged in dossier body -> WITNESSED/Celebrant
    occ_match = re.search(r"(special[- ]occasion request[^\n]*)", body, re.IGNORECASE)
    if occ_match:
        ev = f'"{occ_match.group(1).strip()}" — {filename}'
        signals.append(("WITNESSED", 2, ev))
        signals.append(("Celebrant", 2, ev))

    confirmed = CONFIRMED_OCCASION_RE.search(body)
    if confirmed:
        ev = f'explicit occasion stated: "{confirmed.group(1)}" — {filename}'
        signals.append(("__CONFIRMED_WITNESSED__", 5, ev))
        signals.append(("__CONFIRMED_CELEBRANT__", 5, ev))

    # Payment discipline (paid in full ahead of FPD) -> soft EARNED signal
    if re.search(r"paid.{0,20}(?:ahead|early|in full)", body, re.IGNORECASE):
        pass  # too weak/common to score alone; left as a documented non-signal

    return signals


TABLE_HEADER_RE = re.compile(r"^\s*\|\s*(?:date|item|element|category|milestone)\s*\|", re.IGNORECASE)
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[-\s|:]+\|\s*$")
# Lines where the keyword names an ABSENCE (a data-collection gap) rather than
# a client tell must not score — "anniversary: not captured" is not a WITNESSED
# signal, it is the opposite: we don't know yet.
NEGATION_RE = re.compile(
    r"not captured|gap to fill|not (?:yet )?(?:known|confirmed|on file)|tbd|n/a|unknown|"
    r"declined|do not (?:raise|mention)|capture (?:furlow|client)|ask (?:missy|client)|"
    r"request when appropriate",
    re.IGNORECASE,
)


def keyword_signals(body: str, lexicon: dict, filename: str):
    signals = []
    lines = body.splitlines()
    for label, patterns in lexicon.items():
        for pat in patterns:
            for i, line in enumerate(lines):
                if TABLE_HEADER_RE.match(line) or TABLE_SEPARATOR_RE.match(line):
                    continue
                if NEGATION_RE.search(line):
                    continue
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    ev = f'"{line.strip()[:140]}" — {filename}:{i+1}'
                    signals.append((label, 1, ev))
    return signals


def score_and_rank(signals, categories):
    scores = {c: 0 for c in categories}
    evidence = {c: [] for c in categories}
    for label, weight, ev in signals:
        confirmed = label.startswith("__CONFIRMED_")
        key = label.replace("__CONFIRMED_", "").rstrip("__")
        if key not in scores:
            continue
        scores[key] += weight
        evidence[key].append((ev, "CONFIRMED" if confirmed else None))
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return ranked, evidence


def confidence_for(category, score, evidence_list, has_confirmed):
    if score <= 0:
        return "UNKNOWN"
    if has_confirmed:
        return "CONFIRMED"
    return "INFERRED"


def profile_client(paths):
    all_signals_pillar = []
    all_signals_traveler = []
    filenames = []
    for path in paths:
        frontmatter, body, _ = load_dossier(path)
        fname = path.name
        filenames.append(fname)
        all_signals_pillar += structural_signals(frontmatter, body, fname)
        all_signals_pillar += keyword_signals(body, PILLAR_KEYWORDS, fname)
        all_signals_traveler += structural_signals(frontmatter, body, fname)
        all_signals_traveler += keyword_signals(body, TRAVELER_KEYWORDS, fname)

    pillar_ranked, pillar_evidence = score_and_rank(all_signals_pillar, PILLARS)
    traveler_ranked, traveler_evidence = score_and_rank(all_signals_traveler, TRAVELER_TYPES)

    def confirmed_flag(evlist):
        return any(tag == "CONFIRMED" for _, tag in evlist)

    result = {"source_files": filenames}

    # Primary / secondary pillar
    primary_pillar, primary_score = pillar_ranked[0]
    secondary_pillar, secondary_score = pillar_ranked[1] if len(pillar_ranked) > 1 else (None, 0)

    primary_conf = confidence_for(
        primary_pillar, primary_score, pillar_evidence[primary_pillar],
        confirmed_flag(pillar_evidence[primary_pillar]),
    )
    result["primary_pillar"] = primary_pillar if primary_score > 0 else "UNKNOWN"
    result["primary_confidence"] = primary_conf
    result["primary_evidence"] = (
        [ev for ev, _ in pillar_evidence[primary_pillar]][:3]
        if primary_score > 0
        else ["No emotional or structural signal found in dossier for any pillar."]
    )

    if secondary_score > 0:
        secondary_conf = confidence_for(
            secondary_pillar, secondary_score, pillar_evidence[secondary_pillar],
            confirmed_flag(pillar_evidence[secondary_pillar]),
        )
        result["secondary_pillar"] = secondary_pillar
        result["secondary_confidence"] = secondary_conf
        result["secondary_evidence"] = [ev for ev, _ in pillar_evidence[secondary_pillar]][:3]
    else:
        result["secondary_pillar"] = "none"
        result["secondary_confidence"] = "UNKNOWN"
        result["secondary_evidence"] = []

    # Traveler type
    primary_type, type_score = traveler_ranked[0]
    result["traveler_type"] = primary_type if type_score > 0 else "UNKNOWN"
    result["traveler_confidence"] = confidence_for(
        primary_type, type_score, traveler_evidence[primary_type],
        confirmed_flag(traveler_evidence[primary_type]),
    )
    result["traveler_evidence"] = (
        [ev for ev, _ in traveler_evidence[primary_type]][:3]
        if type_score > 0
        else ["No traveler-type tell found in dossier — ask at next touchpoint."]
    )

    result["raw_pillar_scores"] = {k: v for k, v in pillar_ranked}
    result["raw_traveler_scores"] = {k: v for k, v in traveler_ranked}

    if result["primary_pillar"] == "UNKNOWN" or result["traveler_confidence"] == "UNKNOWN":
        result["notes"] = (
            "Negative-Space Rule applied: dossier lacks explicit emotional tells for one or "
            "more categories. Do not force a pillar for client copy — route an intake question "
            "to Dani/Reyes before the emotional brief is finalized."
        )
    else:
        result["notes"] = ""

    return result


def format_summary(client_label, result):
    lines = [f"{client_label}", "=" * len(client_label)]
    lines.append(
        f"Primary:   {result['primary_pillar']} ({result['primary_confidence']})"
    )
    for ev in result["primary_evidence"]:
        lines.append(f"           - {ev}")
    lines.append(
        f"Secondary: {result['secondary_pillar']} ({result['secondary_confidence']})"
    )
    for ev in result["secondary_evidence"]:
        lines.append(f"           - {ev}")
    lines.append(
        f"Traveler:  {result['traveler_type']} ({result['traveler_confidence']})"
    )
    for ev in result["traveler_evidence"]:
        lines.append(f"           - {ev}")
    if result["notes"]:
        lines.append(f"NOTE: {result['notes']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier_paths", nargs="*", help="One or more dossier .md files (same client's files grouped into one profile)")
    ap.add_argument("--client", help="Client name substring to look up under dossiers/")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of human summary")
    args = ap.parse_args()

    if args.client:
        paths = find_dossier_files(args.client)
        if not paths:
            print(f"No dossier files matched '{args.client}' under {DOSSIERS_DIR}", file=sys.stderr)
            sys.exit(1)
        label = args.client
    elif args.dossier_paths:
        expanded = []
        for p in args.dossier_paths:
            expanded += [Path(x) for x in glob.glob(p)] if any(c in p for c in "*?[") else [Path(p)]
        paths = expanded
        label = paths[0].stem if paths else "client"
    else:
        ap.print_help()
        sys.exit(1)

    result = profile_client(paths)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_summary(label, result))
        print()
        print("Example output-line format:")
        sec = result["secondary_pillar"]
        sec_str = f" + {sec.title()} (secondary)" if sec != "none" else ""
        print(
            f'  "{result["primary_pillar"].title()} (primary){sec_str}, '
            f'{result["traveler_type"]} traveler"'
        )


if __name__ == "__main__":
    main()
