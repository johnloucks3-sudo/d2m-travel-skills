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

# Financial fields that require freshness tracking
FINANCIAL_FIELDS = [
    "fpd_amount",
    "fpd",
    "balance_due",
    "total_cost",
    "deposit_amount",
]

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


def validate_dossier(path: Path) -> dict:
    result = {
        "file": path.name,
        "path": str(path),
        "is_intel": is_intel_dossier(path),
        "has_frontmatter": False,
        "missing_required": [],
        "freshness_issues": [],
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
    result["pass"] = not result["missing_required"] and not result["freshness_issues"]
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
            for issue in r["freshness_issues"]:
                print(f"  {issue}")
    else:
        print("\n✅ All client dossiers pass validation")

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
