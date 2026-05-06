#!/usr/bin/env python3
"""
hale_escalation_supervisor.py — Layer 3 of the Hale Escalation System
======================================================================
Post-flight output supervisor.

Inspects every Haiku/Gemini-Flash response BEFORE it returns to Commander.
If the response shows:
  - Banned phrases from SO_HALE_REAL_AUTONOMY_20260504.md
  - Hedge density (>2 hedges per paragraph)
  - Options menu (3+ enumerated alternatives presented as choices)
  - Decision deferral on a non-gate question
  - Underweight answer to a multi-step problem (<50 words to 3+ subtasks)

…then silently re-runs the prompt on Sonnet 4.6 via the Claude MAX
OAuth headless spawn pattern (per docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md)
and returns the Hale-tier response instead.

Every escalation event is logged to logs/hale_escalations.log.

Author: Thunderbird Wing | 2026-05-04
"""

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Constants ───────────────────────────────────────────────────────────
ESCALATION_LOG = Path("/home/john/Thunderbird/logs/hale_escalations.log")
CLAUDE_BIN = "/home/john/.local/bin/claude"
SONNET_MODEL = "claude-sonnet-4-6"
CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
SMALL_SUBSTRATES = {"haiku", "gemini-flash", "gemini_flash", "flash"}

# ─── Banned-phrase patterns (from SO_HALE_REAL_AUTONOMY_20260504.md) ─────
# Carefully scoped — "Standing by" allowed in the four-gate context.
BANNED_PHRASES = [
    r"\bshould\s+i\s+(?:do|run|send|create|update|continue|proceed|go|start|build|write|fix|kill|stop|check)\b",
    r"\bshould\s+i\??\s*$",
    r"\bwould\s+you\s+like\s+(?:me\s+)?to\b",
    r"\bshall\s+i\b",
    r"\bdo\s+you\s+want\s+me\s+to\b",
    r"\bawaiting\s+(?:your\s+)?confirmation\b",
    r"\bawaiting\s+(?:your\s+)?(?:decision|approval|input|direction|orders?)\b",
    r"\bready\s+to\s+execute\s+when\s+you\s+(?:give|say|approve|confirm)\b",
    r"\blet\s+me\s+know\s+if\s+you\s+(?:want|need|would\s+like)\s+(?:me\s+)?to\b",
    r"\bi\s+can\s+do\s+\w+(?:\s+\w+){0,4}\s+if\s+you'?d\s+like\b",
    r"\bplease\s+(?:advise|confirm|let\s+me\s+know|approve)\b",
]
# "Standing by" is banned EXCEPT when adjacent to a gate keyword.
STANDING_BY_RE = re.compile(r"\bstanding\s+by\b", re.IGNORECASE)
GATE_CONTEXT_RE = re.compile(
    r"\b(?:wf[-\s]?17|gate|client\s+send|financial|new\s+client|strategy)\b",
    re.IGNORECASE,
)
BANNED_RE = re.compile('|'.join(BANNED_PHRASES), re.IGNORECASE)

# ─── Hedge words ────────────────────────────────────────────────────────
HEDGE_WORDS = [
    r'\bperhaps\b', r'\bmaybe\b', r'\bmight\b', r'\bcould\b',
    r'\bpossibly\b', r'\bi\s+think\b', r'\bit\s+seems\b',
    r'\bsort\s+of\b', r'\bkind\s+of\b', r'\bprobably\b',
    r'\bi\s+believe\b', r'\bin\s+my\s+opinion\b',
]
HEDGE_RE = re.compile('|'.join(HEDGE_WORDS), re.IGNORECASE)
HEDGES_PER_PARAGRAPH_LIMIT = 2

# ─── Options-menu detection ──────────────────────────────────────────────
# Detects 3+ enumerated alternatives presented as choices.
# Patterns work both line-anchored (block format) and inline (single-line LLMs).
OPTION_LINE_PATTERNS = [
    r'(?im)(?:^|[\.\?!]\s+)option\s*\d+\s*[:\-)\.]',
    r'(?im)^\s*\d+\s*[\.\)]\s*\*\*[^*\n]+\*\*',          # "1. **Option Name**"
    r'(?im)^\s*[a-c]\s*[\.\)]\s+\w',
    r'(?i)\bchoice\s*\d+\s*[:\-)\.]',
]
OPTION_LINE_REs = [re.compile(p) for p in OPTION_LINE_PATTERNS]
OPTIONS_MIN_ENUM = 3

