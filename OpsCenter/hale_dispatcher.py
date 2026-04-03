"""
Hale Brain Dispatcher
=====================
Three-brain routing for Col Victoria "Iron Vic" Hale, COO — Thunderbird Wing.

Brain 1: Qwen 3.6 Plus (OpenRouter, $0)   — ops, context, research, scan, summarize
Brain 2: Claude Sonnet (headless)         — reasoning, code, strategy, complex writing
Brain 3: DeepSeek (direct or OpenRouter)  — arbitration, high-stakes, brain disagreement
Self:    Hale handles directly             — simple, within institutional knowledge

Usage:
    from hale_dispatcher import HaleDispatcher
    hale = HaleDispatcher()
    result = hale.dispatch("Summarize the Furlow dossier and flag anything overdue.")

Author: Col Victoria "Iron Vic" Hale (COS) — built 2026-04-03
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# ── Paths ──
_ROOT = Path(__file__).resolve().parent.parent
_OPSCENTER = Path(__file__).resolve().parent
_STATE   = _ROOT / "hale_state.json"
_MEMORY  = _ROOT / "hale_memory.md"
_DECISIONS = _ROOT / "hale_decisions.md"
_BRIEF   = _ROOT / "hale_brief.md"
_PERSONA = _ROOT / "Personas" / "hale_cos.md"
_CONTEXT = _ROOT / "hale_session_context.md"  # Qwen deep scan output

# ── Env ──
load_dotenv(str(_ROOT / ".env"))
load_dotenv(str(_ROOT / ".env.telegram"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEEPSEEK_API_KEY   = os.getenv("DEEPSEEK_API_KEY", "")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")

QWEN_MODEL         = "qwen/qwen3.6-plus:free"
SONNET_MODEL       = "claude-sonnet-4-6"
OPUS_MODEL         = "claude-opus-4-6"
DEEPSEEK_MODEL     = "deepseek-chat"
DEEPSEEK_OR_MODEL  = "deepseek/deepseek-chat"  # OpenRouter proxy

MT = timezone(timedelta(hours=-6))


# ── Task classification ──

BRAIN1_KEYWORDS = {
    "summarize", "summary", "digest", "scan", "search", "find", "list",
    "read", "check", "status", "health", "what is", "what's", "how many",
    "count", "show me", "tell me", "who is", "when is", "lookup",
    "research", "intel", "brief", "report", "overview", "dossier",
}

BRAIN2_KEYWORDS = {
    "write", "draft", "compose", "create", "build", "code", "fix",
    "debug", "strategy", "analyze", "analyse", "recommend", "plan",
    "design", "propose", "explain", "why", "how to", "improve",
    "compare", "decide", "voice", "email", "proposal", "copy",
    # DeepSeek ruling 2026-04-03: multi-source synthesis → Brain 2
    "synthesize", "synthesis", "vs", "versus", "across", "compare across",
    "rank", "weigh", "tradeoff", "trade-off", "competitive brief",
    "which is better", "pros and cons", "evaluate",
}

# Brain 3 trigger: requires actual Brain 1 vs Brain 2 conflict, or explicit Commander command
# NOT triggered by keywords alone (DeepSeek ruling 2026-04-03)
BRAIN3_EXPLICIT_COMMANDS = {
    "arbitrate", "deepseek", "solomon", "get a ruling", "ask deepseek",
    "settle this", "third opinion",
}

SELF_PATTERNS = {
    "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
    "thanks", "thank you", "ok", "yes", "no", "got it", "understood",
    "confirm", "acknowledged", "standing by",
}


def classify_task(content: str) -> str:
    """
    Returns: 'brain1' | 'brain2' | 'brain3' | 'self'

    Routing rules (DeepSeek arbitrated 2026-04-03):
    - Brain 3: explicit Commander command only (not keyword-triggered)
    - Brain 2: reasoning, strategy, code, voice, OR multi-source synthesis
    - Brain 1: single-source retrieval, ops, scan, summarize
    - Self: simple greetings and direct acknowledgments
    """
    lower = content.lower().strip()

    # Brain 3: explicit command only — never keyword-triggered alone
    for kw in BRAIN3_EXPLICIT_COMMANDS:
        if kw in lower:
            return "brain3"

    # Brain 2: reasoning + multi-source synthesis
    for kw in BRAIN2_KEYWORDS:
        if kw in lower:
            return "brain2"

    # Brain 1: single-source ops/retrieval
    for kw in BRAIN1_KEYWORDS:
        if kw in lower:
            return "brain1"

    # Self: simple direct patterns
    for kw in SELF_PATTERNS:
        if lower.startswith(kw) or lower == kw:
            return "self"

    # Default: Brain 1 — safe, cheap, operational
    return "brain1"


# ── Brain 1: Qwen via OpenRouter ──

def _call_brain1(system: str, task: str, max_tokens: int = 2000) -> str:
    """Brain 1: Qwen 3.6 Plus via OpenRouter. $0/month."""
    if not OPENROUTER_API_KEY:
        return "[BRAIN1 ERROR] OPENROUTER_API_KEY not set."

    try:
        payload = json.dumps({
            "model": QWEN_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": task},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }, ensure_ascii=False).encode("utf-8")
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json; charset=utf-8",
                "HTTP-Referer": "https://d2mluxury.quest",
                "X-Title": "Thunderbird Wing - Hale Dispatcher",
            },
            data=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[BRAIN1 ERROR] Qwen failed: {e}"


# ── Brain 2: Claude headless (Sonnet or Opus) ──

def _call_brain2(task: str, model: str = SONNET_MODEL, max_words: int = 500) -> str:
    """
    Brain 2: headless Claude via `claude -p`.
    Receives Hale's digest + task — never raw files.
    """
    persona_text = ""
    if _PERSONA.exists():
        persona_text = _PERSONA.read_text()[:3000]  # First 3K of persona for context

    prompt = f"""{persona_text}

