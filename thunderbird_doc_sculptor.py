#!/usr/bin/env python3
"""
THUNDERBIRD DOCUMENT SCULPTOR
D2M Dreams2Memories Travel, LLC
Version: 1.0.0 · 2026-03-23

Reduces Commander editing burden — three-pass polish applied to every
outbound draft BEFORE it reaches Commander review.

  PASS 1 — TONE: Match relationship tier (Friends/Client/Vendor/Prospect)
  PASS 2 — FORMAT: D2M structure, length, scannability
  PASS 3 — VOICE: Commander's real patterns from voice ledger

INTEGRATION POINTS (add one line to each):
  thunderbird_dani_engine.py  → call sculpt_for_dani() at Artist phase end
  thunderbird_commander_inbox.py → call sculpt_for_reply() before queue

CLI:
  python thunderbird_doc_sculptor.py <draft_file_or_text> [tier]
  python thunderbird_doc_sculptor.py --learn   (extract principles from log)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, date

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CONFIG_DIR      = THUNDERBIRD_DIR / "config"
LOGS_DIR        = THUNDERBIRD_DIR / "logs"
DATA_DIR        = THUNDERBIRD_DIR / "data"

VOICE_EXAMPLES_FILE      = CONFIG_DIR / "voice_examples.json"
SCULPTOR_PRINCIPLES_FILE = CONFIG_DIR / "sculptor_principles.json"
SCULPTOR_LOG_FILE        = LOGS_DIR   / "sculptor.log"

# ─── Relationship tiers ───────────────────────────────────────────────────────

TIERS = {
    "friends_family": {
        "label":    "Friends & Family",
        "warmth":   "highest — these are people John loves",
        "formality":"casual, personal, natural",
        "length":   "as long as feels right — not a transaction",
    },
    "client": {
        "label":    "Client",
        "warmth":   "warm and professional",
        "formality":"polished but never stiff",
        "length":   "concise — respect their time",
    },
    "vendor": {
        "label":    "Vendor / Supplier",
        "warmth":   "professional",
        "formality":"transactional",
        "length":   "brief, action-oriented",
    },
    "prospect": {
        "label":    "Prospect",
        "warmth":   "inviting but never pushy",
        "formality":"polished",
        "length":   "short — earn the next message",
    },
}

# ─── Default principles (override by sculptor_principles.json) ────────────────

DEFAULT_PRINCIPLES = {
    "always": [
        "Short sentences. Warm but certain.",
        "Lead with the answer, not the reasoning. No preamble.",
        "Never corporate-speak.",
        "Brand is ALWAYS 'Dreams2Memories Travel, LLC'. Never 'Love Group Travel'.",
        "Sign-off: 'Thanks' or 'Thank you'. NEVER 'Best' or 'Best regards'.",
        "Phone 719-291-0742 is personal — given selectively, never in mass comms.",
        "No trailing summaries or recaps at the end.",
    ],
    "format": [
        "Max 3 sentences per paragraph.",
        "If listing items, use line breaks — not bullet walls.",
        "Subject lines: direct, descriptive, not clever.",
        "No redundant closing sentence that just restates the opener.",
    ],
    "tone": [
        "Validate feelings before problem-solving.",
        "Correct misinformation gently but directly.",
        "Match the energy of the recipient's last message.",
        "Confident in recommendation, not pushy in approach.",
        "No filler phrases: 'I hope this finds you well', 'Please don't hesitate', etc.",
    ],
}

# ─── Core helpers ─────────────────────────────────────────────────────────────

def load_voice_examples(tier: str = None) -> list:
    if not VOICE_EXAMPLES_FILE.exists():
        return []
    try:
        with open(VOICE_EXAMPLES_FILE) as f:
            data = json.load(f)
        examples = data if isinstance(data, list) else data.get("examples", [])
        if tier:
            tier_examples = [e for e in examples if e.get("tier") == tier]
            return (tier_examples or examples)[:5]
        return examples[:5]
    except Exception:
        return []


def load_principles() -> dict:
    if SCULPTOR_PRINCIPLES_FILE.exists():
        try:
            with open(SCULPTOR_PRINCIPLES_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_PRINCIPLES


def _log(client: str, tier: str, changes: list, confidence: float):
    try:
        SCULPTOR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts":         datetime.now().isoformat(),
            "client":     client,
            "tier":       tier,
            "changes":    changes,
            "confidence": confidence,
        }
        with open(SCULPTOR_LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ─── Main sculpt engine ───────────────────────────────────────────────────────

def sculpt(
    draft:       str,
    tier:        str = "client",
    context:     str = "",
    client_name: str = "",
) -> dict:
    """
    Apply three-pass polish to a draft.

    Returns dict:
        polished      – cleaned draft text
        changes       – list of specific changes made
        confidence    – 0.0–1.0
        tier_applied  – tier used
        error         – present only on failure
    """
    tier_info = TIERS.get(tier, TIERS["client"])
    examples   = load_voice_examples(tier)
    principles = load_principles()

    voice_block = ""
    if examples:
        voice_block = "\n\nCOMMANDER'S ACTUAL VOICE EXAMPLES (use these as the target register):\n"
        for i, ex in enumerate(examples[:3], 1):
            text = ex.get("text", str(ex)) if isinstance(ex, dict) else str(ex)
            voice_block += f"Example {i}: {text}\n"

    system = f"""You are the D2M Document Sculptor for Dreams2Memories Travel, LLC.

