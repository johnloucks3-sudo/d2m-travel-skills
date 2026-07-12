"""
Thunderbird Dossier Scanner — IOC Build 3
===========================================
Proactive gap detection across all client dossiers.

Purpose: Remove Commander as safety net. System surfaces gaps before problems.

Scans for:
  - FPDs within 14 days with payment not confirmed
  - Unassigned seats on confirmed flights
  - Missing passport verification
  - Validation touchpoints overdue
  - Insurance gaps
  - Portal uploads not confirmed ("I think?")

Runs daily at 6:45 AM, results injected into morning briefing.
"""

import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DOSSIER_DIR = Path(os.path.expanduser("~/Thunderbird/dossiers"))

# Files to skip (not client dossiers)
SKIP_FILES = {"CLAUDE.md", "DANI_TESTER_BRIEFINGS.md", "DOSSIER_Regent_Tips_Guide.md"}

# Legitimate markdown structural markers — excluded from the repeated-line
# corruption check (see _check_corruption). These recur many times in any
# normal well-sectioned dossier and are not a corruption signal.
_STRUCTURAL_MARKERS = {"---", "***", "___"}


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------

class Alert:
    """A gap or action item detected in a dossier."""

    SEVERITY_CRITICAL = "CRITICAL"
    SEVERITY_WARNING = "WARNING"
    SEVERITY_INFO = "INFO"

    def __init__(self, dossier: str, category: str, severity: str, message: str):
        self.dossier = dossier
        self.category = category
        self.severity = severity
        self.message = message

    def __repr__(self):
        return f"[{self.severity}] {self.dossier} — {self.category}: {self.message}"

    def to_dict(self) -> Dict[str, str]:
        return {
            "dossier": self.dossier,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Scanner functions
# ---------------------------------------------------------------------------

def _parse_date(text: str) -> Optional[datetime]:
    """Try to parse common date formats from dossier text."""
    formats = [
        "%b %d, %Y",    # Mar 25, 2026
        "%b %d",         # Mar 25 (assume current year)
        "%Y-%m-%d",      # 2026-03-25
        "%B %d, %Y",    # March 25, 2026
    ]
    text = text.strip().rstrip(",").strip()
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            # If no year parsed (just month/day), assume current year
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt
        except ValueError:
            continue
    return None


def _check_corruption(filepath: Path, text: str, lines: list) -> Optional[Alert]:
    """Detect dossier file corruption before scanning.

    Two signals:
    1. Repeated-line ratio — any single line appearing >10x is a write-loop artifact.
    2. File size spike — files over 500KB are almost certainly corrupted (largest
       legitimate dossier in production is ~120KB).
    Returns an Alert if corruption is detected, else None.
    """
    name = filepath.stem
    size_kb = filepath.stat().st_size / 1024

    if size_kb > 500:
        return Alert(name, "corruption", Alert.SEVERITY_CRITICAL,
            f"File size {size_kb:.0f}KB far exceeds normal range (<120KB) — likely write-loop corruption. "
            f"DO NOT USE for client work. Restore from Drive or git.")

    if lines:
        from collections import Counter
        # 2026-07-13 BUG FIX: legitimate markdown structural markers (YAML
        # frontmatter delimiters, horizontal-rule section dividers) recur
        # many times in any normal well-sectioned dossier and were false-
        # positiving as "write-loop corruption" — e.g. a clean 212-line
        # dossier with 13 '---' section dividers got flagged "DO NOT USE,
        # restore from git" though nothing was wrong with it. Genuine
        # write-loop corruption duplicates substantive content, not a bare
        # 3-char divider, so structural markers are excluded from the count.
        line_counts = Counter(
            l.strip() for l in lines
            if l.strip() and l.strip() not in _STRUCTURAL_MARKERS
        )
        if line_counts:
            most_common_line, most_common_count = line_counts.most_common(1)[0]
            repeat_ratio = most_common_count / len(lines)
            if most_common_count > 10 and repeat_ratio > 0.05:
                return Alert(name, "corruption", Alert.SEVERITY_CRITICAL,
                    f"Repeated-line corruption detected: '{most_common_line[:60]}' "
                    f"appears {most_common_count}x ({repeat_ratio:.0%} of file). "
                    f"DO NOT USE for client work. Restore from Drive or git.")

    return None


def _scan_one_dossier(filepath: Path, today: datetime) -> List[Alert]:
    """Scan a single dossier file for gaps and action items."""
    alerts: List[Alert] = []
    name = filepath.stem  # e.g., "Furlow_Regent_3071222"
    lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    text = "".join(lines)
    text_upper = text.upper()

    # -----------------------------------------------------------------------
    # 0. Corruption pre-check — abort scan if file is corrupted
    # -----------------------------------------------------------------------
    corruption_alert = _check_corruption(filepath, text, lines)
    if corruption_alert:
        return [corruption_alert]  # Surface immediately, skip remaining checks

    # -----------------------------------------------------------------------
    # 1. Final Payment Date (FPD) — critical if within 14 days
    # -----------------------------------------------------------------------
    fpd_patterns = [
        r"FINAL PAYMENT.*?(\w+ \d{1,2},? \d{4})",
        r"Balance Due.*?(\w+ \d{1,2},? \d{4})",
        r"PAYMENT DUE.*?(\w+ \d{1,2},? \d{4})",
        r"FPD[:\s]+(\w+ \d{1,2},? \d{4})",
    ]
    fpd_date = None
    for pat in fpd_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            fpd_date = _parse_date(m.group(1))
            if fpd_date:
                break

    if fpd_date:
        days_until = (fpd_date - today).days
        # Payment-made detection — must match the frontmatter forms too, or PAID clients
        # get flagged "FPD OVERDUE" forever. (Fixed 2026-06-15: 'paid_in_full' underscores,
        # 'Final Payment Made', and pro-bono were all being missed.)
        payment_confirmed = bool(re.search(
            r"(PAYMENT\s+(CONFIRMED|PROCESSED|COMPLETE|PAID|MADE))"
            r"|(PAID[_ ]IN[_ ]FULL)"
            r"|(PAYMENT[_ ]STATUS[:\s]+PAID)"
            r"|(FINAL PAYMENT[^\n]{0,40}(MADE|PAID|✅))"
            r"|(PRO[_ ]BONO)",
            text_upper,
        ))
        if not payment_confirmed:
            if days_until < 0:
                alerts.append(Alert(name, "payment", Alert.SEVERITY_CRITICAL,
                    f"FPD OVERDUE by {abs(days_until)} days ({fpd_date.strftime('%b %d')})"))
            elif days_until <= 7:
                alerts.append(Alert(name, "payment", Alert.SEVERITY_CRITICAL,
                    f"FPD in {days_until} days ({fpd_date.strftime('%b %d')}) — payment not confirmed"))
            elif days_until <= 14:
                alerts.append(Alert(name, "payment", Alert.SEVERITY_WARNING,
                    f"FPD in {days_until} days ({fpd_date.strftime('%b %d')}) — payment not confirmed"))

    # -----------------------------------------------------------------------
    # 2. Unassigned seats on flights
    # -----------------------------------------------------------------------
    # Look for seat columns with " — " or empty/dash indicators
    seat_gaps = len(re.findall(r'\|\s*—\s*\|', text))
    # Also check for "not assigned" or "seats still needed"
    if re.search(r'seats?\s+(still\s+)?need(ed)?|not\s+assigned|unassigned', text, re.IGNORECASE):
        seat_gaps += 1
    if seat_gaps > 0:
        alerts.append(Alert(name, "flights", Alert.SEVERITY_WARNING,
            f"{seat_gaps} flight segment(s) with unassigned seats"))

    # -----------------------------------------------------------------------
    # 3. Missing passport verification
    # -----------------------------------------------------------------------
    if re.search(r'passport', text, re.IGNORECASE):
        if re.search(r'passport.{0,30}(PENDING|not\s+verified|"I think"|\bI think\b)', text, re.IGNORECASE):
            alerts.append(Alert(name, "documents", Alert.SEVERITY_WARNING,
                "Passport verification pending or uncertain"))

    # -----------------------------------------------------------------------
    # 4. Insurance gaps
    # -----------------------------------------------------------------------
    has_insurance_mention = re.search(r'insurance|travel\s+protection', text, re.IGNORECASE)
    if has_insurance_mention:
        insurance_confirmed = re.search(
            r'insurance.{0,50}(CONFIRMED|BOOKED|PURCHASED|ACTIVE)',
            text, re.IGNORECASE,
        )
        insurance_pending = re.search(
            r'insurance.{0,80}(PENDING|not\s+booked|reviewing|holding off|open|suspicious)',
            text, re.IGNORECASE,
        )
        if insurance_pending and not insurance_confirmed:
            alerts.append(Alert(name, "insurance", Alert.SEVERITY_WARNING,
                "Travel insurance not confirmed"))

    # -----------------------------------------------------------------------
    # 5. Uncertain portal uploads ("I think?")
    # -----------------------------------------------------------------------
    if re.search(r'["\'](I think\??)["\'"]|uploaded.*\(\s*"?I think', text, re.IGNORECASE):
        alerts.append(Alert(name, "documents", Alert.SEVERITY_WARNING,
            'Uncertain portal upload — client said "I think?" — verify'))

    # -----------------------------------------------------------------------
    # 6. Overdue validation touchpoints
    # -----------------------------------------------------------------------
    # Look for "Monthly Validations:" line with dates
    val_match = re.search(r'Monthly Validations?:?\s*([\w\s·,]+)', text)
    if val_match:
        date_str = val_match.group(1)
        # Extract individual dates like "Apr 1 · May 1 · Jun 1"
        month_day_matches = re.findall(r'(\w+ \d{1,2})', date_str)
        for md in month_day_matches:
            vdate = _parse_date(md)
            if vdate and (today - vdate).days > 3:
                # This validation date has passed
                alerts.append(Alert(name, "validation", Alert.SEVERITY_INFO,
                    f"Validation touchpoint {md} may be overdue"))
                break  # Only flag the most recent overdue one

    # -----------------------------------------------------------------------
    # 7. Open action items (unchecked boxes)
    # -----------------------------------------------------------------------
    open_items = re.findall(r'^\s*\d+\.\s*\[ \]\s*(.+)', text, re.MULTILINE)
    if len(open_items) > 3:
        alerts.append(Alert(name, "actions", Alert.SEVERITY_INFO,
            f"{len(open_items)} open action items — review needed"))

    # -----------------------------------------------------------------------
    # 8. Process payment directives not yet completed
    # -----------------------------------------------------------------------
    if re.search(r'PROCESS PAYMENT|PAYMENT AUTHORIZED', text, re.IGNORECASE):
        if not re.search(r'PAYMENT (PROCESSED|COMPLETE|CONFIRMED)', text, re.IGNORECASE):
            alerts.append(Alert(name, "payment", Alert.SEVERITY_CRITICAL,
                "Payment authorized but not yet confirmed as processed"))

    return alerts


def scan_all_dossiers() -> List[Alert]:
    """Scan all dossiers in the dossier directory for gaps.

    Returns list of Alert objects sorted by severity (CRITICAL first).
    """
    if not DOSSIER_DIR.exists():
        logger.warning(f"Dossier directory not found: {DOSSIER_DIR}")
        return []

    today = datetime.now()
    all_alerts: List[Alert] = []

    for f in sorted(DOSSIER_DIR.glob("*.md")):
        if f.name in SKIP_FILES:
            continue
        try:
            file_alerts = _scan_one_dossier(f, today)
            all_alerts.extend(file_alerts)
        except Exception as e:
            logger.error(f"Error scanning {f.name}: {e}")
            all_alerts.append(Alert(f.stem, "scan_error", Alert.SEVERITY_INFO, str(e)))

    # Sort: CRITICAL → WARNING → INFO
    severity_order = {Alert.SEVERITY_CRITICAL: 0, Alert.SEVERITY_WARNING: 1, Alert.SEVERITY_INFO: 2}
    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 9))

    logger.info(f"Dossier scan complete: {len(all_alerts)} alerts across {len(list(DOSSIER_DIR.glob('*.md')))} dossiers")
    return all_alerts


