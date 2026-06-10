"""
classifier.py — Task Classifier for Slot Router
Dreams2Memories Travel, LLC

Classifies an incoming task description along three axes:
  task_type:  research | build | draft | validate | decide | monitor | maintain
  subtype:    e.g. research.cruise_intel, build.daemon, draft.email
  complexity: simple | medium | complex | critical
"""

import re
import sys
from dataclasses import dataclass

TASK_TYPES = {'research', 'build', 'draft', 'validate', 'decide', 'monitor', 'maintain'}
COMPLEXITY_LEVELS = ['simple', 'medium', 'complex', 'critical']

# Client names known to the wing — presence bumps complexity slightly
CLIENT_NAMES = [
    'furlow', 'kuklinski', 'mcleod', 'nichols', 'loucks', 'westbrook',
    'morton', 'dodge', 'spencer', 'lyons', 'britan', 'bryana', 'ely', 'darrow',
]


@dataclass
class Classification:
    task_type: str
    subtype: str
    complexity: str
    confidence: float


# ─── Type scoring patterns ────────────────────────────────────────────────────

TYPE_PATTERNS: dict[str, list[tuple[str, int]]] = {
    'research': [
        (r'\b(research|find|look.?up|search|what\s+is|what\s+are|how\s+does|investigate|explore)\b', 3),
        (r'\b(weather|intel|discover|report|brief|overview|summary)\b', 2),
        (r'\b(cruise|flight|hotel|destination|port|ship|itinerary|fare|price|rate)\b', 2),
        (r'\b(news|status|current|latest|update\s+on|check\s+on)\b', 1),
    ],
    'build': [
        (r'\b(build|create|implement|develop|code|script|daemon|service|tool|mcp|skill|api|endpoint)\b', 3),
        (r'\b(fix|debug|repair|patch|refactor|wire|set\s+up|configure)\b', 2),
        (r'\.py\b|\.sh\b|\.json\b|\.yaml\b|\.toml\b', 2),
        (r'\b(function|class|module|pipeline|timer|systemd|cron)\b', 1),
    ],
    'draft': [
        (r'\b(draft|write|compose|email|letter|proposal|message|prepare)\b', 3),
        (r'\b(welcome|onboard|follow.?up|lifecycle|touchpoint|itinerary)\b', 2),
        (r'\b(send|client|passenger|guest|customer)\b', 1),
    ],
    'validate': [
        (r'\b(validate|verify|check|audit|confirm|reconcile|review|inspect)\b', 3),
        (r'\b(fpd|payment|balance|booking|commission|dossier|financial)\b', 2),
        (r'\b(correct|accurate|match|consistent|integrity)\b', 1),
    ],
    'decide': [
        (r'\b(decide|decision|should\s+we|recommend|advise|choose|approve|approve|strategy)\b', 3),
        (r'\b(option|trade.?off|consider|evaluate|judge|judgment)\b', 2),
        (r'\b(commander|chief|boss|your\s+call)\b', 1),
    ],
    'monitor': [
        (r'\b(monitor|watch|track|observe|alert|notify|poll|watch)\b', 3),
        (r'\b(fare\s+watch|price\s+watch|availability|daily|hourly|weekly|ongoing)\b', 2),
        (r'\b(continuous|recurring|schedule|background)\b', 1),
    ],
    'maintain': [
        (r'\b(maintain|clean|prune|purge|archive|backup|rotate|refresh|sync|re-?index)\b', 3),
        (r'\b(log|cache|database|index|token|credential|cookie|keepalive)\b', 2),
        (r'\b(routine|periodic|housekeeping|upkeep)\b', 1),
    ],
}

# ─── Subtype scoring patterns ─────────────────────────────────────────────────