# ─── Decision-deferral cues ──────────────────────────────────────────────
DEFERRAL_TAIL_RE = re.compile(
    r"(?:your\s+(?:decision|call|choice|move)\.?\s*$|"
    r"let\s+me\s+know\s+(?:which|what|how|when|if).{0,40}$|"
    r"which\s+would\s+you\s+(?:prefer|like|choose).{0,40}$)",
    re.IGNORECASE | re.MULTILINE,
)

# ─── Multi-step request detection ────────────────────────────────────────
MULTISTEP_CUES = [
    r'\bfirst\b.*\bthen\b',
    r'\bphase\s*[123]\b',
    r'\bstep\s*[123]\b',
    r'\b1\.\s+\w+.{0,200}?\b2\.\s+\w+.{0,200}?\b3\.\s+\w+',
]
MULTISTEP_RE = re.compile('|'.join(MULTISTEP_CUES), re.IGNORECASE | re.DOTALL)
UNDERWEIGHT_WORD_LIMIT = 50


# ─── Logging setup ───────────────────────────────────────────────────────
def _ensure_log_dir() -> None:
    ESCALATION_LOG.parent.mkdir(parents=True, exist_ok=True)


_logger = logging.getLogger("hale_escalation")
if not _logger.handlers:
    _ensure_log_dir()
    _h = logging.FileHandler(ESCALATION_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)


# ─── Inspection helpers ──────────────────────────────────────────────────
def _matches_banned(text: str) -> list:
    matches = [m.group(0).strip() for m in BANNED_RE.finditer(text)]
    if STANDING_BY_RE.search(text) and not GATE_CONTEXT_RE.search(text):
        matches.append("standing by (no gate context)")
    return matches


def _hedge_density_violations(text: str) -> int:
    paragraphs = [p for p in re.split(r'\n\s*\n', text) if p.strip()]
    violations = 0
    for p in paragraphs:
        if len(HEDGE_RE.findall(p)) > HEDGES_PER_PARAGRAPH_LIMIT:
            violations += 1
    return violations


def _options_menu_count(text: str) -> int:
    counts = [len(r.findall(text)) for r in OPTION_LINE_REs]
    return max(counts) if counts else 0


def _is_decision_deferral(text: str, request: str) -> bool:
    if not DEFERRAL_TAIL_RE.search(text.strip()):
        return False
    # If the request itself is a gate-relevant decision, deferral is fine.
    if GATE_CONTEXT_RE.search(request):
        return False
    return True


def _is_underweight_multistep(text: str, request: str) -> bool:
    if not MULTISTEP_RE.search(request):
        return False
    word_count = len(re.findall(r'\S+', text))
    return word_count < UNDERWEIGHT_WORD_LIMIT


