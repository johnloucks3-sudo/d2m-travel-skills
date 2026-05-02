"""
Hale Brain Dispatcher
=====================
Three-brain routing for Col Victoria "Iron Vic" Hale, COO — Thunderbird Wing.

⚠️ CRITICAL FIX (SO 2026-04-27): Switched from FREE OpenRouter tiers to Claude MAX (unlimited tier).
Brief generation and synthesis now use Claude Sonnet headless via OAuth.

Brain 1: (DEPRECATED — was OpenRouter free tiers)
Brain 2: Claude MAX (Sonnet headless)                        — brief generation, synthesis, reasoning
Brain 3: DeepSeek (direct or OpenRouter)                    — arbitration, high-stakes, brain disagreement
Self:    Hale handles directly                               — simple, within institutional knowledge

Usage:
    from hale_dispatcher import HaleDispatcher
    hale = HaleDispatcher()
    result = hale.dispatch("Summarize the Furlow dossier and flag anything overdue.")

Author: Col Victoria "Iron Vic" Hale (COS) — built 2026-04-03, fixed 2026-04-24
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

# Token optimization (from same directory)
sys.path.insert(0, str(Path(__file__).parent))
try:
    from hale_token_optimizer import HaleTokenOptimizer
except ImportError as e:
    print(f"Warning: Could not import HaleTokenOptimizer: {e}", file=sys.stderr)
    HaleTokenOptimizer = None

# ── Paths ──
_ROOT = Path(__file__).resolve().parent.parent
_OPSCENTER = Path(__file__).resolve().parent
_STATE   = _ROOT / "hale_state.json"
_MEMORY  = _ROOT / "hale_memory.md"
_DECISIONS = _ROOT / "hale_decisions.md"
_BRIEF   = _ROOT / "hale_brief.md"
_PERSONA = _ROOT / "Personas" / "hale_cos.md"
_CONTEXT = _ROOT / "hale_session_context.md"  # DeepSeek deep scan output

# ── Env ──
load_dotenv(str(_ROOT / ".env"))
load_dotenv(str(_ROOT / ".env.telegram"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEEPSEEK_API_KEY   = os.getenv("DEEPSEEK_API_KEY", "")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")

DEEPSEEK_V4_MODEL  = "deepseek/deepseek-v4-pro"  # ✅ ACTIVE: $0.305/M tokens — cost-optimized reasoning
QWEN_MODEL         = DEEPSEEK_V4_MODEL  # Legacy alias (updated)
SONNET_MODEL       = "claude-sonnet-4-6"
OPUS_MODEL         = "claude-opus-4-6"
DEEPSEEK_MODEL     = "deepseek-chat"
DEEPSEEK_OR_MODEL  = "deepseek/deepseek-v4-pro"  # OpenRouter proxy — $0.305/M, cost-optimized

# Free OpenRouter tiers (SO 2026-04-24)
FREE_OPENROUTER_RESEARCH = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
FREE_OPENROUTER_OPS = "openrouter/openai/gpt-oss-120b:free"
FREE_OPENROUTER_SUMMARY = "openrouter/google/gemma-3-27b-it:free"
FREE_OPENROUTER_BULK = "openrouter/deepseek/deepseek-r1:free"

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

# Visual synthesis keywords (SO 2026-04-28)
VISUAL_KEYWORDS = {
    "visual", "visualize", "dashboard", "graphics", "infographic", "chart",
    "heatmap", "wheel", "lifecycle", "waterfall", "risk matrix", "brief visual",
    "generate visuals", "create graphics", "plot", "diagram", "visual brief",
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
    Returns: 'brain1' | 'brain2' | 'brain3' | 'visual' | 'self'

    Routing rules (DeepSeek arbitrated 2026-04-03, extended 2026-04-28):
    - Brain 3: explicit Commander command only (not keyword-triggered)
    - Visual: graphics, dashboards, infographics generation (SO 2026-04-28)
    - Brain 2: reasoning, strategy, code, voice, OR multi-source synthesis
    - Brain 1: single-source retrieval, ops, scan, summarize
    - Self: simple greetings and direct acknowledgments
    """
    lower = content.lower().strip()

    # Brain 3: explicit command only — never keyword-triggered alone
    for kw in BRAIN3_EXPLICIT_COMMANDS:
        if kw in lower:
            return "brain3"

    # Visual synthesis: dashboard, charts, infographics
    for kw in VISUAL_KEYWORDS:
        if kw in lower:
            return "visual"

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


