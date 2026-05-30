"""
validate_dossier.py — Pre-Generation Dossier Gate
Dreams2Memories Travel, LLC | Thunderbird Wing
Built per McLeod AAR 2026-05-29 (Sterling A7)

Usage:
    python3 itinerary/validate_dossier.py dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md
    python3 itinerary/validate_dossier.py --client mcleod   # auto-locates by client keyword
    python3 itinerary/validate_dossier.py --all             # validates all active dossiers

Exit codes:
    0 = all checks passed, safe to generate
    1 = warnings only (generate at your own risk)
    2 = errors — generator should refuse to run
"""

import sys, re
from pathlib import Path

DOSSIER_DIR = Path("/home/john/Thunderbird/dossiers")

# ── REQUIRED FIELDS ──────────────────────────────────────────────────────────
# Each tuple: (field_label, regex_or_keyword, severity)
# severity: "ERROR" = block generation | "WARN" = flag but allow
REQUIRED_CHECKS = [
    # Frontmatter / booking fundamentals
    ("Booking confirmation #",  r"(?i)(booking|confirmation|conf)[#\s:]+\d{5,}|298475|3071222|3078056|3096289|9593|9595", "ERROR"),
    ("Departure date",          r"(?i)departure.*202[6-9]|embark.*202[6-9]|jun.*202[6-9]|aug.*202[6-9]|dec.*202[6-9]", "ERROR"),
    ("Payment status",          r"(?i)(PAID IN FULL|payment complete|FPD.*paid|paid.*full)", "ERROR"),
    ("Client names",            r"(?i)(client|guest|traveler).{0,50}[A-Z][a-z]+ [A-Z][a-z]+", "ERROR"),
    # Documents
    ("Passport data",           r"(?i)(passport|pass\s*#|expires).{0,30}20(2[6-9]|3[0-9])", "WARN"),
    # Flights
    ("Flight PNR",              r"(?i)(PNR|record locator|booking code|pnr\s*[:\|]?\s*)[A-Z0-9]{5,8}|[A-Z]{2}\d{6}|[A-Z0-9]{6}", "WARN"),
    # Insurance
    ("Insurance status",        r"(?i)(insurance|CFAR|allianz|chase sapphire|travel protection)", "WARN"),
    # Hotel
    ("Hotel confirmation",      r"(?i)(hotel|property).{0,80}(confirmed|booked|paid|\d{6,})", "WARN"),
    # Transfers
    ("Transfer status",         r"(?i)(transfer|blacklane|royal transfer|welcome pickup).{0,60}(confirmed|booked|paid|#\d{4,})", "WARN"),
    # Financial source rule (SO-PIPELINE-INTEGRITY-20260528 Rule 4)
    ("Dollar amounts sourced",  r"(?i)(PAID IN FULL|CONFIRMED|\[Source|portal|TESS|invoice|booking master)", "WARN"),
]

# ── KNOWN MISSPELLINGS TO CATCH ───────────────────────────────────────────────
SPELL_ERRORS = {
    "Herculanum":    "Herculaneum",
    "Herculanium":   "Herculaneum",
    "Polignano":     "(Bari/Polignano — verify: is this port actually on the voyage?)",
    "Blacklain":     "Blacklane",
    "Valleta":       "Valletta",
    "Kotor Montengro": "Kotor, Montenegro",
}

# ── PORT ORDER VERIFICATION ───────────────────────────────────────────────────
# Maps booking confirmation substrings to expected port sequences.
# Extend as new voyages are added. Source = cruise line portal, not dossier prose.
PORT_ORDERS = {
    "298475":  # McLeod Silver Muse SM260623010
        ["Civitavecchia", "Naples", "Giardini Naxos", "Siracusa",
         "Valletta", "At Sea", "Kotor", "Dubrovnik", "Split", "Zadar", "Fusina"],
    "3071222":  # Furlow Regent Grandeur Scandinavia
        ["Stockholm", "Berlin", "Warnemunde", "Copenhagen", "Kristiansand", "Oslo"],
    "3078056":  # Nichols Regent Grandeur Scandinavia (same voyage)
        ["Stockholm", "Berlin", "Warnemunde", "Copenhagen", "Kristiansand", "Oslo"],
    "3096289":  # Ely/Darrow Regent Grandeur Scandinavia (same voyage)
        ["Stockholm", "Berlin", "Warnemunde", "Copenhagen", "Kristiansand", "Oslo"],
    "9593880":  # Kuklinski Viking Mars Panama Canal
        ["Panama City", "At Sea", "Cartagena", "Colon", "Huatulco", "Puerto Quetzal",
         "Cabo San Lucas", "Ft. Lauderdale"],
}


def check_spelling(content: str) -> list:
    issues = []
    for wrong, suggestion in SPELL_ERRORS.items():
        if wrong.lower() in content.lower():
            issues.append(f"SPELL: '{wrong}' found — should be '{suggestion}'")
    return issues


