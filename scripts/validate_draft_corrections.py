#!/usr/bin/env python3
"""
validate_draft_corrections.py — Thunderbird Wing | A7 Sterling | 2026-06-04

PURPOSE: Gate before Gmail draft creation. Validates every Commander correction is
reflected in the final draft. Blocks if ANY correction is unaccounted for.

USAGE:
    python3 scripts/validate_draft_corrections.py --client "Ely" --draft output/Ely_TripValidation_v4_gmail.html

EXIT CODES:
    0 = PASS  — all corrections verified, draft may proceed to Gmail
    1 = FAIL  — one or more corrections not verified, BLOCK draft creation

INTEGRATION: Wire before create_gmail_draft_direct.py in all client product pipelines.
    python3 scripts/validate_draft_corrections.py --client Ely --draft $DRAFT_PATH || exit 1

POLARITY LOGIC:
    Each correction is split on commas into clauses. Each clause is classified:
      - EXPECT-ABSENT: contains negation markers (see NEGATION_MARKERS below)
      - EXPECT-PRESENT: all other clauses
    A key term is extracted from each clause for matching.
    Polarity and extracted term are ALWAYS printed — the gate is auditable.

METRIC: 0 client drafts created without passing this gate.
OWNER: Sterling (A7)
"""

import argparse
import html
import re
import sys
from pathlib import Path


# ── Path resolution ────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CORRECTIONS_DIR = REPO_ROOT / "corrections"

# ── Polarity: words that signal "this thing should NOT appear in the draft" ───
# "deferred" is intentionally NOT in this list — deferred = status-present, not absent.
# "CFAR" dropped → eliminate CFAR → absent. "deferred payment" → present (see spec).
NEGATION_MARKERS = {
    "eliminate",
    "drop",
    "dropped",
    "remove",
    "removed",
    "cancel",
    "cancelled",
    "omit",
    "exclude",
    "excluded",
    "without",
    "no longer",
    "absent",
    "none",
    "delete",
    "deleted",
    "strip",
    "stripped",
    "suppress",
    "suppressed",
}

# Stop words — never use these alone as a key term (too generic for reliable matching).
# Includes common correction imperative verbs that describe the action, not the subject.
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "this", "that", "be",
    "as", "are", "was", "were", "all", "both", "only", "also", "not", "no",
    "do", "does", "did", "have", "has", "had", "will", "would", "should",
    "may", "can", "per", "via", "vs", "nights", "night", "days", "day",
    # Correction imperative verbs — describe action, not the subject term
    "add", "use", "use", "keep", "move", "update", "change", "include",
    "ensure", "confirm", "confirmed", "note", "make", "set", "put",
}


def strip_html(text: str) -> str:
    """
    Strip HTML tags and decode entities. Collapse whitespace.
    Ensures 'At Six' isn't split across tag boundaries.
    """
    text = html.unescape(text)
    # Remove style and script blocks entirely
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def classify_clause(clause: str) -> tuple[str, str, str]:
    """
    Classify a correction clause into polarity and extract the key search term.

    Returns: (polarity, key_term, explanation)
      polarity: "EXPECT-PRESENT" or "EXPECT-ABSENT"
      key_term: the salient term to search for in the draft
      explanation: human-readable string for audit output
    """
    clause_lower = clause.lower()

    # Detect negation — word-boundary match to prevent substring false positives.
    # "cancel" must not match inside "cancellation"; "drop" must not match "backdrop".
    # "no longer" has a space so re.escape + \b on each word handles it correctly.
    polarity = "EXPECT-PRESENT"
    matched_marker = None
    for marker in sorted(NEGATION_MARKERS, key=len, reverse=True):  # longest-first
        pattern = r"\b" + re.escape(marker) + r"\b"
        if re.search(pattern, clause_lower):
            polarity = "EXPECT-ABSENT"
            matched_marker = marker
            break

    # Extract key term: prefer CAPITALIZED multi-word phrases (proper nouns).
    # Pattern: consecutive ALPHA-ONLY words starting with uppercase.
    # Does NOT span across digits or ordinals (Night 1 → stops before "1"),
    # preventing over-long phrases like "At Six Night" that won't match drafts.
    proper_noun_re = re.compile(r"(?:[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)")
    proper_nouns = proper_noun_re.findall(clause)

    # Filter out negation markers that happen to be capitalized, stop words,
    # and tokens that are immediately followed by a digit (ordinals: Night 1, Day 2)
    filtered = []
    for p in proper_nouns:
        if p.lower() in NEGATION_MARKERS:
            continue
        if p.lower() in STOP_WORDS:
            continue
        if len(p) <= 2:
            continue
        # Check whether this phrase is immediately followed by a digit in the clause
        # — if so, truncate to avoid absorbing ordinals into the key term
        m = re.search(re.escape(p) + r"\s+\d", clause)
        if m:
            # Use only the first word of the phrase (e.g., "At Six" not "At Six Night")
            first_two = " ".join(p.split()[:2])
            filtered.append(first_two)
        else:
            filtered.append(p)

    if filtered:
        # Use the longest proper noun phrase as the key term
        key_term = max(filtered, key=len)
    else:
        # Fall back: all tokens, strip stop words and negation markers
        tokens = re.findall(r"\b[a-zA-Z]+\b", clause)
        meaningful = [
            t for t in tokens
            if t.lower() not in STOP_WORDS
            and t.lower() not in NEGATION_MARKERS
            and len(t) > 2
        ]
        if meaningful:
            key_term = meaningful[0]  # First meaningful token
        else:
            key_term = clause.strip()  # Last resort — full clause

    explanation = f"polarity={polarity}, term='{key_term}'"
    if matched_marker:
        explanation += f", negation='{matched_marker}'"

    return polarity, key_term, explanation


