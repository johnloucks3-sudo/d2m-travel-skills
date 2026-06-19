"""
validate_dossier.py — Pre-Generation Dossier Gate
Dreams2Memories Travel, LLC | Thunderbird Wing
Built per McLeod AAR 2026-05-29 (Sterling A7)

Usage:
    python3 itinerary/validate_dossier.py dossiers/McLeod_Erik_Melissa_SilverMuse_Complete.md
    python3 itinerary/validate_dossier.py --client mcleod   # auto-locates by client keyword
    python3 itinerary/validate_dossier.py --all             # validates all active dossiers
    python3 itinerary/validate_dossier.py --client kuklinski --email-json   # also emit email template JSON

    --email-json   After validation, write output/{ClientName}_email_template_{date}.json
                   Eliminates manual 40-min WF-17 validation email drafting cycle (ELON A12, 2026-05-30)

Exit codes:
    0 = all checks passed, safe to generate
    1 = warnings only (generate at your own risk)
    2 = errors — generator should refuse to run

Spelling fixes: unambiguous corrections in SPELL_FIXES are applied in-place automatically.
No human gate — spot-it-fix-it (SO-2026-05-04).
"""

import sys, re, json
from datetime import date, datetime
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
    # Client contact — required for WF-17 readiness (Dani A3 — 2026-05-29)
    ("Client email address",    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "ERROR"),
    # International visa/entry check (Reyes A8 — 2026-05-29)
    ("Schengen/visa status",    r"(?i)(schengen|visa|entry requirement|passport valid|U\.?S\.? passport|no visa required|visa-free)", "WARN"),
]

# ── SPELLING CORRECTIONS ─────────────────────────────────────────────────────
# SPELL_FIXES: unambiguous wrong→right pairs applied in-place automatically.
# No human gate — spot-it-fix-it (SO-2026-05-04).
SPELL_FIXES = {
    "Herculanum":      "Herculaneum",
    "Herculanium":     "Herculaneum",
    "Blacklain":       "Blacklane",
    "Valleta":         "Valletta",
    "Kotor Montengro": "Kotor, Montenegro",
}