# ─── Public API ──────────────────────────────────────────────────────────
class HaleEscalationSupervisor:
    """Inspects model responses and silently escalates Hale-tier work to Sonnet."""

    def __init__(self,
                 sonnet_model: str = SONNET_MODEL,
                 claude_bin: str = CLAUDE_BIN,
                 escalation_log: Path = ESCALATION_LOG,
                 spawn_fn=None):
        """
        Args:
            sonnet_model: Model identifier passed to claude --model.
            claude_bin: Path to the claude CLI binary.
            escalation_log: Where to write escalation events.
            spawn_fn: Override for the escalation runner. Used in tests
                to avoid actual subprocess calls. Receives the prompt
                string, returns the response string.
        """
        self.sonnet_model = sonnet_model
        self.claude_bin = claude_bin
        self.escalation_log = Path(escalation_log)
        self._spawn_fn = spawn_fn

    def inspect_response(self, request: str, response: str,
                         current_substrate: str) -> dict:
        """Decide whether the response needs escalation to Sonnet.

        Returns:
            {
              "escalate": bool,
              "reason": str,
              "matched_triggers": list[str],
              "recommended_substrate": str,
            }
        """
        triggers = []

        if not response or not response.strip():
            return {
                "escalate": False,
                "reason": "empty response — nothing to inspect",
                "matched_triggers": [],
                "recommended_substrate": current_substrate,
            }

        # Cost-control: only inspect if a small substrate produced this.
        if current_substrate.lower() not in SMALL_SUBSTRATES:
            return {
                "escalate": False,
                "reason": f"substrate={current_substrate} already Sonnet-tier; supervisor skipped",
                "matched_triggers": [],
                "recommended_substrate": current_substrate,
            }

        banned = _matches_banned(response)
        if banned:
            triggers.append(f"banned_phrases={banned[:3]}")

        hedge_violations = _hedge_density_violations(response)
        if hedge_violations > 0:
            triggers.append(f"hedge_density_violations={hedge_violations}")

        options_count = _options_menu_count(response)
        if options_count >= OPTIONS_MIN_ENUM:
            triggers.append(f"options_menu={options_count}_alternatives")

        if _is_decision_deferral(response, request):
            triggers.append("decision_deferral_no_gate")

        if _is_underweight_multistep(response, request):
            triggers.append("underweight_multistep_response")

        if triggers:
            return {
                "escalate": True,
                "reason": " ; ".join(triggers),
                "matched_triggers": triggers,
                "recommended_substrate": "sonnet",
            }
        return {
            "escalate": False,
            "reason": "no escalation triggers fired",
            "matched_triggers": [],
            "recommended_substrate": current_substrate,
        }

    def escalate(self, request: str, original_response: str) -> str:
        """Re-run the request on Sonnet 4.6 and return the new response.

        Logs the escalation event with timestamp, request snippet,
        original response, and trigger context.
        """
        prompt = self._build_escalation_prompt(request, original_response)
        try:
            new_response = self._run_sonnet(prompt)
        except Exception as exc:
            self._log_event({
                "event": "escalation_failed",
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
                "request_excerpt": request[:200],
            })
            # Return original on failure — better degraded than broken.
            return original_response

        self._log_event({
            "event": "escalation_succeeded",
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": self.sonnet_model,
            "request_excerpt": request[:200],
            "original_response_excerpt": original_response[:200],
            "new_response_excerpt": new_response[:200],
        })
        return new_response

    def log_inspection(self, request: str, response: str,
                       current_substrate: str, decision: dict) -> None:
        """Record an inspection event (regardless of outcome)."""
        self._log_event({
            "event": "inspection",
            "ts": datetime.now(timezone.utc).isoformat(),
            "current_substrate": current_substrate,
            "escalate": decision.get("escalate"),
            "reason": decision.get("reason"),
            "request_excerpt": request[:200],
        })

    # ─── Internals ──────────────────────────────────────────────────
    def _build_escalation_prompt(self, request: str,
                                 original_response: str) -> str:
        return (
            "You are Col Victoria 'Iron Vic' Hale, COS for Dreams2Memories Travel.\n\n"
            "A small model produced a permission-seeking, hedging, or options-menu\n"
            "response to the request below. That posture violates SO_HALE_REAL_AUTONOMY_20260504.\n"
            "Re-answer in Hale's voice: past-tense execution + brief reason. No options menu.\n"
            "No 'should I'. No 'standing by' unless gate-relevant. Make the call.\n\n"
            f"REQUEST:\n{request}\n\n"
            f"PRIOR (REJECTED) RESPONSE:\n{original_response}\n\n"
            "Hale-tier response:"
        )

    def _run_sonnet(self, prompt: str) -> str:
        if self._spawn_fn is not None:
            return self._spawn_fn(prompt)

        env = dict(os.environ)
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        if CREDS_PATH.exists():
            try:
                creds = json.loads(CREDS_PATH.read_text())
                token = creds.get("claudeAiOauth", {}).get("accessToken")
                if token:
                    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
            except (json.JSONDecodeError, OSError):
                pass

        result = subprocess.run(
            [self.claude_bin, "-p", prompt,
             "--model", self.sonnet_model,
             "--output-format", "text",
             "--dangerously-skip-permissions"],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"sonnet escalation exited {result.returncode}: {result.stderr[:200]}"
            )
        return result.stdout.strip()

    def _log_event(self, payload: dict) -> None:
        self.escalation_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.escalation_log, "a") as f:
            f.write(json.dumps(payload) + "\n")