def load_corrections(corrections_file: Path) -> list[str]:
    """
    Parse corrections file. Return list of raw correction text strings.
    """
    if not corrections_file.exists():
        return []

    corrections = []
    with open(corrections_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("**Text:**"):
                text = stripped.replace("**Text:**", "").strip()
                if text:
                    corrections.append(text)
    return corrections


def split_correction_into_clauses(correction: str) -> list[str]:
    """
    Split a correction string into individual clauses on commas.
    Each clause is stripped. Empty clauses are discarded.
    """
    return [c.strip() for c in correction.split(",") if c.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Validate that all Commander corrections are present in the draft."
    )
    parser.add_argument(
        "--client", required=True, help="Client name (e.g., Ely, Nichols, Furlow)"
    )
    parser.add_argument(
        "--draft", required=True, help="Path to the draft file (HTML or MD)"
    )
    args = parser.parse_args()

    client = args.client.strip()
    draft_path = Path(args.draft)
    if not draft_path.is_absolute():
        draft_path = REPO_ROOT / draft_path

    # ── 1. Load draft content ──────────────────────────────────────────────────
    if not draft_path.exists():
        print(f"[ERROR] Draft file not found: {draft_path}", file=sys.stderr)
        sys.exit(1)

    raw_draft = draft_path.read_text(encoding="utf-8")
    draft_text = strip_html(raw_draft)
    draft_lower = draft_text.lower()

    # ── 2. Load corrections ────────────────────────────────────────────────────
    corrections_file = CORRECTIONS_DIR / f"{client}_corrections.md"
    corrections = load_corrections(corrections_file)

    if not corrections:
        print(f"CHECKING: {client} corrections vs draft...")
        print(f"[INFO] No corrections file found at {corrections_file.relative_to(REPO_ROOT)}")
        print(f"       Nothing to validate. Proceeding.")
        print(f"RESULT: PASS — no corrections on file")
        sys.exit(0)

    # ── 3. Validate each correction ────────────────────────────────────────────
    print(f"CHECKING: {client} corrections vs draft...")
    print(f"  Draft:       {draft_path.name}")
    print(f"  Corrections: {corrections_file.relative_to(REPO_ROOT)}")
    print(f"  Count:       {len(corrections)} correction(s)")
    print()

    failures = []
    passes = []

    for corr_idx, correction in enumerate(corrections, 1):
        clauses = split_correction_into_clauses(correction)
        print(f"  Correction {corr_idx}: \"{correction}\"")

        for clause in clauses:
            polarity, key_term, explanation = classify_clause(clause)
            print(f"    Clause: \"{clause}\" → {explanation}")

            key_term_lower = key_term.lower()
            found_in_draft = key_term_lower in draft_lower

            if polarity == "EXPECT-PRESENT":
                if found_in_draft:
                    result = f"[PASS] \"{key_term}\" — found in draft"
                    passes.append(result)
                else:
                    result = f"[FAIL] \"{key_term}\" — NOT FOUND in draft"
                    failures.append((clause, key_term, polarity))
                print(f"    {result}")

            else:  # EXPECT-ABSENT
                if not found_in_draft:
                    result = f"[PASS] \"{key_term}\" absent — confirmed absent"
                    passes.append(result)
                else:
                    result = f"[FAIL] \"{key_term}\" should be ABSENT — but FOUND in draft"
                    failures.append((clause, key_term, polarity))
                print(f"    {result}")

        print()

    # ── 4. Final verdict ───────────────────────────────────────────────────────
    if failures:
        print(f"RESULT: BLOCKED — {len(failures)} correction(s) not verified.")
        print()
        print("  Unresolved:")
        for clause, key_term, polarity in failures:
            direction = "must appear in draft" if polarity == "EXPECT-PRESENT" else "must NOT appear in draft"
            print(f"    - Clause: \"{clause}\" | Term: \"{key_term}\" | {direction}")
        print()
        print("  Fix draft before creating Gmail draft.")
        sys.exit(1)
    else:
        print(f"RESULT: PASS — all {len(passes)} check(s) verified.")
        print(f"        Safe to proceed to Gmail draft creation.")
        sys.exit(0)


if __name__ == "__main__":
    main()