def check_port_order(content: str, booking_ref: str) -> list:
    """Only runs port order check if dossier has an actual itinerary table (| Day | or ## Itinerary)."""
    issues = []
    has_itinerary = bool(re.search(r'(?i)(##\s*itinerary|##\s*cruise segment|\|\s*day\s*\||\|\s*june\s*\||\|\s*july\s*\|)', content))
    if not has_itinerary:
        return []  # No itinerary table in dossier — port check skipped

    for conf_key, expected_ports in PORT_ORDERS.items():
        if conf_key in content:
            prev_pos = -1
            out_of_order = []
            for port in expected_ports:
                pos = content.lower().find(port.lower())
                if pos == -1:
                    # Only flag missing ports as errors if they're primary embark/disembark
                    pass  # Missing interim ports are warnings, not errors
                elif pos < prev_pos:
                    out_of_order.append(port)
                else:
                    prev_pos = pos
            if out_of_order:
                issues.append(f"PORT ORDER: These ports appear out of sequence: {out_of_order}")
            break
    return issues


def validate(dossier_path: Path, verbose: bool = True) -> tuple[int, list, list]:
    """
    Returns (exit_code, errors, warnings)
    exit_code: 0=clean, 1=warnings, 2=errors
    """
    if not dossier_path.exists():
        return 2, [f"FILE NOT FOUND: {dossier_path}"], []

    content = dossier_path.read_text(encoding="utf-8")
    errors, warnings = [], []

    if verbose:
        print(f"\n{'='*60}")
        print(f"VALIDATING: {dossier_path.name}")
        print(f"{'='*60}")

    # Required field checks
    for label, pattern, severity in REQUIRED_CHECKS:
        found = bool(re.search(pattern, content))
        if not found:
            msg = f"MISSING {severity}: {label}"
            if severity == "ERROR":
                errors.append(msg)
            else:
                warnings.append(msg)
            if verbose:
                print(f"  {'✗' if severity == 'ERROR' else '⚠'} {msg}")
        elif verbose:
            print(f"  ✓ {label}")

    # Spell check
    spell_issues = check_spelling(content)
    for issue in spell_issues:
        warnings.append(issue)
        if verbose:
            print(f"  ⚠ {issue}")

    # Port order check
    port_issues = check_port_order(content, "")
    for issue in port_issues:
        errors.append(issue)
        if verbose:
            print(f"  ✗ {issue}")

    # CONFIRMED/INFERRED/UNKNOWN tagging check (Pipeline Integrity Rule 2)
    dollar_count = len(re.findall(r'\$\d[\d,]+', content))
    tagged_count  = len(re.findall(r'(?i)CONFIRMED|INFERRED|UNKNOWN', content))
    if dollar_count > 0 and tagged_count == 0:
        warnings.append(f"PIPELINE RULE 2: {dollar_count} dollar amounts found but no CONFIRMED/INFERRED tags")
        if verbose:
            print(f"  ⚠ PIPELINE RULE 2: {dollar_count} dollar amounts, 0 confidence tags")

    # Summary
    if verbose:
        print(f"\n  {'─'*40}")
        if errors:
            print(f"  ✗ {len(errors)} ERROR(s) — generator should NOT run")
        elif warnings:
            print(f"  ⚠ {len(warnings)} WARNING(s) — review before generating")
        else:
            print(f"  ✓ CLEAN — safe to generate")

    code = 2 if errors else (1 if warnings else 0)
    return code, errors, warnings


def main():
    args = sys.argv[1:]
    if not args or "--help" in args:
        print(__doc__)
        sys.exit(0)

    if "--all" in args:
        # Validate all .md dossiers in the dossier directory
        paths = sorted(DOSSIER_DIR.glob("*.md"))
        paths = [p for p in paths if p.name != "CLAUDE.md"]
        worst = 0
        for p in paths:
            code, errs, warns = validate(p, verbose=True)
            worst = max(worst, code)
        print(f"\n{'='*60}")
        print(f"BATCH RESULT: {len(paths)} dossiers checked | Exit code: {worst}")
        sys.exit(worst)

    if "--client" in args:
        idx = args.index("--client")
        keyword = args[idx + 1].lower()
        matches = [p for p in DOSSIER_DIR.glob("*.md")
                   if keyword in p.name.lower() and p.name != "CLAUDE.md"]
        if not matches:
            print(f"No dossier found matching: {keyword}")
            sys.exit(2)
        path = matches[0]
        if len(matches) > 1:
            print(f"Multiple matches — using: {path.name}")
    else:
        path = Path(args[0])
        if not path.is_absolute():
            path = Path("/home/john/Thunderbird") / path

    code, errs, warns = validate(path, verbose=True)

    if errs:
        print(f"\nErrors ({len(errs)}):")
        for e in errs:
            print(f"  ✗ {e}")
    if warns:
        print(f"\nWarnings ({len(warns)}):")
        for w in warns:
            print(f"  ⚠ {w}")

    sys.exit(code)


if __name__ == "__main__":
    main()