SUBTYPE_PATTERNS: dict[str, list[str]] = {
    'research.cruise_intel':   [r'\bcruise\b', r'\bship\b', r'\bsailing\b', r'\bvoyage\b', r'\bcabin\b', r'\bembark\b'],
    'research.flight':         [r'\bflight\b', r'\bairline\b', r'\bairfare\b', r'\bair\b', r'\bairport\b', r'\bden\b'],
    'research.destination':    [r'\bweather\b', r'\bcity\b', r'\bport\b', r'\bdestination\b', r'\bcountry\b', r'\bbergen\b'],
    'research.general':        [],
    'build.mcp_tool':          [r'\bmcp\b', r'\btool\b'],
    'build.skill':             [r'\bskill\b'],
    'build.daemon':            [r'\bdaemon\b', r'\bservice\b', r'\bwatcher\b', r'\btimer\b'],
    'build.script':            [r'\bscript\b', r'\.py\b', r'\.sh\b'],
    'build.general':           [],
    'draft.email':             [r'\bemail\b', r'\bmessage\b', r'\bletter\b'],
    'draft.proposal':          [r'\bproposal\b', r'\bquote\b'],
    'draft.itinerary':         [r'\bitinerary\b'],
    'draft.general':           [],
    'validate.financial':      [r'\b(fpd|payment|commission|balance|\$|dollar|financial)\b'],
    'validate.dossier':        [r'\bdossier\b'],
    'validate.booking':        [r'\bbooking\b', r'\breservation\b'],
    'validate.general':        [],
    'decide.strategy':         [r'\bstrategy\b', r'\bstrategic\b'],
    'decide.client':           [r'\bclient\b', r'\bpassenger\b'],
    'decide.finance':          [r'\bfinance\b', r'\bbudget\b'],
    'decide.general':          [],
    'monitor.fare_watch':      [r'\bfare\b', r'\bprice\b', r'\brate\b'],
    'monitor.general':         [],
    'maintain.credentials':    [r'\bcredential\b', r'\bcookie\b', r'\btoken\b', r'\bauth\b'],
    'maintain.logs':           [r'\blog\b', r'\bprune\b', r'\barchive\b'],
    'maintain.general':        [],
}

# ─── Complexity scoring ───────────────────────────────────────────────────────

COMPLEXITY_BUMPS: list[tuple[str, int]] = [
    # Critical triggers (+2)
    (r'\b(urgent|p0|critical|deadline|overdue|immediately|asap|emergency)\b', 2),
    (r'\blegal\b|\bcompliance\b|\bcontract\b|\bregulat\b', 2),
    # Financial triggers (+2)
    (r'\$[\d,]+|\bcommission\b|\bfpd\b|\bpayment\b|\bbalance\b|\bfinancial\b', 2),
    # Booking ID pattern (+1)
    (r'\b[0-9]{6,}\b', 1),
    # Scope/multi-step (+1)
    (r'\b(multiple|several|all|every|comprehensive|full|complete|across\s+all)\b', 1),
    (r'\b(analyze|synthesize|compare|evaluate|deep\s+dive|thorough)\b', 1),
    (r'\b(multi|cross.?domain|multi.?step)\b', 1),
    # Long description (+1)
]


def classify(task_desc: str) -> Classification:
    text = task_desc.lower()

    # ── Score task types ──
    type_scores: dict[str, float] = {t: 0.0 for t in TASK_TYPES}
    for task_type, patterns in TYPE_PATTERNS.items():
        for pattern, weight in patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            type_scores[task_type] += matches * weight

    best_type = max(type_scores, key=lambda t: type_scores[t])
    best_score = type_scores[best_type]

    if best_score == 0:
        best_type = 'research'
        confidence = 0.3
    else:
        total = sum(type_scores.values())
        confidence = best_score / total if total > 0 else 0.5

    # ── Score subtypes (only for matching type prefix) ──
    prefix = f'{best_type}.'
    subtype = f'{best_type}.general'
    best_subtype_score = 0

    for st, patterns in SUBTYPE_PATTERNS.items():
        if not st.startswith(prefix):
            continue
        score = sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))
        if score > best_subtype_score:
            best_subtype_score = score
            subtype = st

    # ── Complexity scoring ──
    complexity_score = 0

    for pattern, delta in COMPLEXITY_BUMPS:
        if re.search(pattern, text, re.IGNORECASE):
            complexity_score += delta

    # Client name presence bumps slightly
    for name in CLIENT_NAMES:
        if name in text:
            complexity_score += 1
            break  # Only once, even if multiple clients mentioned

    # Word count contributes
    word_count = len(task_desc.split())
    if word_count > 30:
        complexity_score += 1
    if word_count > 60:
        complexity_score += 1

    if complexity_score >= 5:
        complexity = 'critical'
    elif complexity_score >= 3:
        complexity = 'complex'
    elif complexity_score >= 1:
        complexity = 'medium'
    else:
        complexity = 'simple'

    # decide always escalates to critical
    if best_type == 'decide':
        complexity = 'critical'

    return Classification(
        task_type=best_type,
        subtype=subtype,
        complexity=complexity,
        confidence=round(confidence, 2),
    )


def classify_to_dict(task_desc: str) -> dict:
    c = classify(task_desc)
    return {
        'task_type': c.task_type,
        'subtype': c.subtype,
        'complexity': c.complexity,
        'confidence': c.confidence,
    }


if __name__ == '__main__':
    desc = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Research Bergen weather July 2027'
    result = classify(desc)
    print(f"Type:       {result.task_type}")
    print(f"Subtype:    {result.subtype}")
    print(f"Complexity: {result.complexity}")
    print(f"Confidence: {result.confidence:.0%}")
