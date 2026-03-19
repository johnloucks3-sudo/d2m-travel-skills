"""
Thunderbird Poe Gateway Config
================================
Dreams2Memories Travel, LLC

Reads poe.env and provides:
  - POE_MODE flag (1 = route via Poe, 0 = Max plan OAuth)
  - build_api_env() — drop-in for all subprocess env construction
  - log_usage()     — tracks token consumption and estimated point cost
  - usage_summary() — daily/monthly point burn report

Point cost model (approximated from Poe pricing):
  Sonnet 4.5/4.6: ~1,042 points per 1,000 tokens (blended input+output)
  Opus 4.5/4.6:   ~1,750 points per 1,000 tokens (blended)
  Haiku 3.5:      ~200 points per 1,000 tokens (blended)

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
    "dani_response":     "claude-opus-4-6",     # Dani → client (only external-facing)

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
    """Return 'haiku', 'sonnet', or 'opus' for a given model ID."""
    m = model.lower()
    if "opus"  in m: return "opus"
    if "haiku" in m: return "haiku"
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
            env["ANTHROPIC_BASE_URL"] = url
            logger.debug("Poe mode: routing via %s", url)
    else:
        # Max plan OAuth — strip key so CLI finds the OAuth credentials
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        logger.debug("Max plan mode: ANTHROPIC_API_KEY stripped")

    return env

# ── Usage logging ─────────────────────────────────────────────────────────────

# Approximate points per 1K tokens by model family
_POINTS_PER_1K = {
    "sonnet": 1042,
    "opus":   1750,
    "haiku":  200,
}

def _points_per_1k(model: str) -> int:
    model_lower = model.lower()
    for key, rate in _POINTS_PER_1K.items():
        if key in model_lower:
            return rate
    return 1042  # default to Sonnet rate

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
    print(f"POE_MODE  : {poe_mode()}")
    print(f"POE_MODEL : {poe_model()}")
    print(f"POE_BASE_URL: {poe_base_url()}")
    key = poe_api_key()
    print(f"POE_API_KEY : {'SET (' + key[:8] + '...)' if key else 'NOT SET'}")
    print()
    if "--summary" in sys.argv:
        summary = usage_summary(30)
        print(json.dumps(summary, indent=2))
    elif "--test" in sys.argv:
        env = build_api_env()
        print("Env keys set:", [k for k in env if "ANTHROPIC" in k])