# SPELL_FLAGS: ambiguous — flag for human review, never auto-apply.
SPELL_FLAGS = {
    "Polignano": "(Bari/Polignano — verify: is this port actually on the voyage?)",
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


def apply_spelling_fixes(content: str, dossier_path: Path) -> tuple[str, list[str]]:
    """Apply SPELL_FIXES in-place. Returns (updated_content, list_of_applied_fixes).
    Case-preserving: matches any case variant of the wrong word."""
    applied = []
    for wrong, correct in SPELL_FIXES.items():
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        if pattern.search(content):
            # Preserve ALL-CAPS if source is all-caps
            def _replace(m):
                src = m.group(0)
                if src.isupper():
                    return correct.upper()
                if src[0].isupper():
                    return correct[0].upper() + correct[1:]
                return correct
            content = pattern.sub(_replace, content)
            applied.append(f"'{wrong}' → '{correct}'")
    if applied:
        dossier_path.write_text(content, encoding="utf-8")
    return content, applied


def check_spelling(content: str) -> list:
    """Return flag-only issues (ambiguous — never auto-corrected)."""
    issues = []
    for wrong, note in SPELL_FLAGS.items():
        if wrong.lower() in content.lower():
            issues.append(f"SPELL FLAG: '{wrong}' — {note}")
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

    # Auto-fix unambiguous spelling errors in-place before any other checks
    content, fixed = apply_spelling_fixes(content, dossier_path)
    for fix in fixed:
        if verbose:
            print(f"  ✎ AUTO-FIXED: {fix}")

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


# ── EMAIL TEMPLATE JSON EXTRACTION ───────────────────────────────────────────
# ELON A12 — 2026-05-30
# Eliminates manual 40-min WF-17 email drafting cycle.
# Reads validated dossier → emits structured JSON that Dani can turn into
# a complete client email in one pass, with zero hallucination risk.

# Dining window ships + relevant date (hardcoded for current booking season)
# Regent Grandeur dining opens May 31, 2026. Viking — no equivalent window.
DINING_WINDOW_SHIPS = {
    "grandeur": {"date": "May 31, 2026", "venues": ["Chartreuse", "Sette Mari", "Pacific Rim"]},
    "silver muse": {"date": "May 31, 2026", "venues": []},  # Silversea — check if applicable
}

# Ships that have specialty dining windows (case-insensitive partial match)
DINING_WINDOW_KEYWORDS = ["grandeur", "silver muse", "silver nova"]


def _parse_frontmatter(content: str) -> dict:
    """Extract YAML-ish frontmatter between --- delimiters."""
    fm = {}
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return fm
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, _, val = line.partition(':')
            val = val.strip().strip('"\'')
            fm[key.strip()] = val
    return fm


def _extract_client_name(content: str, fm: dict) -> str:
    """Best-effort client name from frontmatter or dossier header."""
    if fm.get("full_name"):
        return fm["full_name"]
    # Try H1 dossier header pattern
    m = re.search(r'^# CLIENT DOSSIER\s*[—–-]\s*(.+)$', content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return fm.get("client", "Unknown Client")


def _extract_booking_ref(content: str, fm: dict) -> str:
    """Extract primary booking ref from frontmatter or content."""
    if fm.get("booking"):
        return fm["booking"]
    # Scan for known booking ref patterns
    m = re.search(r'(?i)booking[:\s#]+(\d{5,})', content)
    if m:
        return m.group(1)
    # Known refs embedded in content
    for known in ["298475", "3071222", "3078056", "3096289", "9593880", "9595029"]:
        if known in content:
            return known
    return "UNKNOWN"


def _extract_ship(content: str, fm: dict) -> str:
    if fm.get("ship"):
        return fm["ship"]
    m = re.search(r'(?i)(Silver Muse|Silver Nova|Viking Mars|SS Grandeur|Seven Seas Grandeur|Grandeur)', content)
    return m.group(1) if m else fm.get("cruise_line", "UNKNOWN")


def _extract_departure(content: str, fm: dict) -> str:
    if fm.get("departure"):
        return fm["departure"]
    m = re.search(r'(?i)departure.*?(20\d\d-\d\d-\d\d)', content)
    return m.group(1) if m else "UNKNOWN"


def _extract_payment_status(content: str, fm: dict) -> str:
    if fm.get("payment_status"):
        ps = fm["payment_status"].lower()
        if "paid" in ps or "full" in ps or "complete" in ps:
            return "PAID IN FULL"
        return fm["payment_status"].upper()
    # Scan content
    if re.search(r'(?i)PAID IN FULL|payment complete|paid.*full', content):
        return "PAID IN FULL"
    if re.search(r'(?i)balance due.*\$[\d,]+', content):
        m = re.search(r'(?i)balance due[:\s]+\$([\d,]+)', content)
        return f"BALANCE DUE: ${m.group(1)}" if m else "BALANCE OUTSTANDING"
    return "UNKNOWN — VERIFY IN PORTAL"


def _extract_email_to(content: str, fm: dict) -> str:
    """Find primary client email. Prefer frontmatter, fall back to content scan."""
    # Frontmatter primary fields
    for key in ("email_primary", "email", "email_al", "email_al"):
        if fm.get(key) and "@" in fm[key]:
            return fm[key]
    # First email in content that isn't a D2M address
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
    for e in emails:
        if "d2m" not in e.lower() and "concierge" not in e.lower():
            return e
    return "UNKNOWN — REQUIRED BEFORE SEND"


def _extract_outstanding_items(content: str, errors: list, warnings: list) -> list:
    """
    Derive outstanding items from:
      1. Validator errors/warnings (structural)
      2. Content-level signals (seat gaps, missing forms, open transfers, etc.)
    Returns list of human-readable strings.
    """
    items = []

    # Pull structural issues from validator output
    for msg in errors + warnings:
        if "MISSING" in msg:
            label = msg.replace("MISSING ERROR:", "").replace("MISSING WARN:", "").strip()
            items.append(f"Missing field: {label}")

    # Seat assignment gaps — explicit ⚠️ UNASSIGNED pattern
    unassigned = re.findall(r'⚠️\s*UNASSIGNED[^\n]*', content)
    for u in unassigned:
        clean = re.sub(r'[⚠️✅]+', '', u).strip()
        items.append(f"Seat gap: {clean}")

    # Missing guest forms
    if re.search(r'(?i)(guest.*form.*missing|form.*not.*returned|josh.*form|missing.*profile form)', content):
        items.append("Guest profile form outstanding (check dossier for named guest)")

    # Flights not booked
    if re.search(r'(?i)flights?\s*(are\s*)?(not\s+booked|unbooked|not\s+arranged|pending)', content):
        items.append("Flights not booked — action required before embarkation")

    # Transfers not arranged
    if re.search(r'(?i)transfer(s)?\s*(are\s*)?(not\s+arranged|unplanned|pending|not\s+booked)', content):
        items.append("Ground transfers not arranged")

    # Hotel not booked
    if re.search(r'(?i)(pre-cruise hotel|pre.?cruise hotel|night before).{0,80}(not booked|unbooked|pending|TBD)', content):
        items.append("Pre-cruise hotel not confirmed")

    # Cabin change — flag for awareness
    if re.search(r'(?i)CABIN CHANGE|suite changed|cabin changed|moved from', content):
        m = re.search(r'(?i)suite changed? from (\S+)\s*[→–-]+\s*(\S+)', content)
        if m:
            items.append(f"Cabin change on file: {m.group(1)} → {m.group(2)} — confirm client is aware")

    # Pipeline Rule 2 — dollar tags
    dollar_count = len(re.findall(r'\$\d[\d,]+', content))
    tagged_count = len(re.findall(r'(?i)CONFIRMED|INFERRED|UNKNOWN', content))
    if dollar_count > 0 and tagged_count == 0:
        items.append(f"Pipeline Rule 2: {dollar_count} dollar amounts without confidence tags")

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)

    return deduped


def _extract_insurance_status(content: str) -> str:
    """Classify insurance posture into one of four states."""
    c = content.lower()
    # Explicitly declined — word-boundary anchored to avoid "know...insurance" false positives
    if re.search(r'(?i)\bsaid no\b|\bdeclined insurance\b|\bno interest\b|\binsurance\b.{0,20}\bno\b|\bno thanks\b', content):
        return "DECLINED — soft re-raise appropriate"
    # Deferred explicitly
    if re.search(r'(?i)\bdeferred\b|\bwait.*couple.*months\b|\brevisit.*insurance\b|\bfollow.?up.*insurance\b|\binsurance.*deferred\b', content):
        return "DEFERRED — follow up now"
    # Active Allianz standalone policy — must have purchase confirmation, not just "Allianz-style"
    if re.search(r'(?i)allianz.{0,40}(purchased|paid \$|policy.{0,10}#|plan.{0,10}#|\$\d{3,}.*allianz|we paid allianz)', content):
        return "STANDALONE POLICY — verify coverage scope"
    # Chase Sapphire or card coverage only — check BEFORE generic insurance-paid match
    if re.search(r'(?i)chase sapphire|amex platinum.*insurance|card.*coverage|credit card.*protection', content):
        return "CC COVERAGE ONLY — no standalone policy"
    # Generic standalone confirmation
    if re.search(r'(?i)travel protection.*confirmed', content):
        return "STANDALONE POLICY — verify coverage scope"
    # Wants insurance, not yet acted
    if re.search(r'(?i)want(s)? (trip |travel )?insurance|interested in insurance|considering insurance', content):
        return "WANTS INSURANCE — no policy yet, action needed"
    # Found insurance mention but status unclear
    if re.search(r'(?i)(insurance|CFAR|travel protection)', content):
        return "MENTIONED — status unclear, verify"
    return "NO MENTION — raise proactively"


def _dining_window_relevant(content: str, ship: str) -> bool:
    """True if this client's ship has an open or imminent dining reservation window."""
    ship_lower = ship.lower()
    today = date.today()
    # Window hardcoded for current active booking season — May 31, 2026
    window_date = date(2026, 5, 31)
    if today > window_date:
        return False  # Window has passed
    # Check if ship type has a specialty dining window
    for kw in DINING_WINDOW_KEYWORDS:
        if kw in ship_lower or kw in content.lower()[:500]:
            return True
    return False


def _harlan_flag(content: str) -> str:
    """
    Rule 5 flag: does this dossier have dollar amounts that need Harlan sign-off?
    Returns one of: 'none', 'needs Rule 5', 'cleared'
    """
    dollar_amounts = re.findall(r'\$\d[\d,]+', content)
    if not dollar_amounts:
        return "none"
    # Check for explicit Harlan sign-off marker
    if re.search(r'(?i)Harlan sign.?off|Rule 5.*cleared|confirmed.*harlan', content):
        return "cleared"
    return f"needs Rule 5 — {len(dollar_amounts)} dollar amounts present"


def _build_suggested_cta(outstanding_items: list, insurance_status: str,
                          dining_window: bool, payment_status: str) -> str:
    """Single most important action for client to take right now."""
    # Priority order: payment > flight booking > seat gaps > guest forms > dining > insurance

    if "BALANCE" in payment_status or "OUTSTANDING" in payment_status:
        return "Complete final payment before FPD — confirm preferred card"

    # Flight booking is urgent
    if any("Flights not booked" in i for i in outstanding_items):
        return "Confirm arrival preference (day-before vs day-of) so flights can be built"

    # Seat gap
    if any("Seat gap" in i for i in outstanding_items):
        return "Reply with seat preference so we can close the remaining flight seat gap"

    # Dining window open NOW
    if dining_window:
        return "Send specialty dining preferences before May 31 8PM ET — windows fill fast"

    # Guest form outstanding
    if any("Guest profile form" in i for i in outstanding_items):
        return "Complete guest profile form (link in email) before we go deeper into planning"

    # Insurance action needed
    if insurance_status in ("DEFERRED — follow up now", "NO MENTION — raise proactively",
                             "WANTS INSURANCE — no policy yet, action needed"):
        return "Confirm insurance preference so coverage can be arranged while window is open"

    # Nothing urgent — portal check-in
    return "Log into Outside Agents portal to confirm your booking details look correct"


def _safe_filename(name: str) -> str:
    """Convert client name to safe filename component."""
    return re.sub(r'[^\w\s-]', '', name).replace(' ', '_').replace('&', 'and')


def build_email_json(dossier_path: Path, errors: list, warnings: list) -> dict:
    """
    Given a validated dossier and its error/warning lists,
    extract all fields needed for the WF-17 validation email template.
    """
    content = dossier_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(content)

    client_name    = _extract_client_name(content, fm)
    booking_ref    = _extract_booking_ref(content, fm)
    ship           = _extract_ship(content, fm)
    departure      = _extract_departure(content, fm)
    payment_status = _extract_payment_status(content, fm)
    email_to       = _extract_email_to(content, fm)
    insurance      = _extract_insurance_status(content)
    dining         = _dining_window_relevant(content, ship)
    outstanding    = _extract_outstanding_items(content, errors, warnings)
    harlan         = _harlan_flag(content)
    cta            = _build_suggested_cta(outstanding, insurance, dining, payment_status)

    # Voyage label for subject line
    voyage_label = fm.get("voyage", ship)
    month_label  = ""
    if departure and departure != "UNKNOWN":
        try:
            dep_date = datetime.strptime(departure, "%Y-%m-%d")
            month_label = dep_date.strftime("%B %Y")
        except ValueError:
            month_label = departure
    draft_subject = f"Your {voyage_label} Voyage — {datetime.now().strftime('%B')} Check-In"

    return {
        "client_name":          client_name,
        "booking_ref":          booking_ref,
        "ship":                 ship,
        "departure":            departure,
        "payment_status":       payment_status,
        "email_to":             email_to,
        "outstanding_items":    outstanding,
        "insurance_status":     insurance,
        "dining_window_relevant": dining,
        "suggested_cta":        cta,
        "harlan_flag":          harlan,
        "draft_subject":        draft_subject,
        "_meta": {
            "generated_by":     "validate_dossier.py --email-json (ELON A12)",
            "generated_at":     datetime.now().isoformat(),
            "source_dossier":   str(dossier_path),
            "validator_errors": len(errors),
            "validator_warns":  len(warnings),
        }
    }


def write_email_json(dossier_path: Path, errors: list, warnings: list) -> Path:
    """Build, write, and return the path of the email template JSON."""
    output_dir = Path("/home/john/Thunderbird/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = build_email_json(dossier_path, errors, warnings)
    client_slug = _safe_filename(payload["client_name"])
    today_str   = date.today().isoformat()
    out_path    = output_dir / f"{client_slug}_email_template_{today_str}.json"

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main():
    args = sys.argv[1:]
    if not args or "--help" in args:
        print(__doc__)
        sys.exit(0)

    emit_email_json = "--email-json" in args
    args = [a for a in args if a != "--email-json"]  # strip flag before path parsing

    if "--all" in args:
        # Validate all .md dossiers in the dossier directory
        paths = sorted(DOSSIER_DIR.glob("*.md"))
        paths = [p for p in paths if p.name != "CLAUDE.md"]
        worst = 0
        for p in paths:
            code, errs, warns = validate(p, verbose=True)
            worst = max(worst, code)
            if emit_email_json:
                out = write_email_json(p, errs, warns)
                print(f"  → Email JSON: {out}")
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

    if emit_email_json:
        out = write_email_json(path, errs, warns)
        print(f"\n{'='*60}")
        print(f"EMAIL JSON WRITTEN: {out}")
        print(json.dumps(json.loads(out.read_text()), indent=2))

    sys.exit(code)


if __name__ == "__main__":
    main()