---
TASK FROM HALE:
{task}

Respond in max {max_words} words. Brief-first. No preamble."""

    try:
        env = {**os.environ, "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY}
        result = subprocess.run(
            ["claude", "-p", prompt, "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=120, env=env,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            err = result.stderr.strip()
            return f"[BRAIN2 ERROR] claude -p failed (rc={result.returncode}): {err[:300]}"
    except subprocess.TimeoutExpired:
        return "[BRAIN2 ERROR] Claude headless timed out (120s)."
    except FileNotFoundError:
        return "[BRAIN2 ERROR] `claude` not found in PATH."
    except Exception as e:
        return f"[BRAIN2 ERROR] {e}"


# ── Brain 3: DeepSeek arbitration ──

def _call_brain3(question: str) -> str:
    """Brain 3: DeepSeek — arbitration, disputes, high-stakes rulings. PII-free."""
    # Try direct DeepSeek API first
    if DEEPSEEK_API_KEY:
        try:
            resp = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are the Wing's arbitrator. Issue a clear, direct ruling. Max 500 tokens. No hedging."},
                        {"role": "user",   "content": question},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 402:
                pass  # Fallthrough to OpenRouter proxy
            else:
                return f"[BRAIN3 ERROR] DeepSeek direct: {e}"
        except Exception:
            pass  # Fallthrough to OpenRouter proxy

    # Fallback: OpenRouter proxy for DeepSeek
    if OPENROUTER_API_KEY:
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_OR_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are the Wing's arbitrator. Issue a clear, direct ruling. Max 500 tokens. No hedging."},
                        {"role": "user",   "content": question},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return "[DeepSeek via OR] " + data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[BRAIN3 ERROR] All DeepSeek routes failed: {e}"

    return "[BRAIN3 ERROR] No DeepSeek API key and no OpenRouter key available."


# ── State management ──

def load_state() -> dict:
    try:
        return json.loads(_STATE.read_text())
    except Exception:
        return {}


def save_state(state: dict):
    try:
        _STATE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(f"[STATE] Failed to save: {e}", file=sys.stderr)


def log_decision(decision: str, rationale: str, brain: str, outcome: str = "pending"):
    """Append an autonomous decision to hale_decisions.md."""
    ts = datetime.now(MT).strftime("%Y-%m-%d")
    entry = f"""