def generate_alert_digest() -> str:
    """Format scan results as a morning briefing section.

    Returns empty string if no alerts.
    """
    alerts = scan_all_dossiers()
    if not alerts:
        return ""

    critical = [a for a in alerts if a.severity == Alert.SEVERITY_CRITICAL]
    warnings = [a for a in alerts if a.severity == Alert.SEVERITY_WARNING]
    info = [a for a in alerts if a.severity == Alert.SEVERITY_INFO]

    lines = ["## DOSSIER ALERTS"]

    if critical:
        lines.append(f"\n**CRITICAL ({len(critical)}):**")
        for a in critical:
            lines.append(f"- **{a.dossier}** [{a.category}]: {a.message}")

    if warnings:
        lines.append(f"\n**WARNING ({len(warnings)}):**")
        for a in warnings:
            lines.append(f"- {a.dossier} [{a.category}]: {a.message}")

    if info:
        lines.append(f"\n**INFO ({len(info)}):**")
        for a in info:
            lines.append(f"- {a.dossier} [{a.category}]: {a.message}")

    lines.append(f"\n*Scanned {len(list(DOSSIER_DIR.glob('*.md')))} dossiers at {datetime.now().strftime('%H:%M')}*")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_dossier_scanner_tools(mcp_server):
    """Register dossier scanner tools with the MCP server."""

    @mcp_server.tool(
        name="scan_dossiers",
        annotations={"title": "Scan All Dossiers for Gaps", "readOnlyHint": True},
    )
    async def scan_dossiers_tool() -> str:
        """Scan all client dossiers for gaps: FPDs, missing seats, passports, insurance, etc."""
        import json
        alerts = scan_all_dossiers()
        return json.dumps({
            "alert_count": len(alerts),
            "critical": len([a for a in alerts if a.severity == "CRITICAL"]),
            "warning": len([a for a in alerts if a.severity == "WARNING"]),
            "info": len([a for a in alerts if a.severity == "INFO"]),
            "alerts": [a.to_dict() for a in alerts],
        }, indent=2)

    @mcp_server.tool(
        name="dossier_alert_digest",
        annotations={"title": "Generate Dossier Alert Digest", "readOnlyHint": True},
    )
    async def dossier_alert_digest_tool() -> str:
        """Generate formatted alert digest for morning briefing."""
        return generate_alert_digest() or "No dossier alerts detected."

    logger.info("Dossier scanner tools registered (2 tools)")
