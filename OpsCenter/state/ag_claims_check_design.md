# AG Claims Check Design

### 1. Quantitative Claims & Falsifiability Analysis
In reviewing `/home/john/Thunderbird/output/weekly_reports/weekly_report_2026-07-29.md`, here is the breakdown of quantitative claims:

**Checkable (Falsifiable):**
- "approximately 124 commits" (Git log length)
- "across seven days" (Calendar)
- "12-pax dark navy intake portal" (Form parameters)
- "2-window consolidated brief daemons" (Code configuration)
- "36 drafts restaged" (Gmail API / label count)
- "three Google Calendar reminders" (Calendar API)
- "8-Sector Wing Exercise" (Test harness output)
- "100% PASS" (Test suite results)
- "12 ghost missions from a single payment event" (Mission board history)
- "BA Business Class quote ($3,823.96)" (Pricing cache)
- "2-minute to 15-minute cadence" (Cron/timer config)
- "5X ($100/mo)" (Anthropic billing tier)
- "three suspense clocks set" (Calendar API)
- "FPD of $24,798" (TESS / financial DB)
- "0 drafts aging" (Gmail API)
- "D2M Pipeline: $18,830.93" / "Commissions Expected: $21,849.16" (Financial pipeline)
- "138 active missions total" / "~113 missions" (Mission board state)
- "16 active clients" (CRM / Dossier count)
- "26 artifacts, 25 artifacts, 13 artifacts, 10 artifacts — total 74 formal approval actions" (Hale bus / log)

**Uncheckable (Unfalsifiable / Anti-Theater):**
- "60+ initiatives executed" (No system tracks an "initiative"; it is an arbitrary grouping).
- "highest-output infrastructure week on record" (Subjective superlative unless defined by a specific metric like commit volume).
- "ten meaningful decisions than sixty-four nominal ones" (Meaningful vs. nominal is subjective judgment, not a metric).

### 2. The Rule & Pseudocode
To enforce SO-REPORTING-2026 Section 2.4, we need an **Artifact Allowlist Rule**.
**The Rule:** A quantitative claim (a number or number-word) is only permitted if the noun phrase it modifies resolves to a known, countable system artifact (e.g., `commits`, `missions`, `drafts`, `artifacts`, `clients`, `dollars`). If a number is attached to an abstract, un-tracked noun (`initiatives`, `efforts`, `wins`), it is flagged as theater and rejected.

**Pseudocode:**
```python
import re

# Canonical countable entities that have a queryable ground truth in D2M systems
CHECKABLE_ARTIFACTS = {
    'commit', 'commits', 'mission', 'missions', 'draft', 'drafts',
    'client', 'clients', 'artifact', 'artifacts', 'action', 'actions',
    'file', 'files', 'dollar', 'dollars', 'day', 'days', 'week', 'weeks',
    'pax', 'clock', 'clocks', 'timer', 'timers', 'quote', 'quotes'
}

# Anti-theater words that indicate fluff
THEATER_NOUNS = {'initiative', 'initiatives', 'effort', 'efforts', 'win', 'wins', 'project', 'projects'}

def claims_check(sentence: str) -> bool:
    # Find all numbers (digits or words) and the following noun
    # Simplified regex for demonstration: matches number + optional adjective + noun
    pattern = re.compile(r'\b(\d+|one|two|three|sixty)\+?\s+(?:[a-z\-]+\s+)?([a-z\-]+)\b', re.IGNORECASE)
    
    matches = pattern.findall(sentence)
    for number, noun in matches:
        noun_lower = noun.lower()
        if noun_lower in THEATER_NOUNS:
            return False, f"REJECT: Unfalsifiable metric '{noun_lower}'"
        
        # If we want strict mode: if noun_lower not in CHECKABLE_ARTIFACTS: return False
    return True, "PASS"
```

**3 Worked Examples that PASS:**
1. `"We closed 12 ghost missions."` (Matches "12 [ghost] missions" -> 'missions' is checkable)
2. `"Generated 36 drafts."` (Matches "36 drafts" -> 'drafts' is checkable)
3. `"Total of 124 commits this week."` (Matches "124 commits" -> 'commits' is checkable)

**3 Worked Examples that FAIL:**
1. `"60+ initiatives executed."` (Matches "60+ initiatives" -> flagged as theater)
2. `"Completed 5 major efforts."` (Matches "5 [major] efforts" -> flagged as theater)
3. `"Delivered 10 big wins for the Wing."` (Matches "10 [big] wins" -> flagged as theater)

### 3. The Failure Mode (Adversarial Assessment)
This rule is imperfect by design to avoid freezing legitimate prose.
- **False Negative (Legitimate sentence wrongly rejected):** `"I spun up 3 new test harnesses."` The rule rejects it because "harnesses" isn't in the canonical artifact allowlist, punishing the agent for valid technical specificity.
- **False Positive (Unfalsifiable claim that slips through):** `"We took 60 actions to improve client trust."` Because "actions" is in the allowlist (to permit "approval actions"), the engine passes it, even though "actions to improve trust" is just as abstract and unfalsifiable as "initiatives."