### {ts} — Autonomous Decision
**Decision:** {decision}
**Rationale:** {rationale}
**Brain used:** {brain}
**Outcome:** {outcome}
**Commander notified:** Next brief
**Disagreement logged:** No

"""
    try:
        existing = _DECISIONS.read_text()
        # Insert before the closing signature line
        if "Col Victoria" in existing:
            updated = existing.replace(
                "\n---\n\n*Col Victoria",
                entry + "\n---\n\n*Col Victoria"
            )
        else:
            updated = existing + entry
        _DECISIONS.write_text(updated)
    except Exception as e:
        print(f"[DECISIONS] Failed to log: {e}", file=sys.stderr)


# ── Hale system prompt builder ──

def _build_hale_system() -> str:
    """Load Hale's persona + memory + Qwen deep scan context."""
    base = ""
    if _PERSONA.exists():
        base = _PERSONA.read_text()

    # Inject memory
    mem_snippet = ""
    if _MEMORY.exists():
        mem_snippet = "\n\n---\n## LIVE MEMORY\n" + _MEMORY.read_text()[:2000]

    # Inject Qwen deep scan context (institutional knowledge)
    context_snippet = ""
    if _CONTEXT.exists():
        context_snippet = "\n\n---\n## WING CONTEXT (Qwen scan)\n" + _CONTEXT.read_text()[:4000]

    return base + mem_snippet + context_snippet


# ── Main dispatcher ──

