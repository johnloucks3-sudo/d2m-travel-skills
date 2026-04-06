"""
Thunderbird Pre-Send Evaluator
===============================

Zero-API-cost regex scanner that catches leaks BEFORE COS review.
Runs between Dani's draft and the COS gate. No LLM calls — pure pattern matching.

Catches:
  - Commission/markup/net rate leaks (internal pricing visible to client)
  - Internal persona names (Hale, Dembe, Harlan, etc.)
  - Staff terminology (SSS, A2, COS, IOC, etc.)
  - Internal system references (Thunderbird, MCP, dossier, etc.)
  - Placeholder text left in drafts
  - Wrong sign-off (not "Thanks" / "Thank you")
  - Missing stationery elements

Integration:
  - Called in Dani Engine Phase 3 (Advocate) before draft creation
  - Also callable as standalone validation via MCP tool
  - Returns PASS / FAIL with specific violation list
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("thunderbird_presend_evaluator")


# ============================================================================
# Severity Levels
# ============================================================================

class Severity(str, Enum):
    BLOCK = "BLOCK"    # Must fix before sending — hard stop
    WARN = "WARN"      # Should fix but COS can override
    INFO = "INFO"      # Stylistic suggestion


@dataclass
class Violation:
    """A single pre-send violation."""
    rule_id: str
    severity: Severity
    message: str
    match: str = ""        # The offending text
    line_num: int = 0      # Approximate line in the draft
    suggestion: str = ""   # How to fix it

    def __str__(self) -> str:
        loc = f" (line {self.line_num})" if self.line_num else ""
        return f"[{self.severity.value}] {self.rule_id}{loc}: {self.message}"


@dataclass
class EvalResult:
    """Result of pre-send evaluation."""
    passed: bool
    violations: list[Violation] = field(default_factory=list)
    draft_hash: str = ""

    @property
    def block_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.BLOCK)

    @property
    def warn_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARN)

    def summary(self) -> str:
        if self.passed:
            return "PASS — no violations detected"
        blocks = [v for v in self.violations if v.severity == Severity.BLOCK]
        warns = [v for v in self.violations if v.severity == Severity.WARN]
        parts = []
        if blocks:
            parts.append(f"{len(blocks)} BLOCK")
        if warns:
            parts.append(f"{len(warns)} WARN")
        return f"FAIL — {', '.join(parts)} violations"

    def to_cos_report(self) -> str:
        """Format for COS review gate."""
        lines = [f"PRE-SEND EVALUATION: {self.summary()}"]
        if not self.violations:
            return lines[0]
        lines.append("")
        for v in self.violations:
            lines.append(f"  {v}")
            if v.suggestion:
                lines.append(f"    → Fix: {v.suggestion}")
        return "\n".join(lines)


# ============================================================================
# Rule Definitions
# ============================================================================

# COMMISSION / PRICING LEAKS — absolute blockers
COMMISSION_PATTERNS = [
    (r"\b(?:commission|markup|net\s*rate|agent\s*rate|wholesale|net\s*price)\b",
     "Commission/pricing terminology leaked"),
    (r"\b\d+%\s*(?:markup|commission|margin)\b",
     "Percentage markup/commission visible"),
    (r"\bmarkup\b", "Markup reference in client text"),
    (r"\bnet\s+(?:usd|eur|gbp|\$|€|£)\s*\d", "Net rate with currency visible"),
    (r"\bagent\s*(?:rate|price|cost|commission)\b", "Agent pricing terminology"),
    (r"\b(?:our|my)\s+(?:commission|cut|margin|share)\b", "Possessive commission reference"),
]

# INTERNAL PERSONA / STAFF NAMES — blockers
PERSONA_PATTERNS = [
    (r"\b(?:Col(?:onel)?\.?\s*)?(?:Victoria|Hale|Iron\s*Vic)\b", "COS persona name leaked"),
    (r"\b(?:Lt\s*Col\.?\s*)?(?:Marcus|Dembe|Wraith)\b", "A2 persona name leaked"),
    (r"\b(?:Lt\s*Col\.?\s*)?(?:Ryan|Castillo|Viper)\b", "A5 persona name leaked"),
    (r"\b(?:Victor|Vic)\s*Harlan\b", "A9 persona name leaked"),
    (r"\b(?:Col(?:onel)?\.?\s*)?(?:James|Padre)\s*Washington\b", "CH persona name leaked"),
    (r"\bNaia\s*Solberg[\s-]*Vega\b", "EXEC persona name leaked"),
    (r"\bLuna\s*Voss\b", "A6 persona name leaked"),
    (r"\bELON\b(?!\s*Musk)", "A12 persona name leaked"),  # Not Elon Musk context
    (r"\bTommy\s*Ikeda\b", "Decommissioned A10 persona referenced"),
]

# INTERNAL JARGON — blockers
JARGON_PATTERNS = [
    (r"\bStaff\s*Summary\s*Sheet\b", "SSS reference in client text"),
    (r"\b(?:SSS|IOC|MCP|A2A|C2)\b", "Internal acronym leaked"),
    (r"\bThunderbird\s*(?:OS|API|system)\b", "Internal system name leaked"),
    (r"\b(?:dossier|dossiers)\b", "Internal 'dossier' term (use 'trip file' or 'booking details')"),
    (r"\bcall_persona\b", "Code function name leaked"),
    (r"\brun_staff_meeting\b", "Internal function name leaked"),
    (r"\b(?:Phase\s*[123]|Aggregate|Artist|Advocate)\b(?=.*(?:Dani|engine|pipeline))",
     "Dani engine internals leaked"),
    (r"\bWing\s*(?:memory|coordinator)\b", "Internal architecture term"),
    (r"\bpersona\b(?!\s+non\s+grata)", "Internal 'persona' term in client text"),
]

# PLACEHOLDER / TEMPLATE ARTIFACTS — blockers
PLACEHOLDER_PATTERNS = [
    (r"\{\{.*?\}\}", "Unreplaced template variable"),
    (r"\[(?:TODO|FIXME|XXX|PLACEHOLDER|INSERT|FILL)\b", "Placeholder text left in draft"),
    (r"\[YOUR\s+\w+\s+HERE\]", "Template placeholder not replaced"),
    (r"<(?:client_name|date|amount|details)>", "XML placeholder not replaced"),
    (r"Lorem\s+ipsum", "Lorem ipsum placeholder text"),
]

# SIGN-OFF RULES — warnings
SIGNOFF_PATTERNS = [
    (r"\bBest(?:\s+regards?)?\s*,?\s*$", "Sign-off uses 'Best' — must be 'Thanks' or 'Thank you'"),
    (r"\bCheers\s*,?\s*$", "Sign-off uses 'Cheers' — must be 'Thanks' or 'Thank you'"),
    (r"\bWarm(?:ly|\s+regards)\s*,?\s*$", "Sign-off uses 'Warm regards' — use 'Thanks' or 'Thank you'"),
    (r"\bSincerely\s*,?\s*$", "Too formal — use 'Thanks' or 'Thank you'"),
]

# STYLE — info level
STYLE_PATTERNS = [
    (r"(?:Love\s*Group\s*Travel|LGT)\b", "Wrong company name — must be Dreams2Memories Travel"),
    (r"\bconcierge@d2mluxury\.quest\b.*\bjohnloucks3@\b",
     "Both email addresses in same message — pick one"),
]


def _scan_patterns(
    text: str,
    patterns: list[tuple[str, str]],
    rule_prefix: str,
    severity: Severity,
) -> list[Violation]:
    """Scan text against a list of (regex, message) patterns."""
    violations = []
    lines = text.split("\n")

    for i, (pattern, message) in enumerate(patterns):
        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for m in matches:
                violations.append(Violation(
                    rule_id=f"{rule_prefix}-{i+1:02d}",
                    severity=severity,
                    message=message,
                    match=m.group()[:80],
                    line_num=line_num,
                ))
                break  # One match per pattern per line is enough

    return violations


# ============================================================================
# Main Evaluator
# ============================================================================

def evaluate_draft(
    body: str,
    subject: str = "",
    recipient: str = "",
    is_client_facing: bool = True,
) -> EvalResult:
    """Evaluate a draft email before sending.

    Args:
        body: Email body text (plain text or HTML — HTML tags stripped)
        subject: Email subject line
        recipient: Recipient email address
        is_client_facing: If False, relaxes internal jargon rules

    Returns:
        EvalResult with pass/fail and violation list
    """
    # Strip HTML tags for pattern matching
    clean_body = re.sub(r"<[^>]+>", " ", body)
    clean_body = re.sub(r"&\w+;", " ", clean_body)  # HTML entities
    clean_body = re.sub(r"\s+", " ", clean_body)

    # Also check subject
    full_text = f"{subject}\n{clean_body}"

    violations: list[Violation] = []

    # Always check — commission leaks are catastrophic
    violations.extend(_scan_patterns(
        full_text, COMMISSION_PATTERNS, "COMM", Severity.BLOCK))

    # Always check — persona names should never leak
    violations.extend(_scan_patterns(
        full_text, PERSONA_PATTERNS, "PERSONA", Severity.BLOCK))

    if is_client_facing:
        # Internal jargon
        violations.extend(_scan_patterns(
            full_text, JARGON_PATTERNS, "JARGON", Severity.BLOCK))

        # Placeholders
        violations.extend(_scan_patterns(
            full_text, PLACEHOLDER_PATTERNS, "TMPL", Severity.BLOCK))

        # Sign-off
        violations.extend(_scan_patterns(
            full_text, SIGNOFF_PATTERNS, "SIGNOFF", Severity.WARN))

    # Style — always check
    violations.extend(_scan_patterns(
        full_text, STYLE_PATTERNS, "STYLE", Severity.WARN))

    # Check for empty body
    if len(clean_body.strip()) < 20:
        violations.append(Violation(
            rule_id="BODY-01",
            severity=Severity.BLOCK,
            message="Draft body is too short or empty",
            suggestion="Ensure the email has meaningful content",
        ))

    # Determine pass/fail — BLOCK violations = fail
    passed = not any(v.severity == Severity.BLOCK for v in violations)

    result = EvalResult(passed=passed, violations=violations)

    logger.info(f"Pre-send eval: {result.summary()}")
    if not passed:
        for v in violations:
            if v.severity == Severity.BLOCK:
                logger.warning(f"  BLOCK: {v}")

    return result


def evaluate_and_format(
    body: str,
    subject: str = "",
    recipient: str = "",
    is_client_facing: bool = True,
) -> tuple[bool, str]:
    """Convenience wrapper returning (passed, report_text)."""
    result = evaluate_draft(body, subject, recipient, is_client_facing)
    return result.passed, result.to_cos_report()


# ============================================================================
# Quick Checks (single-purpose)
# ============================================================================

def check_commission_leak(text: str) -> bool:
    """Quick check: does this text contain commission/pricing leaks?"""
    for pattern, _ in COMMISSION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def check_persona_leak(text: str) -> bool:
    """Quick check: does this text contain internal persona names?"""
    for pattern, _ in PERSONA_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def check_jargon_leak(text: str) -> bool:
    """Quick check: does this text contain internal jargon?"""
    for pattern, _ in JARGON_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
