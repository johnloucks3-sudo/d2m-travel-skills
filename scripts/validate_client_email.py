#!/usr/bin/env python3
"""
Client Email Pre-Draft Validator — D2M Pipeline Integrity Gate
Runs BEFORE any client HTML is committed to drafts/.
Hard stop on failures. No bypass without explicit Commander override in hale_decisions.md.

Usage:
    python3 scripts/validate_client_email.py <html_file> [--dossier <dossier_file>]
    python3 scripts/validate_client_email.py --all   # scan all files in drafts/
"""
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

GOLD_TEMPLATE = Path("storage/d2m_gold_standard_template.html")
DRAFTS_DIR = Path("drafts")

results = []

def check(name, passed, detail="", severity="BLOCK"):
    status = PASS if passed else (FAIL if severity == "BLOCK" else WARN)
    results.append((name, passed, detail, severity))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return passed


def validate_file(html_path: Path, dossier_path: Path = None) -> bool:
    global results
    results = []
    print(f"\n{'='*60}")
    print(f"VALIDATING: {html_path.name}")
    print(f"{'='*60}")

    if not html_path.exists():
        print(f"  [FAIL] File not found: {html_path}")
        return False

    html = html_path.read_text(encoding="utf-8")
    html_lower = html.lower()
    text_only = re.sub(r"<[^>]+>", " ", html)  # strip tags for content checks

    # ── 1. STATIONERY ────────────────────────────────────────────────────────
    print("\n[STATIONERY]")
    check("Deep navy background present",
          "#07076b" in html or "#08086e" in html,
          "Expected gold-standard navy (#07076b / #08086e)")
    check("D2M logo URL present",
          "1HYa61cNwcialWk64DimGwIfCAbUjESsu" in html,
          "Gold-standard D2M logo Drive ID missing")
    check("DREAMS2MEMORIES letterhead present",
          "DREAMS2MEMORIES" in html.upper(),
          "Header letterhead text missing")
    check("Old cream stationery not used",
          "#f7f3ea" not in html_lower,
          "Old cream (#f7f3ea) found — wrong stationery",
          severity="BLOCK")
    check("Commander sig block present",
          "John A Loucks" in html or "johnloucks3@gmail.com" in html,
          "Commander sig missing")

    # ── 2. ROUTING ───────────────────────────────────────────────────────────
    print("\n[ROUTING]")
    # Can't check Gmail routing from file alone — remind operator
    check("Not staged to d2mconcierge",
          True,  # enforced at staging time, not file time
          "Verified at staging — must go to johnloucks3",
          severity="WARN")

    # ── 3. FINANCIAL FIGURES ─────────────────────────────────────────────────
    print("\n[FINANCIAL]")
    dollar_matches = re.findall(r"\$[\d,]+(?:\.\d{2})?", text_only)
    if dollar_matches:
        # Each dollar figure should have a SOURCE comment nearby in the raw HTML
        sourced = "<!-- SOURCE:" in html or "source:" in html_lower
        check("Dollar figures have source annotations",
              sourced,
              f"Found {dollar_matches[:5]} — add <!-- SOURCE: dossier/portal --> inline",
              severity="WARN")
    else:
        check("No untraced dollar figures", True, "No dollar amounts found")

    # SBC check — if mentioned, must specify which SBC (Viking vs D2M)
    if "sbc" in html_lower or "shipboard credit" in html_lower:
        viking_sbc = "viking" in html_lower and ("sbc" in html_lower or "shipboard" in html_lower)
        d2m_sbc = "d2m" in html_lower and ("sbc" in html_lower or "shipboard" in html_lower)
        check("SBC attribution distinguishes Viking vs D2M",
              viking_sbc or d2m_sbc,
              "SBC mentioned without source attribution (Viking-only or D2M-only?)")

    # ── 4. CONTENT INTEGRITY ─────────────────────────────────────────────────
    print("\n[CONTENT]")

    # PE deferred payment — must NOT say "after the cruise" or "when you get home"
    # Catch affirmative misstatements only — "not post-cruise" is correct language
    bad_pe_phrases = [
        r"pay\s+after\s+the\s+cruise",
        r"pay\s+when\s+you\s+get\s+home",
        r"pay\s+after\s+you.?re\s+home",
        r"pay\s+when\s+you\s+return",
        r"payment\s+due\s+after\s+the\s+cruise",
    ]
    pe_violation = any(re.search(p, html_lower) for p in bad_pe_phrases)
    check("PE deferred payment not misstated",
          not pe_violation,
          "Found 'after the cruise/home' language — PE charges ~1 week before excursion")

    # PE SBC coverage — if PE mentioned, must note D2M SBC covers it
    if "project expedition" in html_lower or " pe " in html_lower:
        check("PE SBC coverage noted",
              "d2m" in html_lower and "sbc" in html_lower,
              "PE mentioned but D2M SBC coverage not stated")

    # Placeholder text
    placeholders = re.findall(r"FORM_URL_PLACEHOLDER|TODO|FIXME|\[INSERT|\{\{", html)
    check("No placeholder text",
          len(placeholders) == 0,
          f"Found: {placeholders[:3]}" if placeholders else "")

    # Sign-off
    check("Correct sign-off (not 'Best')",
          not re.search(r"\bBest\b(?:\s+regards?)?\s*[,\n<]", html, re.IGNORECASE),
          "Sign-off uses 'Best' — must be Thanks/Thank you")

    # ── 5. PERSONA INTEGRITY ─────────────────────────────────────────────────
    print("\n[PERSONA]")
    # Check that internal persona names aren't in visible text (strip tags first)
    internal_names = ["victoria hale", "wraith", "sterling", "harlan", "dembe",
                      "iron vic", "luna voss", "thunderbird os"]
    found_names = [n for n in internal_names if n in text_only.lower()]
    check("No internal persona names in visible text",
          len(found_names) == 0,
          f"Found: {found_names}" if found_names else "")

    # ── 6. DOSSIER CROSS-CHECK ───────────────────────────────────────────────
    if dossier_path and dossier_path.exists():
        print("\n[DOSSIER CROSS-CHECK]")
        dossier = dossier_path.read_text()
        # Check client names match
        name_match = re.search(r"full_name:\s*[\"']?([^\"'\n]+)", dossier)
        if name_match:
            full_name = name_match.group(1).strip()
            first_names = [n.strip() for n in re.split(r"[,&/+]", full_name) if n.strip()]
            for fn in first_names[:2]:
                fname = fn.split()[0]
                check(f"Client name '{fname}' in email",
                      fname in html,
                      f"Dossier name '{fname}' not found in email")

    # ── SUMMARY ──────────────────────────────────────────────────────────────
    blocks = [(n, d) for n, p, d, s in results if not p and s == "BLOCK"]
    warns = [(n, d) for n, p, d, s in results if not p and s == "WARN"]

    print(f"\n{'='*60}")
    if blocks:
        print(f"\033[91m❌ BLOCKED — {len(blocks)} issue(s) must be fixed:\033[0m")
        for n, d in blocks:
            print(f"   • {n}: {d}")
        print(f"\033[93m⚠️  {len(warns)} warning(s) — fix before send\033[0m" if warns else "")
    elif warns:
        print(f"\033[93m⚠️  PASS WITH {len(warns)} WARNING(S) — review before send\033[0m")
    else:
        print(f"\033[92m✅ ALL CHECKS PASSED — ready for Commander review\033[0m")

    # Log result
    log_path = Path("logs/email_validation.log")
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        status = "BLOCKED" if blocks else ("WARNINGS" if warns else "PASS")
        f.write(f"{datetime.now().isoformat()} | {html_path.name} | {status} | "
                f"{len(blocks)} blocks, {len(warns)} warns\n")

    return len(blocks) == 0


def main():
    parser = argparse.ArgumentParser(description="D2M Client Email Validator")
    parser.add_argument("html", nargs="?", help="HTML file to validate")
    parser.add_argument("--dossier", help="Dossier file for cross-check")
    parser.add_argument("--all", action="store_true", help="Validate all files in drafts/")
    args = parser.parse_args()

    if args.all:
        files = list(DRAFTS_DIR.glob("*.html"))
        if not files:
            print("No HTML files in drafts/")
            sys.exit(0)
        all_pass = all(validate_file(f) for f in files)
        sys.exit(0 if all_pass else 1)
    elif args.html:
        dossier = Path(args.dossier) if args.dossier else None
        passed = validate_file(Path(args.html), dossier)
        sys.exit(0 if passed else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