class HaleDispatcher:
    """
    Hale's three-brain dispatcher.

    Usage:
        hale = HaleDispatcher()
        result = hale.dispatch("Draft a Telegram summary of the Furlow booking status.")
        print(result)

    Override:
        result = hale.dispatch(task, brain_override="opus")   # Commander OPUS: prefix
        result = hale.dispatch(task, brain_override="sonnet") # Commander Sonnet: prefix
    """

    def __init__(self):
        self.system = _build_hale_system()
        self.state  = load_state()
        self._brain_log: list[dict] = []

    def dispatch(self, task: str, brain_override: Optional[str] = None) -> str:
        """
        Classify task → route to correct brain → return result.

        brain_override: 'opus' | 'sonnet' | 'brain1' | 'brain2' | 'brain3' | None
        """
        start = time.time()

        # ── Determine brain ──
        if brain_override in ("opus", "sonnet"):
            brain  = "brain2"
            model  = OPUS_MODEL if brain_override == "opus" else SONNET_MODEL
            reason = f"Commander override: {brain_override.upper()}"
        elif brain_override in ("brain1", "brain2", "brain3"):
            brain  = brain_override
            model  = SONNET_MODEL
            reason = f"Explicit override: {brain_override}"
        else:
            brain  = classify_task(task)
            model  = SONNET_MODEL
            reason = "Auto-classified"

        # ── Dispatch ──
        if brain == "self":
            result    = self._handle_self(task)
            brain_tag = "Hale (self)"

        elif brain == "brain1":
            result    = _call_brain1(self.system, task)
            brain_tag = "Brain 1 (Qwen)"
            # Self-escalate on error
            if result.startswith("[BRAIN1 ERROR]"):
                result    = _call_brain2(f"{self.system}\n\nTASK: {task}", model=SONNET_MODEL)
                brain_tag = "Brain 2 (Sonnet — Qwen error escalation)"
                log_decision(
                    f"Escalated Qwen→Sonnet on: {task[:80]}",
                    "Qwen returned an error; task required reliable response.",
                    "Brain 2 (Sonnet)"
                )
                # Notify Commander of escalation (Padre's recommendation)
                self._escalation_note = f"Escalated to Sonnet — Qwen failed on: {task[:60]}"

        elif brain == "brain2":
            digest = f"{self.system[:500]}\n\nTASK: {task}"
            result = _call_brain2(digest, model=model)
            brain_tag = f"Brain 2 ({model.split('-')[1].title() if '-' in model else model})"

        elif brain == "brain3":
            # Strip PII before sending to DeepSeek
            clean_task = self._strip_pii(task)
            result     = _call_brain3(clean_task)
            brain_tag  = "Brain 3 (DeepSeek)"

        else:
            result    = self._handle_self(task)
            brain_tag = "Hale (self)"

        elapsed = round(time.time() - start, 1)

        # ── Log routing decision ──
        entry = {
            "ts":      datetime.now(MT).isoformat(),
            "task":    task[:100],
            "brain":   brain_tag,
            "reason":  reason,
            "elapsed": elapsed,
        }
        self._brain_log.append(entry)

        # Update state
        state = load_state()
        if "brain_routing_log" not in state:
            state["brain_routing_log"] = []
        state["brain_routing_log"] = (state["brain_routing_log"] + [entry])[-50:]  # Keep last 50
        save_state(state)

        return result

    def _handle_self(self, task: str) -> str:
        """Hale handles simple/direct tasks without spinning up a brain."""
        lower = task.lower().strip()

        if any(g in lower for g in ("hello", "hi", "hey", "good morning")):
            return "Good morning, Sir. Standing by."
        if any(g in lower for g in ("status", "health", "alive")):
            return "Wing operational. Thunderbird MCP: check localhost:8765. Goose: verify with `goose run --text test`. Standing by."
        if "brief" in lower:
            if _BRIEF.exists():
                return _BRIEF.read_text()
            return "No brief generated yet. Run hale_dispatcher.generate_brief() to produce one."
        return f"Acknowledged. Standing by on: {task[:100]}"

    def _strip_pii(self, text: str) -> str:
        """
        Remove client PII before sending to DeepSeek/Qwen.
        Strips: full names, booking refs, dollar amounts, email addresses.
        """
        # Email addresses
        text = re.sub(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b', '[EMAIL]', text, flags=re.IGNORECASE)
        # Booking refs (5-6 char alphanumeric)
        text = re.sub(r'\b[A-Z0-9]{5,6}\b', '[REF]', text)
        # Dollar amounts
        text = re.sub(r'\$[\d,]+(?:\.\d{2})?', '[AMOUNT]', text)
        # Known client names
        for name in ["Furlow", "Westbrook", "Lyons", "McLeod", "Britan", "Loucks", "Ely", "Darrow"]:
            text = text.replace(name, "[CLIENT]")
        return text

    def synthesize(self, raw_output: str, scan_type: str = "intel") -> str:
        """
        Read raw scan output and produce Hale's COO synthesis.
        Returns synthesis text only — caller appends raw data.

        scan_type hints: 'intel' | 'innovation' | 'tech' | 'booking' | 'commission' | 'general'
        """
        TYPE_PROMPTS = {
            "innovation": "Focus on: what's actionable for D2M, what threatens our model, what's a real opportunity vs noise. Flag anything that changes how we should use AI.",
            "tech":       "Focus on: tools we should adopt, tools we're using that have better alternatives, cost implications, anything that affects Thunderbird Wing infrastructure.",
            "intel":      "Focus on: what affects our cruise lines or travel industry, client trip impacts, geopolitical risks to active bookings, competitive threats.",
            "booking":    "Focus on: payment status changes, deadline alerts, anything requiring Commander action within 48 hours.",
            "commission": "Focus on: discrepancies, overdue amounts, anything that requires follow-up with suppliers.",
            "general":    "Focus on: what requires Commander attention, what can be handled autonomously, what can be filed.",
        }
        focus = TYPE_PROMPTS.get(scan_type, TYPE_PROMPTS["general"])

        # Strip PII before sending to Qwen if it's an intel/tech scan
        clean_output = raw_output if scan_type in ("booking", "commission") else self._strip_pii(raw_output)
        # Cap input to avoid token overflow
        if len(clean_output) > 8000:
            clean_output = clean_output[:8000] + "\n... [truncated for synthesis]"

        prompt = f"""You are Col Victoria "Iron Vic" Hale, COO — Thunderbird Wing, Dreams2Memories Travel, LLC.

A {scan_type} scan just completed. Read the output below and provide your COO synthesis.

{focus}

Format your synthesis as:
**HALE ({scan_type.upper()} SYNTHESIS)**
[2-4 sentences: what matters, what to act on, what to watch. Commander-first. No fluff.]

**ACTION ITEMS** (if any):
- [Specific action, owner, urgency]

**CAN WAIT:**
- [Lower-priority items]

---

SCAN OUTPUT:
{clean_output}"""

        result = _call_brain1("You are Hale's synthesis engine. Output clean text only.", prompt, max_tokens=600)
        return result

    def generate_brief(self) -> str:
        """
        Generate today's daily brief and write it to hale_brief.md.
        Pre-loads state files and injects as context — Qwen gets data, not tool calls.
        """
        # Pre-load all context files
        state_json = _STATE.read_text() if _STATE.exists() else "{}"
        memory_snippet = _MEMORY.read_text()[:2000] if _MEMORY.exists() else ""
        decisions_snippet = _DECISIONS.read_text()[:1000] if _DECISIONS.exists() else ""

        brief_prompt = f"""You are generating Col Victoria "Iron Vic" Hale's daily operational brief for Commander John Loucks of Dreams2Memories Travel, LLC.

Here is the current wing state:

## HALE STATE (JSON)
{state_json}

## HALE MEMORY (excerpt)
{memory_snippet[:1500]}

## RECENT DECISIONS
{decisions_snippet[:500]}

---

Based on the above data, generate the brief now. Do NOT use tool calls or function calls — the data is already provided above. Write only Markdown text.

Structure:
1. **CLIENT WIRE** — status of Furlow, Westbrook, Lyons from state
2. **OPEN TASKS** — what's in flight, who owns it
3. **FINANCIAL PULSE** — payments due, commissions
4. **WING HEALTH** — MCP, Telegram, Goose status from state
5. **STAFF ASSIGNMENTS** — A-staff work with Commander relevance
6. **DECISIONS NEEDED** — items requiring Commander (none if clear)
7. **INTEL FLASH** — one-line summary of anything notable

Format as Markdown tables where data exists. Be concise. Lead with facts. No tool calls."""

        brief_content = _call_brain1("You are Hale's briefing engine. Output clean Markdown only. No tool calls.", brief_prompt, max_tokens=1500)

        now = datetime.now(MT)
        ts  = now.strftime("%Y-%m-%d %H:%M MT")
        next_brief = (now + timedelta(hours=24)).strftime("%Y-%m-%d 07:00 MT")

        header = f"# HALE — Daily Brief\n*Generated: {ts}*\n\n---\n\n**Sir, here's where we stand.**\n\n---\n\n"
        footer = f"\n\n---\n*— Col Victoria \"Iron Vic\" Hale | Thunderbird Wing | {ts}*\n*Next brief: {next_brief}*\n"

        full_brief = header + brief_content + footer
        _BRIEF.write_text(full_brief)
        return full_brief


# ── CLI entrypoint ──

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "generate_brief"
    hale = HaleDispatcher()

    if task == "generate_brief":
        print(hale.generate_brief())
    else:
        # Check for Commander override prefix
        override = None
        if task.upper().startswith("OPUS:"):
            override = "opus"
            task = task[5:].strip()
        elif task.lower().startswith("sonnet:"):
            override = "sonnet"
            task = task[7:].strip()

        print(hale.dispatch(task, brain_override=override))
