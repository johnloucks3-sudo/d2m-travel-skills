"""
Dossier Validation Script — Sterling A7 / Harlan A9
scripts/validate_dossier.py

Validates all client dossiers against required schema and financial freshness rules.
Run: python3 scripts/validate_dossier.py [--dossier FILE] [--fix]

Checks:
  1. Required fields present (per dossiers/CLAUDE.md)
  2. Financial fields have verified_date and source tags
  3. Financial field freshness (flags if > 30 days since last verification)
  4. YAML frontmatter exists on client dossiers
  5. FPD–PAYMENT-SIGNAL HARD CHECK (Sterling A7, 2026-06-11):
     Any status:active dossier carrying an `fpd:` field MUST also carry a
     payment signal — `payment_status:` OR `balance_due:`. An FPD with no
     payment signal is exactly what made Loucks Grandeur's $24,798 FPD
     invisible. This is a FAILURE (exit 1), surfaced by name + missing field.
     Plus two WARNINGS (never affect exit code): `fpd:` not valid ISO date,
     and `fpd_verified_date` > 30 days stale.
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime, date, timezone, timedelta

THUNDERBIRD = Path(__file__).parent.parent
DOSSIERS_DIR = THUNDERBIRD / "dossiers"

# Required YAML frontmatter fields for any active client dossier
REQUIRED_FIELDS = [
    "client",
    "departure",
    "payment_status",
]

# Financial DOLLAR fields that require strict freshness tracking (hard fail when stale).
# NOTE: `fpd` (a DATE, not a dollar amount) is intentionally NOT here — its own
# ISO-validity and verified-date staleness are handled as WARNINGS by
# check_fpd_payment_signal() per Sterling A7 2026-06-11 (task: stale fpd = warn,
# not fail). `fpd_amount` remains here so the dollar figure stays strictly fresh.
FINANCIAL_FIELDS = [
    "fpd_amount",
    "balance_due",
    "total_cost",
    "deposit_amount",
]

# A status:active dossier with an fpd: but none of these payment signals is the
# Loucks-Grandeur invisible-FPD bug. Presence of ANY one satisfies the hard check.
PAYMENT_SIGNAL_FIELDS = ["payment_status", "balance_due"]

# Max age (days) before a financial field is flagged stale
FRESHNESS_THRESHOLD_DAYS = 30

# Dossiers that are ship/trip intel (not client-facing) — skip financial checks
INTEL_DOSSIER_PREFIXES = [
    "DOSSIER_Celebrity",
    "DOSSIER_ExploraII",
    "DOSSIER_Prestige",
    "DOSSIER_Princess",
    "DOSSIER_Regent_LesserAntilles",
    "DOSSIER_Regent_Tips",
    "DOSSIER_Regent_Loucks",
    "DOSSIER_Loucks_",
    "DOSSIER_SilverNova_Pacific",
    "DOSSIER_VikingMars",  # trip dossier not individual client
    "Britan_Joe",
    "flights_",
    "ElectronicTicket",
]

TODAY = date.today()


def is_intel_dossier(path: Path) -> bool:
    for prefix in INTEL_DOSSIER_PREFIXES:
        if path.name.startswith(prefix):
            return True
    return path.suffix != ".md"


def parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a markdown file. Returns None if absent."""
    text = path.read_text(errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_block = text[3:end].strip()
    fields = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip().strip('"')
    return fields


def check_freshness(fields: dict, path: Path) -> list[str]:
    """Check financial fields for missing or stale verification dates."""
    issues = []
    for field in FINANCIAL_FIELDS:
        if field not in fields:
            continue
        verified_key = f"{field}_verified_date"
        source_key = f"{field}_source"
        if verified_key not in fields:
            issues.append(f"  ⚠️  {field}: no {verified_key} — cannot confirm freshness")
            continue
        if source_key not in fields:
            issues.append(f"  ⚠️  {field}: no {source_key} — origin unknown")
        try:
            verified_date = date.fromisoformat(fields[verified_key])
            age = (TODAY - verified_date).days
            if age > FRESHNESS_THRESHOLD_DAYS:
                issues.append(
                    f"  🔴 {field}: last verified {verified_date} ({age}d ago) — STALE, needs portal check"
                )
        except ValueError:
            issues.append(f"  ⚠️  {field}: {verified_key} has invalid date format: {fields[verified_key]!r}")
    return issues


def check_fpd_payment_signal(fields: dict) -> tuple[list[str], list[str]]:
    """FPD–payment-signal hard check + fpd warnings.

    Returns (failures, warnings).
      FAILURE (exit 1): status:active + fpd present + NO payment signal.
      WARNING (no exit impact): fpd value not valid ISO date;
                                fpd_verified_date > 30 days stale.

    Sterling A7 2026-06-11 — compounding rule from the Loucks-Grandeur
    $24,798 invisible-FPD incident. An FPD with no payment signal hides
    a payable balance from every downstream sweep.
    """
    failures: list[str] = []
    warnings: list[str] = []

    if "fpd" not in fields:
        return failures, warnings

    is_active = fields.get("status", "").strip().lower() == "active"

    # --- HARD CHECK: active + fpd + no payment signal => FAIL ---
    if is_active:
        if not any(sig in fields for sig in PAYMENT_SIGNAL_FIELDS):
            failures.append(
                "❌  FPD–PAYMENT-SIGNAL: status:active carries fpd "
                f"({fields['fpd']!r}) but NO payment signal — add "
                f"'payment_status:' or 'balance_due:' (Loucks-Grandeur invisible-FPD class)"
            )

    # --- WARNING: fpd value not valid ISO date ---
    fpd_raw = fields["fpd"].strip().strip('"')
    try:
        date.fromisoformat(fpd_raw)
    except ValueError:
        warnings.append(
            f"⚠️  fpd value {fpd_raw!r} is not a valid ISO date (expected YYYY-MM-DD)"
        )

    # --- WARNING: fpd_verified_date stale (>30d) ---
    vdate = fields.get("fpd_verified_date", "").strip().strip('"')
    if vdate:
        try:
            verified = date.fromisoformat(vdate)
            age = (TODAY - verified).days
            if age > FRESHNESS_THRESHOLD_DAYS:
                warnings.append(
                    f"⚠️  fpd_verified_date {verified} is {age}d stale "
                    f"(>{FRESHNESS_THRESHOLD_DAYS}d) — re-verify against portal"
                )
        except ValueError:
            warnings.append(
                f"⚠️  fpd_verified_date {vdate!r} is not a valid ISO date"
            )

    return failures, warnings


def validate_dossier(path: Path) -> dict:
    result = {
        "file": path.name,
        "path": str(path),
        "is_intel": is_intel_dossier(path),
        "has_frontmatter": False,
        "missing_required": [],
        "freshness_issues": [],
        "fpd_failures": [],
        "warnings": [],
        "pass": False,
    }

    if result["is_intel"]:
        result["pass"] = True
        return result

    fields = parse_frontmatter(path)
    if fields is None:
        result["missing_required"].append("YAML frontmatter missing entirely")
        return result

    result["has_frontmatter"] = True

    for req in REQUIRED_FIELDS:
        if req not in fields:
            result["missing_required"].append(f"required field '{req}' absent")

    result["freshness_issues"] = check_freshness(fields, path)

    fpd_failures, fpd_warnings = check_fpd_payment_signal(fields)
    result["fpd_failures"] = fpd_failures
    result["warnings"] = fpd_warnings

    # Warnings NEVER affect the exit code — only hard failures do.
    result["pass"] = (
        not result["missing_required"]
        and not result["freshness_issues"]
        and not result["fpd_failures"]
    )
    return result


def run_validation(target: Path | None = None) -> list[dict]:
    if target:
        paths = [target]
    else:
        paths = sorted(DOSSIERS_DIR.glob("*.md"))
        paths = [p for p in paths if p.name != "CLAUDE.md"]

    return [validate_dossier(p) for p in paths]


def print_report(results: list[dict]) -> int:
    """Print validation report. Returns exit code (0=clean, 1=issues found)."""
    client_results = [r for r in results if not r["is_intel"]]
    passed = [r for r in client_results if r["pass"]]
    failed = [r for r in client_results if not r["pass"]]

    print("\n" + "=" * 72)
    print("DOSSIER VALIDATION REPORT")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M MT')}")
    print(f"Checked: {len(client_results)} client dossiers | Skipped: {len(results) - len(client_results)} intel dossiers")
    print("=" * 72)

    if failed:
        print(f"\n🔴 FAILED: {len(failed)}")
        for r in failed:
            print(f"\n  📄 {r['file']}")
            for issue in r["missing_required"]:
                print(f"  ❌  {issue}")
            for issue in r["fpd_failures"]:
                print(f"  {issue}")
            for issue in r["freshness_issues"]:
                print(f"  {issue}")
    else:
        print("\n✅ All client dossiers pass validation")

    # WARNINGS — informational only, never affect exit code.
    warned = [r for r in client_results if r["warnings"]]
    if warned:
        print(f"\n⚠️  WARNINGS (advisory, do not fail the run): {len(warned)} dossier(s)")
        for r in warned:
            print(f"\n  📄 {r['file']}")
            for w in r["warnings"]:
                print(f"  {w}")

    if passed:
        print(f"\n✅ PASSED: {len(passed)}")
        for r in passed:
            print(f"  {r['file']}")

    print("\n" + "=" * 72)
    print("SUMMARY")
    print(f"  Pass: {len(passed)}/{len(client_results)}")
    print(f"  Fail: {len(failed)}/{len(client_results)}")

    # Freshness summary
    stale = sum(1 for r in client_results for i in r["freshness_issues"] if "STALE" in i)
    missing_dates = sum(1 for r in client_results for i in r["freshness_issues"] if "no " in i and "verified_date" in i)
    if stale:
        print(f"  🔴 Stale financial fields (>{FRESHNESS_THRESHOLD_DAYS}d): {stale}")
    if missing_dates:
        print(f"  ⚠️  Financial fields missing verified_date: {missing_dates}")

    # FPD–payment-signal hard-check rollup (Sterling A7 — Baldrige sweep signal)
    fpd_no_signal = sum(1 for r in client_results if r["fpd_failures"])
    fpd_warnings = sum(len(r["warnings"]) for r in client_results)
    print(f"  🔒 FPD without payment signal (HARD FAIL): {fpd_no_signal}")
    if fpd_warnings:
        print(f"  ⚠️  FPD advisory warnings: {fpd_warnings}")
    print("=" * 72 + "\n")

    return 1 if failed else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate D2M client dossiers")
    parser.add_argument("--dossier", type=Path, help="Validate single dossier file")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of report")
    args = parser.parse_args()

    results = run_validation(args.dossier)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
        sys.exit(0)

    sys.exit(print_report(results))