MISSION: Polish drafts to reduce Commander John Loucks' editing burden.
He edits for: tone · format · focus · attitude.
Your job: catch all four BEFORE he sees the draft.

RELATIONSHIP TIER: {tier_info['label']}
  Warmth:    {tier_info['warmth']}
  Formality: {tier_info['formality']}
  Length:    {tier_info['length']}
{f'  Client:    {client_name}' if client_name else ''}

ALWAYS APPLY:
{chr(10).join(f'  • {p}' for p in principles.get('always', DEFAULT_PRINCIPLES['always']))}

FORMAT RULES:
{chr(10).join(f'  • {p}' for p in principles.get('format', DEFAULT_PRINCIPLES['format']))}

TONE RULES:
{chr(10).join(f'  • {p}' for p in principles.get('tone', DEFAULT_PRINCIPLES['tone']))}
{voice_block}

Return ONLY valid JSON — no markdown, no explanation outside the JSON:
{{
  "polished":     "<the polished draft — preserve all factual content>",
  "changes":      ["<specific change 1>", "<specific change 2>"],
  "confidence":   <0.0–1.0>,
  "tier_applied": "{tier}"
}}"""

    user_msg = (
        f"CONTEXT: {context}\n\nDRAFT TO POLISH:\n{draft}"
        if context else
        f"DRAFT TO POLISH:\n{draft}"
    )

    try:
        result = subprocess.run(
            ["claude", "--print", "--output-format", "json", "-p", user_msg],
            input=system,
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "ANTHROPIC_LOG": "error"},
        )
        out = result.stdout.strip()
        start = out.find("{")
        end   = out.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(out[start:end])
        return {
            "polished": draft, "changes": [], "confidence": 0.0,
            "tier_applied": tier, "error": "No JSON in response",
        }
    except subprocess.TimeoutExpired:
        return {
            "polished": draft, "changes": [], "confidence": 0.0,
            "tier_applied": tier, "error": "Timeout (60s)",
        }
    except Exception as e:
        return {
            "polished": draft, "changes": [], "confidence": 0.0,
            "tier_applied": tier, "error": str(e),
        }


# ─── Integration hooks ────────────────────────────────────────────────────────

def sculpt_for_dani(draft: str, client_info: dict) -> tuple:
    """
    Hook for thunderbird_dani_engine.py — call at end of Artist phase.

    Usage:
        from thunderbird_doc_sculptor import sculpt_for_dani
        polished, changes = sculpt_for_dani(artist_draft, {
            "name": client.name,
            "tier": client.tier,   # friends_family | client | vendor | prospect
            "context": thread_summary
        })

    Returns: (polished_text, changes_list)
    """
    result = sculpt(
        draft,
        tier=client_info.get("tier", "client"),
        context=client_info.get("context", ""),
        client_name=client_info.get("name", ""),
    )
    _log(
        client_info.get("name", "dani"),
        client_info.get("tier", "client"),
        result.get("changes", []),
        result.get("confidence", 0.0),
    )
    return result.get("polished", draft), result.get("changes", [])


def sculpt_for_reply(draft: str, thread_context: str = "", tier: str = "client") -> tuple:
    """
    Hook for thunderbird_commander_inbox.py — call before Commander review queue.

    Usage:
        from thunderbird_doc_sculptor import sculpt_for_reply
        polished, changes = sculpt_for_reply(generated_reply, thread_summary, "client")

    Returns: (polished_text, changes_list)
    """
    result = sculpt(draft, tier=tier, context=thread_context)
    _log("inbox_reply", tier, result.get("changes", []), result.get("confidence", 0.0))
    return result.get("polished", draft), result.get("changes", [])


# ─── Learning loop (--learn flag) ────────────────────────────────────────────

def run_learning_loop():
    """
    Extract principles from sculptor.log (last 7 days of changes).
    Update sculptor_principles.json with refined rules.
    Run nightly via cron or call with --learn.
    """
    if not SCULPTOR_LOG_FILE.exists():
        print("No sculptor.log yet — nothing to learn from.")
        return

    entries = []
    with open(SCULPTOR_LOG_FILE) as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except Exception:
                continue

    if not entries:
        print("Log empty.")
        return

    # Collect all changes from recent entries
    all_changes = []
    for e in entries[-200:]:  # last 200 sculpt operations
        all_changes.extend(e.get("changes", []))

    if not all_changes:
        print("No changes recorded yet.")
        return

    prompt = f"""You are analyzing D2M Document Sculptor change logs to extract durable writing principles.

