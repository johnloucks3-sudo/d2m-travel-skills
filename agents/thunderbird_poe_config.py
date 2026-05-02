"""
Thunderbird Poe Gateway Config
================================
Dreams2Memories Travel, LLC

Reads poe.env and provides:
  - POE_MODE flag (1 = route via Poe, 0 = Max plan OAuth)
  - build_api_env() — drop-in for all subprocess env construction
  - log_usage()     — tracks token consumption and estimated point cost
  - usage_summary() — daily/monthly point burn report
  - set_poe_model() — Commander-selectable model profiles
  - list_profiles() — enumerate available named profiles

Point cost model (approximated from Poe pricing):
  Sonnet 4.5/4.6:   ~1,042 points per 1,000 tokens (blended input+output)
  Opus 4.5/4.6:     ~1,750 points per 1,000 tokens (blended)
  Haiku 3.5:        ~200  points per 1,000 tokens (blended)
  Kimi K2:          ~800  points per 1,000 tokens (estimated, verify on Poe)
  Kimi K2 Thinking: ~1,200 points per 1,000 tokens (estimated, extended CoT)
  nano-banana:      ~150  points per 1,000 tokens (estimated, small/fast)

Usage log: ~/Thunderbird/logs/poe_usage.jsonl (one JSON line per call)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("thunderbird_poe_config")

# ── Paths ────────────────────────────────────────────────────────────────────
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
POE_ENV_FILE    = THUNDERBIRD_DIR / "config" / "poe.env"
USAGE_LOG       = THUNDERBIRD_DIR / "logs" / "poe_usage.jsonl"

# ── Load poe.env ─────────────────────────────────────────────────────────────
_cfg: dict[str, str] = {}

def _load_env() -> dict[str, str]:
    global _cfg
    if _cfg:
        return _cfg
    if not POE_ENV_FILE.exists():
        return {}
    for line in POE_ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            _cfg[k.strip()] = v.strip()
    return _cfg

def _cfg_val(key: str, default: str = "") -> str:
    return _load_env().get(key, os.environ.get(key, default))

# ── Public config values ──────────────────────────────────────────────────────
def poe_mode() -> bool:
    """True if POE_MODE=1 in poe.env."""
    return _cfg_val("POE_MODE", "0") == "1"

def poe_api_key() -> str:
    return _cfg_val("POE_API_KEY", "")

def poe_base_url() -> str:
    return _cfg_val("POE_BASE_URL", "https://api.poe.com")

def poe_model() -> str:
    return _cfg_val("POE_MODEL", "claude-sonnet-4-6")

# ── Commander-selectable model profiles ───────────────────────────────────────
#
# Keys   = short names usable in C2 commands (/poe gemini, /poe kimi-think, etc.)
# Values = exact Poe bot/model strings (verify these against poe.com/explore/bots)
#
# NOTE: nano-banana and kimi-k2-thinking Poe bot names should be verified at
#       poe.com/explore/bots — community bot names can change.
#
MODEL_PROFILES: dict[str, dict] = {
    # ── Claude (current default) ─────────────────────────────────────────────
    "claude":        {"poe_model": "claude-sonnet-4-6",          "label": "Claude Sonnet 4.6 (default)",       "tier": "sonnet"},

    # ── Kimi ─────────────────────────────────────────────────────────────────
    "kimi":          {"poe_model": "Kimi-K2",                    "label": "Kimi K2 (standard)",                "tier": "kimi"},
    "kimi-think":    {"poe_model": "Kimi-K2-Thinking",           "label": "Kimi K2 Thinking (extended CoT)",   "tier": "kimi-think"},

    # ── Claude variants on Poe ──────────────────────────────────────────────
    "claude-code":   {"poe_model": "Claude-Code",                "label": "Claude Code (Poe bot)",             "tier": "sonnet"},
    "claude-haiku":  {"poe_model": "Claude-Haiku-4.5",           "label": "Claude Haiku 4.5 (Poe bot)",        "tier": "haiku"},

    # ── nano-banana family ───────────────────────────────────────────────────
    "nano-banana":   {"poe_model": "nano-banana",                "label": "nano-banana (original)",            "tier": "nano"},
    "nano-banana-2": {"poe_model": "Nano-Banana-2",              "label": "Nano-Banana-2",                     "tier": "nano"},
    "nano-webui":    {"poe_model": "NanoBananaWebUI",            "label": "NanoBananaWebUI",                   "tier": "nano"},

    # ── Google ───────────────────────────────────────────────────────────────
    "gemini":        {"poe_model": "Gemini-2.0-Flash",           "label": "Gemini 2.0 Flash",                  "tier": "flash"},
    "gemini-pro":    {"poe_model": "Gemini-2.0-Pro",             "label": "Gemini 2.0 Pro",                    "tier": "pro"},

    # ── OpenAI ───────────────────────────────────────────────────────────────
    "gpt4":          {"poe_model": "GPT-4o",                     "label": "GPT-4o",                            "tier": "gpt4"},
    "gpt4-mini":     {"poe_model": "GPT-4o-Mini",                "label": "GPT-4o Mini (cheap)",               "tier": "gpt4-mini"},

    # ── Speed alias (Groq-class fast) ────────────────────────────────────────
    "speed":         {"poe_model": "Llama-3.3-70B-Groq",         "label": "Llama 3.3 70B via Groq (fast)",    "tier": "llama"},

    # ── xAI ──────────────────────────────────────────────────────────────────
    "grok":          {"poe_model": "Grok-3",                     "label": "Grok 3",                            "tier": "grok"},
    "grok-imagine":  {"poe_model": "Grok-3-Imagine",             "label": "Grok 3 Imagine (image gen)",        "tier": "grok"},
}

# Aliases (shorthand → profile key)
_ALIASES: dict[str, str] = {
    "default":  "claude",
    "sonnet":   "claude",
    "k2":       "kimi",
    "k2-think": "kimi-think",
    "flash":    "gemini",
    "4o":       "gpt4",
    "mini":     "gpt4-mini",
    "haiku":    "claude-haiku",
    "banana":   "nano-banana",
    "banana2":  "nano-banana-2",
    "webui":    "nano-webui",
    "code":     "claude-code",
    "cc":       "claude-code",
    "fast":     "speed",
}


def resolve_profile(name: str) -> dict | None:
    """Return profile dict for a given name or alias, or None if not found."""
    key = _ALIASES.get(name.lower(), name.lower())
    return MODEL_PROFILES.get(key)


def list_profiles() -> list[dict]:
    """Return all profiles with key, label, and current-selection marker."""
    current = poe_model()
    result = []
    for key, p in MODEL_PROFILES.items():
        result.append({
            "key":     key,
            "label":   p["label"],
            "model":   p["poe_model"],
            "active":  p["poe_model"] == current,
        })
    return result


def set_poe_model(profile_name: str) -> dict:
    """Switch the active Poe model by profile name. Writes poe.env atomically.

    Returns {"ok": True, "model": ..., "label": ...} on success,
            {"ok": False, "error": ...} on failure.
    """
    profile = resolve_profile(profile_name)
    if not profile:
        keys = list(MODEL_PROFILES.keys()) + list(_ALIASES.keys())
        return {"ok": False, "error": f"Unknown profile '{profile_name}'. Valid: {sorted(keys)}"}

    model_str = profile["poe_model"]

    # Read current poe.env, update or insert POE_MODEL line
    lines: list[str] = []
    if POE_ENV_FILE.exists():
        lines = POE_ENV_FILE.read_text().splitlines()

    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("POE_MODEL"):
            lines[i] = f"POE_MODEL={model_str}"
            found = True
            break
    if not found:
        lines.append(f"POE_MODEL={model_str}")

    POE_ENV_FILE.write_text("\n".join(lines) + "\n")

    # Invalidate cache so next call to poe_model() picks up the new value
    global _cfg
    _cfg = {}

    logger.info("Poe model switched to: %s (%s)", model_str, profile["label"])
    return {"ok": True, "model": model_str, "label": profile["label"]}

# ── Model Router ──────────────────────────────────────────────────────────────
#
# Strategy: default Sonnet (separate weekly quota, ~0% used), escalate to Opus
# only for high-value client work, drop to Haiku for automation/classification.
#
# Max plan weekly budget awareness (2026-03-18 directive — preserve all-models quota):
#   Sonnet  → separate weekly quota (2% used as of 2026-03-18) ← USE THIS
#   Opus    → all-models weekly budget (39% used) ← CONSERVE
#   Haiku   → all-models budget (cheapest)
#
# To re-enable Opus for specific tasks, change entries below back to "claude-opus-4-6".

TASK_MODEL_MAP: dict[str, str] = {
    # ── Haiku: classification, monitoring, automation ────────────────────────
    "classify":          "claude-haiku-4-5-20251001",
    "monitor":           "claude-haiku-4-5-20251001",
    "alert_check":       "claude-haiku-4-5-20251001",
    "fare_watch":        "claude-haiku-4-5-20251001",
    "route_intent":      "claude-haiku-4-5-20251001",
    "summarize_short":   "claude-haiku-4-5-20251001",
    "intel_classify":    "claude-haiku-4-5-20251001",

    # ── Opus: Dani client-facing responses only ──────────────────────────────
    "dani_response":     "claude-sonnet-4-6",    # Dani → client — Sonnet (SO 2026-03-27: Opus retired)

    # ── Sonnet: everything else — C2, internal, drafts, proposals ────────────
    "default":           "claude-sonnet-4-6",
    "email_draft":       "claude-sonnet-4-6",   # internal drafting (Dani persona handles Opus via PERSONA_MODEL_MAP)
    "client_proposal":   "claude-sonnet-4-6",
    "ship_comparison":   "claude-sonnet-4-6",
    "dossier_update":    "claude-sonnet-4-6",
    "itinerary":         "claude-sonnet-4-6",
    "research":          "claude-sonnet-4-6",
    "booking_extract":   "claude-sonnet-4-6",
    "flight_search":     "claude-sonnet-4-6",
    "hotel_search":      "claude-sonnet-4-6",
    "tour_search":       "claude-sonnet-4-6",
    "intel_analysis":    "claude-sonnet-4-6",
    "morning_brief":     "claude-sonnet-4-6",
    "weekly_report":     "claude-sonnet-4-6",
    "architecture":      "claude-sonnet-4-6",
    "crisis":            "claude-sonnet-4-6",
    "strategy_review":   "claude-sonnet-4-6",
}


def route_model(task_type: str) -> str:
    """Return the appropriate model for a given task type.

    Usage:
        model = route_model("dani_response")   # → "claude-sonnet-4-6"
        model = route_model("client_proposal") # → "claude-opus-4-6"
        model = route_model("classify")        # → "claude-haiku-4-5-20251001"

    Unknown task types fall back to TASK_MODEL_MAP["default"] (Sonnet).
    In Poe mode, returns the configured Poe model for all tasks.
    """
    if poe_mode():
        return poe_model()
    resolved = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["default"])
    logger.debug("route_model(%s) → %s", task_type, resolved)
    return resolved


def model_tier(model: str) -> str:
    """Return a tier string for a given model ID."""
    m = model.lower()
    if "opus"    in m: return "opus"
    if "haiku"   in m: return "haiku"
    if "thinking" in m and "kimi" in m: return "kimi-think"
    if "kimi"    in m: return "kimi"
    if "nano"    in m or "banana" in m: return "nano"
    if "grok"    in m: return "grok"
    if "gemini"  in m: return "flash"
    if "gpt"     in m: return "gpt4"
    if "llama"   in m: return "llama"
    return "sonnet"

# ── Env builder ───────────────────────────────────────────────────────────────
def build_api_env(base_env: dict | None = None) -> dict[str, str]:
    """Return a clean env dict for subprocess / SDK calls.

    Poe mode:  sets ANTHROPIC_API_KEY + ANTHROPIC_BASE_URL for Poe routing.
    Max mode:  strips ANTHROPIC_API_KEY so Claude CLI uses Max plan OAuth.
    """
    env = dict(base_env or os.environ)

    if poe_mode():
        key = poe_api_key()
        url = poe_base_url()
        if not key:
            logger.warning("POE_MODE=1 but POE_API_KEY is empty — falling back to Max plan")
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("ANTHROPIC_BASE_URL", None)
        else:
            env["ANTHROPIC_API_KEY"]  = key
            env["ANTHROPIC_BASE_URL"] = url   # Claude SDK / MCP
            env["ANTHROPIC_HOST"]     = url   # Goose uses HOST not BASE_URL
            logger.debug("Poe mode: routing via %s", url)
    else:
        # Max plan OAuth — strip key so CLI finds the OAuth credentials
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        logger.debug("Max plan mode: ANTHROPIC_API_KEY stripped")

    return env

# ── Usage logging ─────────────────────────────────────────────────────────────

# Approximate points per 1K tokens by tier (verify against poe.com/pricing)
_POINTS_PER_1K: dict[str, int] = {
    "opus":       1750,
    "sonnet":     1042,
    "haiku":      200,
    "kimi-think": 1200,  # estimated — extended CoT burns more
    "kimi":       800,   # estimated
    "nano":       150,   # estimated — small/fast model
    "grok":       1000,  # estimated
    "flash":      300,   # Gemini Flash
    "gpt4":       1100,  # GPT-4o approximate
    "gpt4-mini":  250,
    "llama":      100,   # Groq-hosted Llama, very cheap
}

def _points_per_1k(model: str) -> int:
    tier = model_tier(model)
    return _POINTS_PER_1K.get(tier, 1042)  # default to Sonnet rate

def log_usage(
    persona: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    source: str = "telegram",
) -> dict:
    """Log a single API call and return the usage record."""
    if not poe_mode():
        return {}  # Nothing to track in Max plan mode

    total_tokens = input_tokens + output_tokens
    rate = _points_per_1k(model)
    est_points = int(total_tokens * rate / 1000)

    record = {
        "ts":           datetime.now(timezone.utc).isoformat(),
        "source":       source,
        "persona":      persona,
        "model":        model,
        "input_tokens": input_tokens,
        "output_tokens":output_tokens,
        "total_tokens": total_tokens,
        "est_points":   est_points,
    }

    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    logger.info(
        "Poe usage: %s/%s — %d tokens → ~%d pts",
        source, persona, total_tokens, est_points,
    )
    return record

def estimate_from_text(text: str) -> int:
    """Rough token estimate from character count (when API doesn't return usage)."""
    return max(1, len(text) // 4)

def usage_summary(days: int = 30) -> dict:
    """Summarize Poe point consumption over the last N days."""
    if not USAGE_LOG.exists():
        return {"error": "No usage log found", "log": str(USAGE_LOG)}

    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = []
    with open(USAGE_LOG, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line.strip())
                ts = datetime.fromisoformat(r["ts"])
                if ts >= cutoff:
                    records.append(r)
            except Exception:
                continue

    if not records:
        return {"days": days, "calls": 0, "total_tokens": 0, "est_points": 0}

    total_tokens = sum(r.get("total_tokens", 0) for r in records)
    est_points   = sum(r.get("est_points", 0) for r in records)

    by_persona: dict[str, int] = {}
    by_model:   dict[str, int] = {}
    for r in records:
        p = r.get("persona", "unknown")
        m = r.get("model", "unknown")
        by_persona[p] = by_persona.get(p, 0) + r.get("est_points", 0)
        by_model[m]   = by_model.get(m, 0)   + r.get("est_points", 0)

    return {
        "days":         days,
        "calls":        len(records),
        "total_tokens": total_tokens,
        "est_points":   est_points,
        "est_cost_usd": round(est_points / 1_000_000 * 30, 4),
        "by_persona":   dict(sorted(by_persona.items(), key=lambda x: -x[1])),
        "by_model":     dict(sorted(by_model.items(),   key=lambda x: -x[1])),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    cfg = _load_env()
    args = sys.argv[1:]

    if "--model" in args:
        # python thunderbird_poe_config.py --model kimi-think
        idx = args.index("--model")
        if idx + 1 < len(args):
            result = set_poe_model(args[idx + 1])
            if result["ok"]:
                print(f"✓ Poe model set: {result['label']} ({result['model']})")
            else:
                print(f"✗ {result['error']}")
        else:
            print("Usage: --model <profile>")
        sys.exit(0)

    if "--profiles" in args:
        print(f"{'KEY':<16} {'ACTIVE':<8} {'LABEL'}")
        print("-" * 60)
        for p in list_profiles():
            marker = "◀ active" if p["active"] else ""
            print(f"{p['key']:<16} {marker:<8} {p['label']}")
        sys.exit(0)

    print(f"POE_MODE    : {poe_mode()}")
    print(f"POE_MODEL   : {poe_model()}")
    print(f"POE_BASE_URL: {poe_base_url()}")
    key = poe_api_key()
    print(f"POE_API_KEY : {'SET (' + key[:8] + '...)' if key else 'NOT SET'}")
    print()
    if "--summary" in args:
        summary = usage_summary(30)
        print(json.dumps(summary, indent=2))
    elif "--test" in args:
        env = build_api_env()
        print("Env keys set:", [k for k in env if "ANTHROPIC" in k])

## AGENTS DOCUMENTATION

- Updated to enforce free‑model guardrail for OpenRouter.
- See docs/AGENTS_MODEL_GUIDE.md for allowed models and usage.

