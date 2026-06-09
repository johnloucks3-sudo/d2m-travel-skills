"""
WF-17 Gate Check — Sterling A7
scripts/wf17_gate_check.py

Runs before any client-facing product exits the Wing for Commander review.
Checks creative chain completion, financial source tracing, and dossier freshness.

Usage:
    python3 scripts/wf17_gate_check.py --client McLeod
    python3 scripts/wf17_gate_check.py --draft <draft_id>
    python3 scripts/wf17_gate_check.py --all         # check all active drafts

Exit: 0 = PASS, 1 = FAIL (blocks WF-17)
"""

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
DOSSIERS_DIR = THUNDERBIRD / "dossiers"
DRAFT_METADATA = THUNDERBIRD / "OpsCenter" / "draft_metadata.json"

# Creative chain steps required for a client product to reach WF-17
REQUIRED_CHAIN_STEPS = ["reyes", "luna", "naia", "dani"]

# Financial keywords that require Harlan sign-off
FINANCIAL_PATTERNS = [
    r"\$[\d,]+",          # dollar amounts
    r"balance due",
    r"final payment",
    r"fpd",
    r"commission",
]

FRESHNESS_DAYS = 30


def load_dossier_frontmatter(client_name: str) -> dict | None:
    """Find and parse dossier frontmatter for a client."""
    # Try exact match first, then partial
    candidates = list(DOSSIERS_DIR.glob(f"*{client_name}*.md"))
    candidates = [c for c in candidates if "CLAUDE" not in c.name]
    if not candidates:
        return None
    # Prefer multi-booking master dossier
    masters = [c for c in candidates if "Multi" in c.name or "Complete" in c.name]
    path = masters[0] if masters else candidates[0]

    text = path.read_text(errors="replace")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip().strip('"')
    fields["_dossier_path"] = str(path)
    return fields


def check_chain_completion(draft: dict) -> list[str]:
    """Check if the creative chain steps are recorded in draft metadata."""
    issues = []
    chain_steps = draft.get("chain_steps", {})
    if not chain_steps:
        # No chain tracking at all — legacy draft or chain not wired
        issues.append("  ⚠️  No creative chain steps recorded in draft metadata")
        issues.append("     Confirm manually: Reyes → Luna → Naia → Dani completed?")
        return issues

    for step in REQUIRED_CHAIN_STEPS:
        if step not in chain_steps:
            issues.append(f"  ❌  Chain step missing: {step.upper()} — not recorded as complete")
        elif not chain_steps[step].get("completed"):
            issues.append(f"  ❌  Chain step incomplete: {step.upper()}")

    return issues


def check_financial_fields(draft: dict, dossier: dict | None) -> list[str]:
    """Check financial fields have Harlan sign-off and are not stale."""
    issues = []
    body = draft.get("body_text", "") or draft.get("subject", "")

    has_financial = any(
        re.search(p, body, re.IGNORECASE)
        for p in FINANCIAL_PATTERNS
    )

    if not has_financial:
        return issues  # No financials in draft — no check needed

    if not draft.get("harlan_signoff") and not draft.get("harlan_approved"):
        issues.append("  ❌  Draft contains financial figures — Harlan sign-off ABSENT")
        issues.append("     Run Harlan verification before WF-17")

    if dossier:
        today = date.today()
        # Check each financial field's freshness
        for key, val in dossier.items():
            if key.endswith("_verified_date") and "NEEDS_VERIFICATION" in str(val):
                field = key.replace("_verified_date", "")
                issues.append(f"  ❌  Dossier field '{field}' = NEEDS_VERIFICATION — not cleared for client email")
            elif key.endswith("_verified_date") and val and val not in ("NEEDS_VERIFICATION",):
                try:
                    vdate = date.fromisoformat(val)
                    age = (today - vdate).days
                    if age > FRESHNESS_DAYS:
                        field = key.replace("_verified_date", "")
                        issues.append(f"  🔴  Dossier '{field}' stale: verified {val} ({age}d ago)")
                except ValueError:
                    pass

    return issues


def check_negative_space(draft: dict) -> list[str]:
    """Pipeline Integrity Rule 1: No inferred/pending/probable in client copy."""
    issues = []
    body = draft.get("body_text", "")
    banned = ["likely", "pending", "probably", "should be", "we believe", "assumed"]
    found = [w for w in banned if re.search(r"\b" + w + r"\b", body, re.IGNORECASE)]
    if found:
        issues.append(f"  ❌  Negative-Space Rule violation — banned phrases found: {found}")
        issues.append("     Remove or replace with confirmed data or silence.")
    return issues


def run_gate_check(draft_id: str | None = None, client_name: str | None = None) -> dict:
    """Run full WF-17 gate check. Returns result dict."""

    # Load draft
    draft = {}
    if draft_id and DRAFT_METADATA.exists():
        metadata = json.loads(DRAFT_METADATA.read_text())
        draft = metadata.get(draft_id, {})
        if not draft:
            return {"pass": False, "issues": [f"Draft ID '{draft_id}' not found in draft_metadata.json"]}

    # Infer client from draft if not provided
    if not client_name and draft:
        subject = draft.get("subject", "")
        to = draft.get("to", "")
        # Extract from subject
        for name in ["McLeod", "Furlow", "Ely", "Nichols", "Kuklinski", "Morton", "Loucks", "Spencer", "Westbrook"]:
            if name.lower() in subject.lower() or name.lower() in to.lower():
                client_name = name
                break

    dossier = load_dossier_frontmatter(client_name) if client_name else None

    all_issues = []

    # Run checks
    all_issues += check_chain_completion(draft)
    all_issues += check_financial_fields(draft, dossier)
    all_issues += check_negative_space(draft)

    # Dossier validation (if client known)
    if dossier:
        from validate_dossier import validate_dossier as vd
        sys.path.insert(0, str(THUNDERBIRD / "scripts"))
        vresult = vd(Path(dossier["_dossier_path"]))
        if not vresult["pass"]:
            for issue in vresult.get("freshness_issues", []):
                all_issues.append(f"  {issue}")
            for issue in vresult.get("missing_required", []):
                all_issues.append(f"  ❌  {issue}")

    passed = len(all_issues) == 0
    return {
        "pass": passed,
        "draft_id": draft_id,
        "client": client_name,
        "dossier": dossier.get("_dossier_path") if dossier else None,
        "issues": all_issues,
        "issue_count": len(all_issues),
    }


def print_report(result: dict) -> None:
    print("\n" + "=" * 72)
    print("WF-17 GATE CHECK")
    if result.get("client"):
        print(f"Client: {result['client']}")
    if result.get("draft_id"):
        print(f"Draft: {result['draft_id']}")
    print("=" * 72)

    if result["pass"]:
        print("\n✅ GATE PASS — product cleared for Commander review")
    else:
        print(f"\n🔴 GATE FAIL — {result['issue_count']} issue(s) blocking WF-17")
        print()
        for issue in result["issues"]:
            print(issue)

    print("\n" + "=" * 72 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WF-17 Gate Check")
    parser.add_argument("--draft", help="Draft ID from draft_metadata.json")
    parser.add_argument("--client", help="Client name (McLeod, Furlow, etc.)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    result = run_gate_check(draft_id=args.draft, client_name=args.client)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print_report(result)

    sys.exit(0 if result["pass"] else 1)