# ── Brain 1: FREE OpenRouter tiers (Nemotron/GPT-OSS/Gemma/DeepSeek-R1) ──

def _select_free_model(task: str) -> str:
    """
    Route to appropriate free OpenRouter model based on task type.
    Default rotation: Nemotron → GPT-OSS → Gemma → DeepSeek-R1
    """
    lower = task.lower()

    # Summarization: use Gemma (optimized for brevity)
    if any(kw in lower for kw in ["summarize", "summary", "digest", "brief"]):
        return FREE_OPENROUTER_SUMMARY

    # Research: use Nemotron (strong reasoning)
    if any(kw in lower for kw in ["research", "intel", "analyze", "investigate"]):
        return FREE_OPENROUTER_RESEARCH

    # Bulk/large context: use DeepSeek-R1 (1M context)
    if any(kw in lower for kw in ["scan", "review", "audit", "bulk", "large"]):
        return FREE_OPENROUTER_BULK

    # Default ops: GPT-OSS (balanced)
    return FREE_OPENROUTER_OPS


def _call_brain1(system: str, task: str, max_tokens: int = 2000) -> str:
    """Brain 1: FREE OpenRouter tiers (Nemotron/GPT-OSS/Gemma/DeepSeek-R1). $0/month (SO 2026-04-24)."""
    if not OPENROUTER_API_KEY:
        return "[BRAIN1 ERROR] OPENROUTER_API_KEY not set."

    # Select appropriate free model based on task type
    model = _select_free_model(task)

    try:
        payload = json.dumps({
            "model": model,
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
        return f"[BRAIN1 ERROR] Free OpenRouter failed: {e}"


# ── Brain 2: Claude headless (Sonnet or Opus) ──

def _call_brain2_claude_api(task: str, model: str = SONNET_MODEL, max_words: int = 500) -> str:
    """
    Brain 2 via Claude SDK (fallback when needed).
    Uses ANTHROPIC_API_KEY if available.
    """
    if not ANTHROPIC_API_KEY:
        return "[BRAIN2 FALLBACK] No ANTHROPIC_API_KEY; use template-based brief instead."

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=model,
            max_tokens=int(max_words * 1.3),  # Rough estimation
            messages=[{"role": "user", "content": task}]
        )
        return response.content[0].text.strip()
    except ImportError:
        return "[BRAIN2 ERROR] anthropic module not installed"
    except Exception as e:
        return f"[BRAIN2 ERROR] Claude API failed: {str(e)[:200]}"


def _call_brain2(task: str, model: str = SONNET_MODEL, max_words: int = 500) -> str:
    """
    Brain 2: DEPRECATED — async spawn version disabled due to reliability issues.
    Fallback to Claude SDK or template-based briefs.
    For reliability, the daily brief now uses fast templates instead of Claude generation.
    """
    return _call_brain2_claude_api(task, model, max_words)


# ── Visual Synthesis: Dashboards + Infographics ──

def _call_visual_synthesis() -> str:
    """
    Visual synthesis brain: generate operational dashboards + strategic infographics.
    Returns paths to generated HTML dashboard and data files.
    Called on demand or via daily systemd timer (SO 2026-04-28).

    Generates:
    - phase1_data.json (operational data export)
    - dashboard.html (interactive HTML with Plotly charts)
    - canva_prompts.json (prompts for MCP Canva infographic generation)
    """
    try:
        # Import data generators module
        sys.path.insert(0, str(_ROOT / "core" / "visual_synthesis"))
        from data_generators import generate_data_json, generate_html_dashboard, generate_canva_prompts

        data_path    = generate_data_json()
        dashboard_path = generate_html_dashboard()
        prompts_path = generate_canva_prompts()

        return f"""✅ VISUAL SYNTHESIS COMPLETE

**Generated Files:**
- Data export: {data_path}
- Interactive dashboard: file://{dashboard_path}
- Canva prompts: {prompts_path}

**Dashboard Contents:**
- 4 stat cards (Urgent/At-Risk/On-Track/Pipeline)
- Financial Waterfall (prospect → delivered + at-risk items)
- Operational Heat Map (clients × task types by urgency)

**Next Steps:**
1. Open dashboard in browser: file://{dashboard_path}
2. Generate Canva infographics using MCP with prompts from {prompts_path}
3. Link infographics into hale_brief.md Section 2

Dashboard auto-refreshes daily at 05:30 MT via systemd timer."""
    except Exception as e:
        return f"[VISUAL SYNTHESIS ERROR] {e}"


# ── Phase 2: Weekly Strategic Visuals ──

def _call_phase2_visual_synthesis() -> str:
    """
    Phase 2 visual synthesis: generate weekly strategic infographics.
    Returns paths to generated data and Canva prompts.
    Called on demand or via weekly systemd timer on Sundays 18:00 MT (SO 2026-04-28).

    Generates:
    - phase2_data.json (market opportunities, revenue timeline, capability roadmap)
    - phase2_canva_prompts.json (three prompts for MCP Canva infographic generation)
    """
    try:
        # Import phase2 generators module
        sys.path.insert(0, str(_ROOT / "core" / "visual_synthesis"))
        from phase2_generators import generate_phase2_data_json, generate_canva_prompts_phase2

        data_path = generate_phase2_data_json()
        prompts_path = generate_canva_prompts_phase2()

        return f"""✅ PHASE 2 VISUAL SYNTHESIS COMPLETE

**Generated Files:**
- Strategic data: {data_path}
- Canva prompts: {prompts_path}

**Three Strategic Infographics:**
1. Opportunity Map — Market opportunities by cruise line × destination
2. Revenue Timeline — Commission forecast Apr 2026 → Q1 2027
3. Capability Roadmap — Thunderbird Wing evolution (3M/6M/12M targets)

**Next Steps:**
1. Use prompts from {prompts_path} with MCP Canva generate-design tool
2. Create permanent designs with create-design-from-candidate
3. Link new designs into strategic briefings

Phase 2 visuals auto-generate weekly (Sundays 18:00 MT) via systemd timer."""
    except Exception as e:
        return f"[PHASE2 VISUAL SYNTHESIS ERROR] {e}"


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
    """Load Hale's persona + memory + DeepSeek deep scan context."""
    base = ""
    if _PERSONA.exists():
        base = _PERSONA.read_text()

    # Inject memory
    mem_snippet = ""
    if _MEMORY.exists():
        mem_snippet = "\n\n---\n## LIVE MEMORY\n" + _MEMORY.read_text()[:2000]

    # Inject DeepSeek deep scan context (institutional knowledge)
    context_snippet = ""
    if _CONTEXT.exists():
        context_snippet = "\n\n---\n## WING CONTEXT (DeepSeek scan)\n" + _CONTEXT.read_text()[:4000]

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
        self.optimizer = HaleTokenOptimizer() if HaleTokenOptimizer else None

    def dispatch(self, task: str, brain_override: Optional[str] = None) -> str:
        """
        Classify task → OPTIMIZE FOR TOKENS → route to correct brain → return result.

        brain_override: 'opus' | 'sonnet' | 'brain1' | 'brain2' | 'brain3' | None

        Token optimization is applied automatically via HaleTokenOptimizer:
        1. Model selection based on task type (Haiku/Sonnet/Opus)
        2. Context compression (if context provided)
        3. Lazy context loading (if task doesn't need full context)
        4. Output specifications (format, length constraints)
        5. Batch optimization hints
        """
        start = time.time()

        # ── STEP 1: Classify task ──
        if brain_override in ("opus", "sonnet"):
            brain  = "brain2"
            model  = OPUS_MODEL if brain_override == "opus" else SONNET_MODEL
            reason = f"Commander override: {brain_override.upper()}"
            optimized_task = task
            optimization_info = ""
        elif brain_override in ("brain1", "brain2", "brain3"):
            brain  = brain_override
            model  = SONNET_MODEL
            reason = f"Explicit override: {brain_override}"
            optimized_task = task
            optimization_info = ""
        else:
            brain  = classify_task(task)
            model  = SONNET_MODEL
            reason = "Auto-classified"
            optimized_task = task
            optimization_info = ""

            # ── STEP 2: Apply token optimization (if optimizer loaded) ──
            if self.optimizer:
                # Determine task type for optimizer
                task_type = brain  # Use brain classification as task type
                is_client_facing = any(kw in task.lower() for kw in ["email", "dani", "draft", "client", "proposal"])

                # Run optimizer
                opt_result = self.optimizer.assess_and_optimize(
                    task_text=task,
                    task_type=task_type,
                    context=None,  # Context not provided in this API; could be extended
                    client_facing=is_client_facing
                )

                # Use optimizer's model recommendation
                model_map = {
                    "haiku": "claude-haiku-4-5-20251001",
                    "sonnet": SONNET_MODEL,
                    "opus": OPUS_MODEL,
                }
                model = model_map.get(opt_result.model, SONNET_MODEL)
                optimized_task = opt_result.optimized_prompt

                # Log optimization info
                optimization_info = f" | Optimized: {', '.join(opt_result.strategy_applied)} | Est. savings: {opt_result.savings_estimate} tokens"
                reason = f"Auto-classified + optimized | Model: {opt_result.model} | Strategies: {', '.join(opt_result.strategy_applied)}"

        # ── STEP 3: Dispatch ──
        if brain == "self":
            result    = self._handle_self(optimized_task)
            brain_tag = "Hale (self)"

        elif brain == "visual":
            result    = _call_visual_synthesis()
            brain_tag = "Visual Synthesis (Dashboards + Infographics)"

        elif brain == "brain1":
            result    = _call_brain1(self.system, optimized_task)
            brain_tag = "Brain 1 (FREE OpenRouter)"
            # Self-escalate on error
            if result.startswith("[BRAIN1 ERROR]"):
                result    = _call_brain2(f"{self.system}\n\nTASK: {optimized_task}", model=SONNET_MODEL)
                brain_tag = "Brain 2 (Sonnet — free model escalation)"
                log_decision(
                    f"Escalated OpenRouter→Sonnet on: {optimized_task[:80]}",
                    "Free OpenRouter tier returned an error; task required reliable response.",
                    "Brain 2 (Sonnet)"
                )
                self._escalation_note = f"Escalated to Sonnet — free model failed on: {optimized_task[:60]}"

        elif brain == "brain2":
            digest = f"{self.system[:500]}\n\nTASK: {optimized_task}"
            result = _call_brain2(digest, model=model)
            brain_tag = f"Brain 2 ({model.split('-')[1].title() if '-' in model else model})"

        elif brain == "brain3":
            # Strip PII before sending to DeepSeek
            clean_task = self._strip_pii(optimized_task)
            result     = _call_brain3(clean_task)
            brain_tag  = "Brain 3 (DeepSeek)"

        else:
            result    = self._handle_self(optimized_task)
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
            return "Wing operational. Thunderbird MCP: check localhost:8765. OpenCode: verify with `opencode run \"test\"`. Standing by."
        if "brief" in lower:
            if _BRIEF.exists():
                return _BRIEF.read_text()
            return "No brief generated yet. Run hale_dispatcher.generate_brief() to produce one."
        return f"Acknowledged. Standing by on: {task[:100]}"

    def _strip_pii(self, text: str) -> str:
        """
        Remove client PII before sending to DeepSeek.
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
        Uses Claude MAX headless (SO 2026-04-27).
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

        # Strip PII before sending if it's an intel/tech scan
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

        result = _call_brain2(prompt, model=SONNET_MODEL, max_words=600)
        return result

    def generate_brief(self) -> str:
        """
        Generate today's daily brief and write it to hale_brief.md.
        Uses Claude MAX headless (SO 2026-04-27) — no OpenRouter.
        Pre-loads state files and injects as context.
        """
        # Pre-load all context files
        state_json = _STATE.read_text() if _STATE.exists() else "{}"
        memory_snippet = _MEMORY.read_text()[:2000] if _MEMORY.exists() else ""
        decisions_snippet = _DECISIONS.read_text()[:1000] if _DECISIONS.exists() else ""

        brief_prompt = f"""You are Col Victoria "Iron Vic" Hale, COO of Thunderbird Wing, Dreams2Memories Travel, LLC.

Generate today's operational brief for Commander John Loucks.

## HALE STATE (JSON)
{state_json}

## HALE MEMORY (excerpt)
{memory_snippet[:1500]}

## RECENT DECISIONS
{decisions_snippet[:500]}

---

Structure (Markdown tables):
1. **CLIENT WIRE** — status of active clients (phase, FPD, open items)
2. **OPEN TASKS** — what's in flight, who owns it, urgency
3. **FINANCIAL PULSE** — payments due, commissions, overdue amounts
4. **WING HEALTH** — MCP, Telegram, daemons status from state
5. **STAFF ASSIGNMENTS** — A-staff workload, Commander-relevant focus
6. **DECISIONS NEEDED** — items requiring Commander action
7. **INTEL FLASH** — one-line summary of notable intelligence

Be concise. Lead with facts. No fluff. Max 600 tokens."""

        # Call Claude MAX headless (Sonnet) — bypass OpenRouter entirely
        brief_content = _call_brain2(brief_prompt, model=SONNET_MODEL, max_words=600)

        now = datetime.now(MT)
        ts  = now.strftime("%Y-%m-%d %H:%M MT")
        next_brief = (now + timedelta(hours=24)).strftime("%Y-%m-%d 07:00 MT")

        header = f"# HALE — Daily Brief\n*Generated: {ts}*\n\n---\n\n**Sir, here's where we stand.**\n\n---\n\n"
        footer = f"\n\n---\n*— Col Victoria \"Iron Vic\" Hale | Thunderbird Wing | {ts}*\n*Next brief: {next_brief}*\n"

        full_brief = header + brief_content + footer
        _BRIEF.write_text(full_brief)
        return full_brief

    def generate_visual_brief(self) -> str:
        """
        Generate visual synthesis (dashboards + infographics) for operational brief.
        Callable from systemd timer at 05:30 MT daily (SO 2026-04-28).
        Returns status + file paths.
        """
        result = _call_visual_synthesis()

        # Log generation
        now = datetime.now(MT)
        ts  = now.strftime("%Y-%m-%d %H:%M MT")
        print(f"[{ts}] HALE Visual Synthesis executed", file=sys.stderr)

        return result

    def generate_phase2_visuals(self) -> str:
        """
        Generate Phase 2 strategic visuals (Opportunity Map, Revenue Timeline, Capability Roadmap).
        Callable from systemd timer weekly on Sundays 18:00 MT (SO 2026-04-28).
        Returns status + file paths.
        """
        result = _call_phase2_visual_synthesis()

        # Log generation
        now = datetime.now(MT)
        ts  = now.strftime("%Y-%m-%d %H:%M MT")
        print(f"[{ts}] HALE Phase 2 Visual Synthesis executed", file=sys.stderr)

        return result


# ── CLI entrypoint ──

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "generate_brief"
    hale = HaleDispatcher()

    if task == "generate_brief":
        print(hale.generate_brief())
    elif task == "generate_visual_brief":
        print(hale.generate_visual_brief())
    elif task == "generate_phase2_visuals":
        print(hale.generate_phase2_visuals())
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