CHANGES LOG (last {len(all_changes)} polish operations):
{json.dumps(all_changes, indent=2)}

From this log, extract the top 5 patterns that appear repeatedly.
Turn each pattern into a principle for the sculptor's next runs.

Return JSON:
{{
  "always": ["principle 1", "principle 2"],
  "format": ["principle 1"],
  "tone":   ["principle 1", "principle 2"]
}}

Include ONLY principles supported by repeated evidence in the log.
Merge with existing rules, do not duplicate."""

    try:
        result = subprocess.run(
            ["claude", "--print", "--output-format", "json", "-p", prompt],
            capture_output=True, text=True, timeout=60,
        )
        out = result.stdout.strip()
        start = out.find("{")
        end   = out.rfind("}") + 1
        if start >= 0 and end > start:
            new_principles = json.loads(out[start:end])
            # Merge with existing
            existing = load_principles()
            for key in ["always", "format", "tone"]:
                combined = list(dict.fromkeys(
                    existing.get(key, []) + new_principles.get(key, [])
                ))
                existing[key] = combined[:12]  # cap at 12 per category
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(SCULPTOR_PRINCIPLES_FILE, "w") as f:
                json.dump(existing, f, indent=2)
            print(f"Principles updated. {sum(len(v) for v in existing.values())} total rules.")
        else:
            print("No JSON in learning response.")
    except Exception as e:
        print(f"Learning loop error: {e}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _print_result(original: str, result: dict):
    polished = result.get("polished", original)
    changes  = result.get("changes", [])
    conf     = result.get("confidence", 0.0)
    err      = result.get("error")

    orig_words = len(original.split())
    poly_words = len(polished.split())
    delta      = poly_words - orig_words
    sign       = "+" if delta >= 0 else ""

    print(f"\n{'='*60}")
    print(f"SCULPTOR — {result.get('tier_applied', 'client').upper()}")
    print(f"Words: {orig_words} → {poly_words} ({sign}{delta})  Confidence: {conf:.0%}")
    if err:
        print(f"⚠  Error: {err}")
    print(f"Changes ({len(changes)}):")
    for i, c in enumerate(changes, 1):
        print(f"  {i}. {c}")
    print(f"{'='*60}")
    print("\nPOLISHED DRAFT:\n")
    print(polished)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--learn":
        run_learning_loop()
        sys.exit(0)

    tier       = sys.argv[2] if len(sys.argv) > 2 else "client"
    draft_path = Path(sys.argv[1])

    if draft_path.exists():
        draft_text = draft_path.read_text()
    else:
        draft_text = sys.argv[1]  # treat arg as raw text

    result = sculpt(draft_text, tier=tier)
    _print_result(draft_text, result)
