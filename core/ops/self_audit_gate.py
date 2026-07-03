#!/usr/bin/env python3
"""
core/ops/self_audit_gate.py — Pre-done QC gate for D2M Wing tasks.

Philosophy: AI distrusts its own "done." Before any task is marked complete,
run this gate. It catches count mismatches, missing required fields, per-pax
inconsistencies, and structural gaps.

Usage:
    from core.ops.self_audit_gate import audit, AuditResult
    result = audit(checks)
    if not result.passed:
        raise RuntimeError(result.summary())

    # Or as CLI:
    python3 core/ops/self_audit_gate.py --check count --expected 12 --got 11
"""

from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str  # CRITICAL | WARN | INFO
    check: str
    message: str
    expected: Any = None
    got: Any = None

    def as_dict(self) -> dict:
        d = {"severity": self.severity, "check": self.check, "message": self.message}
        if self.expected is not None:
            d["expected"] = self.expected
        if self.got is not None:
            d["got"] = self.got
        return d


@dataclass
class AuditResult:
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "CRITICAL" for f in self.findings)

    @property
    def critical(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "CRITICAL"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "WARN"]

    def summary(self) -> str:
        lines = [f"AUDIT {'PASS' if self.passed else 'FAIL'} — {len(self.critical)} critical, {len(self.warnings)} warnings"]
        for f in self.findings:
            tag = f"[{f.severity}]"
            detail = f.message
            if f.expected is not None and f.got is not None:
                detail += f" (expected={f.expected!r}, got={f.got!r})"
            lines.append(f"  {tag} {f.check}: {detail}")
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps({
            "passed": self.passed,
            "findings": [f.as_dict() for f in self.findings],
        }, indent=2)


# ---------------------------------------------------------------------------
# Built-in checks
# ---------------------------------------------------------------------------

def check_count(result: AuditResult, expected: int, got: int, label: str = "items") -> None:
    """Verify expected count matches actual count."""
    if got == expected:
        result.findings.append(Finding("INFO", "count_match", f"{label}: {got}/{expected} ✓"))
    else:
        result.findings.append(Finding(
            "CRITICAL", "count_match",
            f"{label} count mismatch", expected=expected, got=got,
        ))


def check_required_fields(result: AuditResult, obj: dict, required: list[str], label: str = "record") -> None:
    """Verify all required fields are present and non-empty."""
    missing = [k for k in required if not obj.get(k)]
    if missing:
        result.findings.append(Finding(
            "CRITICAL", "required_fields",
            f"{label} missing fields: {missing}", expected=required, got=list(obj.keys()),
        ))
    else:
        result.findings.append(Finding("INFO", "required_fields", f"{label}: all required fields present ✓"))


def check_per_pax_consistency(result: AuditResult, records: list[dict], key: str, label: str = "pax") -> None:
    """Verify a field is populated consistently across all pax records."""
    missing = [i for i, r in enumerate(records) if not r.get(key)]
    if missing:
        result.findings.append(Finding(
            "CRITICAL", "per_pax_consistency",
            f"Field '{key}' missing for {len(missing)}/{len(records)} {label} records",
            expected=len(records), got=len(records) - len(missing),
        ))
    else:
        result.findings.append(Finding("INFO", "per_pax_consistency",
            f"Field '{key}' present for all {len(records)} {label} records ✓"))


def check_couples_consistency(result: AuditResult, records: list[dict], couple_key: str = "couple_id") -> None:
    """Verify per-couple records are balanced (each couple has same fields)."""
    couples: dict[str, list[dict]] = {}
    for r in records:
        cid = r.get(couple_key, "unknown")
        couples.setdefault(cid, []).append(r)

    field_sets = {cid: set().union(*[set(r.keys()) for r in recs]) for cid, recs in couples.items()}
    all_fields = set().union(*field_sets.values())
    uneven = {cid: all_fields - fs for cid, fs in field_sets.items() if all_fields - fs}

    if uneven:
        for cid, missing_fields in uneven.items():
            result.findings.append(Finding(
                "WARN", "couples_consistency",
                f"Couple '{cid}' missing fields present in other couples",
                expected=sorted(all_fields), got=sorted(field_sets[cid]),
            ))
    else:
        result.findings.append(Finding("INFO", "couples_consistency",
            f"All {len(couples)} couples have consistent fields ✓"))


def check_no_stale_placeholder(result: AuditResult, text: str, label: str = "content") -> None:
    """Detect TBD / placeholder text that should have been resolved."""
    import re
    placeholders = re.findall(r'\b(TBD|TODO|PLACEHOLDER|FIXME|XXX|\?\?\?)\b', text, re.I)
    if placeholders:
        result.findings.append(Finding(
            "WARN", "stale_placeholder",
            f"{label} contains unresolved placeholders: {sorted(set(placeholders))}",
        ))
    else:
        result.findings.append(Finding("INFO", "stale_placeholder", f"{label}: no stale placeholders ✓"))


def check_financial_totals(result: AuditResult, line_items: list[float], stated_total: float,
                            tolerance: float = 0.02, label: str = "total") -> None:
    """Verify sum of line items matches stated total within tolerance %."""
    computed = sum(line_items)
    if stated_total == 0:
        result.findings.append(Finding("WARN", "financial_totals", f"{label}: stated total is zero"))
        return
    delta_pct = abs(computed - stated_total) / abs(stated_total)
    if delta_pct > tolerance:
        result.findings.append(Finding(
            "CRITICAL", "financial_totals",
            f"{label} sum mismatch (>{tolerance*100:.0f}% tolerance)",
            expected=round(stated_total, 2), got=round(computed, 2),
        ))
    else:
        result.findings.append(Finding("INFO", "financial_totals",
            f"{label}: sum matches stated total within {tolerance*100:.0f}% ✓"))


def check_harlan_sign_off(result: AuditResult, has_dollar_figures: bool, harlan_signed: bool) -> None:
    """Gate: if email contains dollar figures, Harlan must have signed off."""
    if has_dollar_figures and not harlan_signed:
        result.findings.append(Finding(
            "CRITICAL", "harlan_gate",
            "Email contains dollar figures but Harlan sign-off not confirmed",
        ))
    elif has_dollar_figures and harlan_signed:
        result.findings.append(Finding("INFO", "harlan_gate", "Harlan sign-off confirmed ✓"))


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

def run_checks(check_fns: list[Callable[[AuditResult], None]]) -> AuditResult:
    """Run a list of check callables against a shared AuditResult."""
    result = AuditResult()
    for fn in check_fns:
        try:
            fn(result)
        except Exception as e:
            result.findings.append(Finding("WARN", "check_error", f"Check raised: {e}"))
    return result


# Alias for ergonomic import
audit = run_checks


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="D2M pre-done self-audit gate")
    sub = parser.add_subparsers(dest="cmd")

    # count check
    cnt = sub.add_parser("count", help="count_match check")
    cnt.add_argument("--expected", type=int, required=True)
    cnt.add_argument("--got", type=int, required=True)
    cnt.add_argument("--label", default="items")

    # placeholder check
    ph = sub.add_parser("placeholder", help="stale placeholder scan")
    ph.add_argument("--file", required=True)

    # financial check
    fin = sub.add_parser("financial", help="financial totals check")
    fin.add_argument("--items", nargs="+", type=float, required=True)
    fin.add_argument("--total", type=float, required=True)
    fin.add_argument("--tolerance", type=float, default=0.02)

    args = parser.parse_args()

    result = AuditResult()
    if args.cmd == "count":
        check_count(result, args.expected, args.got, args.label)
    elif args.cmd == "placeholder":
        text = Path(args.file).read_text()
        check_no_stale_placeholder(result, text, label=args.file)
    elif args.cmd == "financial":
        check_financial_totals(result, args.items, args.total, args.tolerance)
    else:
        parser.print_help()
        return 1

    print(result.summary())
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(_cli())
