#!/usr/bin/env python3
"""
advisor_test_harness.py
48-hour Advisor Strategy test — Track A (research) + Track B (financial recon)
COS: Hale | Approved: Commander 2026-04-16

Anthropic Advisor Tool (Beta: advisor-tool-2026-03-01)
Docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool

Architecture:
  - Executor model drives the task (cheap, fast)
  - Advisor model fires ONLY when executor gets stuck (expensive, smart)
  - All happens inside a single /v1/messages request
  - Advisor tokens billed separately in usage.iterations[]

Track A — Research Sweep (Dembe):
  Executor: Haiku 4.5  |  Advisor: Opus 4.7  |  max_uses: 3
Track B — Financial Reconciliation:
  Executor: Sonnet 4.6  |  Advisor: Opus 4.7  |  max_uses: 2
"""

import anthropic
import json
import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LOG_DIR = Path("/home/john/Thunderbird/OpsCenter")
RESULTS_PATH = LOG_DIR / "advisor_test_results.json"
LOG_PATH = LOG_DIR / "advisor_test.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("advisor_test")

BETA_TAG = "advisor-tool-2026-03-01"

# ---------------------------------------------------------------------------
# Multi-backend client factory
# ---------------------------------------------------------------------------
# Backend priority: --backend flag > auto-detect
#   "openrouter" — uses OPENROUTER_API_KEY, model IDs prefixed anthropic/
#   "max_oauth"  — uses Max plan OAuth token from ~/.claude/.credentials.json
#   "api"        — uses ANTHROPIC_API_KEY (pay-per-use, needs credits)

OPENROUTER_MODEL_MAP = {
    "claude-haiku-4-5-20251001": "anthropic/claude-haiku-4.5",
    "claude-sonnet-4-6": "anthropic/claude-sonnet-4.6",
    "claude-opus-4-6": "anthropic/claude-opus-4.6",
    "claude-opus-4-7": "anthropic/claude-opus-4.7",
}


def _build_client(backend: str) -> tuple[anthropic.Anthropic, str, bool]:
    """Return (client, backend_name, supports_advisor_beta)."""
    if backend == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        client = anthropic.Anthropic(api_key=key, base_url="https://openrouter.ai/api")
        return client, "openrouter", False  # OpenRouter doesn't support advisor beta

    if backend == "max_oauth":
        creds_path = Path.home() / ".claude" / ".credentials.json"
        creds = json.loads(creds_path.read_text())
        token = creds["claudeAiOauth"]["accessToken"]
        client = anthropic.Anthropic(api_key=token)
        return client, "max_oauth", True

    # Default: API key
    client = anthropic.Anthropic()
    return client, "api", True


def _resolve_model(model_id: str, backend: str) -> str:
    """Map Anthropic model IDs to backend-specific IDs."""
    if backend == "openrouter":
        return OPENROUTER_MODEL_MAP.get(model_id, model_id)
    return model_id


# Global client — set by main()
CLIENT: anthropic.Anthropic = None
BACKEND: str = "api"
ADVISOR_SUPPORTED: bool = True

# Valid model pairs per docs — advisor must be >= executor capability
TRACK_A_CONFIG = {
    "name": "research_sweep",
    "executor": "claude-haiku-4-5-20251001",
    "advisor": "claude-opus-4-7",
    "max_uses": 3,
    "max_tokens": 4096,
}

TRACK_B_CONFIG = {
    "name": "financial_recon",
    "executor": "claude-sonnet-4-6",
    "advisor": "claude-opus-4-7",
    "max_uses": 2,
    "max_tokens": 2048,
}


# ---------------------------------------------------------------------------
# Production prompts — pulled from real D2M modules
# ---------------------------------------------------------------------------

TRACK_A_PROMPT = """\
You are A2 (Lt Col Marcus "Wraith" Dembe), Research & Market Intelligence officer
for Dreams2Memories Travel, LLC — a luxury travel advisory.

Execute a world intelligence sweep. Analyze and synthesize the following domains:

1. TRAVEL ADVISORIES: Identify countries with Level 3+ State Dept advisories
   relevant to luxury cruise itineraries (Mediterranean, Northern Europe,
   Caribbean, South Pacific, Panama Canal). Flag any advisory upgrades in the
   last 7 days.

2. WEATHER & DISRUPTION: Identify port weather disruptions — storms, extreme
   heat, volcanic activity — for the next 14 days across active client
   itineraries: Silver Nova (Mediterranean Aug 2026), Seven Seas Grandeur
   (Scandinavia Aug-Sep 2026), Viking Mars (Panama Canal Dec 2026).

3. CRUISE LINE INTELLIGENCE: Summarize notable developments for targeted lines:
   Silversea, Regent Seven Seas, Cunard, Oceania, Seabourn, Viking,
   AmaWaterways, Ponant. Include: new ship announcements, itinerary changes,
   promotional offers, executive changes.

4. GEOPOLITICAL RISK: Flag any geopolitical developments that could affect
   luxury cruise operations — port closures, sanctions, piracy alerts,
   diplomatic incidents.

Output format: JSON with sections for each domain. Every source gets a URL.
Rate each item's D2M relevance 1-5. Only include items rated 3+.
"""

TRACK_B_PROMPT = """\
You are A9 (Victor "Vic" Harlan), Finance & Process Improvement officer
for Dreams2Memories Travel, LLC.

Execute a commission reconciliation analysis. You have the following data:

EXPECTED COMMISSIONS (from Booking Master):
1. Booking SN-2026-001 | Silversea Silver Nova | Client: Westbrook |
   Net: $42,800 | Markup: 25% | Expected commission: $10,700 |
   Booking date: 2025-12-15 | Status: CONFIRMED | FPD: 2026-06-01

2. Booking RG-2026-002 | Regent Grandeur | Client: Furlow |
   Net: $38,200 | Markup: 25% | Expected commission: $9,550 |
   Booking date: 2026-01-20 | Status: CONFIRMED | FPD: 2026-04-01 (PAID)

3. Booking VM-2026-003 | Viking Mars | Client: Ely/Darrow |
   Net: $28,500 | Markup: 25% | Expected commission: $7,125 |
   Booking date: 2026-02-10 | Status: CONFIRMED | FPD: 2026-08-15

4. Booking SM-2026-004 | Silversea Silver Muse | Client: McLeod |
   Net: $51,300 | Markup: 22% (SLH) | Expected commission: $11,286 |
   Booking date: 2026-03-01 | Status: CONFIRMED | FPD: 2026-05-15

RECEIVED PAYMENTS (from supplier emails, last 90 days):
- Regent Seven Seas: $9,550.00 — Ref RG-2026-002 — 2026-04-05
- Silversea: $10,200.00 — Ref SN-2026-001 — 2026-04-10
- Viking Cruises: $6,800.00 — No ref cited — 2026-04-12

Reconcile expected vs received. For each booking:
1. Match payments to bookings (exact ref match first, then fuzzy by supplier+amount)
2. Categorize: MATCHED / UNDERPAID / MISSING / UNMATCHED
3. Calculate deltas
4. Flag anomalies (underpayments, missing payments, unmatched receipts)
5. Generate a Commander-ready summary with recommended actions

Output: structured report with totals, per-booking status, and action items.
"""


# ---------------------------------------------------------------------------
# Core — run a single advisor task
# ---------------------------------------------------------------------------

def run_advisor_task(config: dict, prompt: str) -> dict:
    """Execute a single task through the Advisor pattern and capture metrics."""
    global ADVISOR_SUPPORTED
    executor_model = _resolve_model(config["executor"], BACKEND)
    advisor_model = _resolve_model(config["advisor"], BACKEND)

    if not ADVISOR_SUPPORTED:
        log.info(f"[{config['name']}] Advisor not supported on {BACKEND} — "
                 f"running executor-only ({executor_model})")
        return _run_executor_only(config, prompt)

    log.info(f"[{config['name']}] Starting — executor={executor_model}, "
             f"advisor={advisor_model}, max_uses={config['max_uses']} "
             f"[backend={BACKEND}]")

    start = time.time()
    try:
        response = CLIENT.beta.messages.create(
            model=executor_model,
            max_tokens=config["max_tokens"],
            betas=[BETA_TAG],
            tools=[
                {
                    "type": "advisor_20260301",
                    "name": "advisor",
                    "model": advisor_model,
                    "max_uses": config["max_uses"],
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        elapsed = time.time() - start
        log.error(f"[{config['name']}] API error after {elapsed:.1f}s: {e}")
        return {
            "track": config["name"],
            "status": "ERROR",
            "error": str(e),
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now().isoformat(),
        }

    elapsed = time.time() - start

    # --- Extract usage from iterations ---
    usage = response.usage
    iterations = []
    executor_input = 0
    executor_output = 0
    advisor_input = 0
    advisor_output = 0

    if hasattr(usage, "iterations") and usage.iterations:
        for it in usage.iterations:
            it_dict = {
                "type": it.type if hasattr(it, "type") else "unknown",
                "input_tokens": getattr(it, "input_tokens", 0),
                "output_tokens": getattr(it, "output_tokens", 0),
                "cache_read_input_tokens": getattr(it, "cache_read_input_tokens", 0),
            }
            if hasattr(it, "model"):
                it_dict["model"] = it.model
            iterations.append(it_dict)

            if it_dict["type"] == "advisor_message":
                advisor_input += it_dict["input_tokens"]
                advisor_output += it_dict["output_tokens"]
            else:
                executor_input += it_dict["input_tokens"]
                executor_output += it_dict["output_tokens"]

    # --- Extract output text and advisor call count ---
    output_text = ""
    advisor_calls = 0
    for block in response.content:
        if hasattr(block, "text"):
            output_text += block.text
        if hasattr(block, "type") and block.type == "server_tool_use":
            if hasattr(block, "name") and block.name == "advisor":
                advisor_calls += 1

    result = {
        "track": config["name"],
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "backend": BACKEND,
        "config": {
            "executor": config["executor"],
            "advisor": config["advisor"],
            "max_uses": config["max_uses"],
        },
        "usage": {
            "executor_input_tokens": executor_input or getattr(usage, "input_tokens", 0),
            "executor_output_tokens": executor_output or getattr(usage, "output_tokens", 0),
            "advisor_input_tokens": advisor_input,
            "advisor_output_tokens": advisor_output,
            "total_tokens": (executor_input + executor_output
                             + advisor_input + advisor_output),
            "advisor_calls": advisor_calls,
            "iterations": iterations,
        },
        "output_length": len(output_text),
        "output_preview": output_text[:500],
        "stop_reason": response.stop_reason,
    }

    log.info(
        f"[{config['name']}] Complete — {elapsed:.1f}s, "
        f"advisor_calls={advisor_calls}, "
        f"executor_tokens={executor_input}in/{executor_output}out, "
        f"advisor_tokens={advisor_input}in/{advisor_output}out"
    )
    return result


# ---------------------------------------------------------------------------
# Baseline — run the same prompt on the advisor model directly (no advisor)
# ---------------------------------------------------------------------------

def _run_executor_only(config: dict, prompt: str) -> dict:
    """Run with executor model only (no advisor) — for backends that don't support the beta."""
    executor_model = _resolve_model(config["executor"], BACKEND)
    log.info(f"[{config['name']}_executor_only] Running on {executor_model} [backend={BACKEND}]")

    start = time.time()
    try:
        response = CLIENT.messages.create(
            model=executor_model,
            max_tokens=config["max_tokens"],
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        elapsed = time.time() - start
        log.error(f"[{config['name']}_executor_only] API error: {e}")
        return {
            "track": f"{config['name']}_executor_only",
            "status": "ERROR",
            "error": str(e),
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now().isoformat(),
        }

    elapsed = time.time() - start
    usage = response.usage
    output_text = "".join(b.text for b in response.content if hasattr(b, "text"))

    return {
        "track": f"{config['name']}_executor_only",
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "backend": BACKEND,
        "config": {
            "executor": config["executor"],
            "advisor": "none",
            "max_uses": 0,
        },
        "usage": {
            "executor_input_tokens": getattr(usage, "input_tokens", 0),
            "executor_output_tokens": getattr(usage, "output_tokens", 0),
            "advisor_input_tokens": 0,
            "advisor_output_tokens": 0,
            "total_tokens": getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0),
            "advisor_calls": 0,
            "iterations": [],
        },
        "output_length": len(output_text),
        "output_preview": output_text[:500],
        "stop_reason": response.stop_reason,
    }


def run_baseline(config: dict, prompt: str) -> dict:
    """Run the same prompt directly on the advisor model for comparison."""
    baseline_model = _resolve_model(config["advisor"], BACKEND)
    log.info(f"[{config['name']}_baseline] Running direct on {baseline_model} [backend={BACKEND}]")

    start = time.time()
    try:
        response = CLIENT.messages.create(
            model=baseline_model,
            max_tokens=config["max_tokens"],
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        elapsed = time.time() - start
        log.error(f"[{config['name']}_baseline] API error: {e}")
        return {
            "track": f"{config['name']}_baseline",
            "status": "ERROR",
            "error": str(e),
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now().isoformat(),
        }

    elapsed = time.time() - start
    usage = response.usage
    output_text = "".join(b.text for b in response.content if hasattr(b, "text"))

    return {
        "track": f"{config['name']}_baseline",
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "backend": BACKEND,
        "config": {"model": config["advisor"], "direct": True},
        "usage": {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.input_tokens + usage.output_tokens,
        },
        "output_length": len(output_text),
        "output_preview": output_text[:500],
        "stop_reason": response.stop_reason,
    }


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

# Per-million-token pricing (as of April 2026)
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
    "claude-opus-4-7":           {"input": 15.00, "output": 75.00},
}


def estimate_cost(result: dict) -> Optional[float]:
    """Estimate cost in USD from a test result."""
    if result["status"] != "OK":
        return None

    total = 0.0
    config = result.get("config", {})

    if config.get("direct"):
        # Baseline: single model
        model = config["model"]
        rates = PRICING.get(model, {})
        u = result["usage"]
        total += u["input_tokens"] * rates.get("input", 0) / 1_000_000
        total += u["output_tokens"] * rates.get("output", 0) / 1_000_000
    else:
        # Advisor pattern: executor + advisor billed separately
        executor = config.get("executor", "")
        advisor = config.get("advisor", "")
        u = result["usage"]
        exec_rates = PRICING.get(executor, {})
        adv_rates = PRICING.get(advisor, {})
        total += u["executor_input_tokens"] * exec_rates.get("input", 0) / 1_000_000
        total += u["executor_output_tokens"] * exec_rates.get("output", 0) / 1_000_000
        total += u["advisor_input_tokens"] * adv_rates.get("input", 0) / 1_000_000
        total += u["advisor_output_tokens"] * adv_rates.get("output", 0) / 1_000_000

    return round(total, 6)


# ---------------------------------------------------------------------------
# Comparison report
# ---------------------------------------------------------------------------

def generate_comparison(advisor_result: dict, baseline_result: dict) -> dict:
    """Compare advisor pattern vs direct baseline."""
    adv_cost = estimate_cost(advisor_result)
    base_cost = estimate_cost(baseline_result)

    comparison = {
        "track": advisor_result["track"],
        "advisor_elapsed": advisor_result.get("elapsed_seconds"),
        "baseline_elapsed": baseline_result.get("elapsed_seconds"),
        "advisor_cost_usd": adv_cost,
        "baseline_cost_usd": base_cost,
    }

    if adv_cost and base_cost and base_cost > 0:
        savings = (base_cost - adv_cost) / base_cost * 100
        comparison["cost_savings_pct"] = round(savings, 1)
    else:
        comparison["cost_savings_pct"] = None

    comparison["advisor_total_tokens"] = advisor_result.get("usage", {}).get("total_tokens", 0)
    comparison["baseline_total_tokens"] = baseline_result.get("usage", {}).get("total_tokens", 0)
    comparison["advisor_calls_made"] = advisor_result.get("usage", {}).get("advisor_calls", 0)

    return comparison


# ---------------------------------------------------------------------------
# Main — run both tracks
# ---------------------------------------------------------------------------

def run_test(tracks: Optional[list] = None, include_baseline: bool = True):
    """Run the full test suite.

    Args:
        tracks: List of track names to run. None = all.
        include_baseline: If True, run direct-Opus baseline for comparison.
    """
    all_tracks = {
        "research_sweep": (TRACK_A_CONFIG, TRACK_A_PROMPT),
        "financial_recon": (TRACK_B_CONFIG, TRACK_B_PROMPT),
    }

    if tracks:
        selected = {k: v for k, v in all_tracks.items() if k in tracks}
    else:
        selected = all_tracks

    # Load existing results (append mode for 48-hour window)
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            all_results = json.load(f)
    else:
        all_results = {
            "test_id": f"advisor-test-{datetime.now().strftime('%Y%m%d')}",
            "started": datetime.now().isoformat(),
            "go_nogo_threshold": {
                "track_a_cost_reduction_pct": 60,
                "track_b_quality_score_gte_baseline": True,
            },
            "runs": [],
            "comparisons": [],
        }

    run_batch = {
        "batch_timestamp": datetime.now().isoformat(),
        "results": [],
    }

    for name, (config, prompt) in selected.items():
        log.info(f"\n{'='*60}")
        log.info(f"TRACK: {name}")
        log.info(f"{'='*60}")

        # Advisor pattern run
        advisor_result = run_advisor_task(config, prompt)
        advisor_result["estimated_cost_usd"] = estimate_cost(advisor_result)
        run_batch["results"].append(advisor_result)

        # Baseline run (direct Opus)
        if include_baseline:
            baseline_result = run_baseline(config, prompt)
            baseline_result["estimated_cost_usd"] = estimate_cost(baseline_result)
            run_batch["results"].append(baseline_result)

            # Comparison
            comp = generate_comparison(advisor_result, baseline_result)
            all_results["comparisons"].append(comp)

            log.info(f"\n--- {name} COMPARISON ---")
            adv_c = comp.get('advisor_cost_usd')
            base_c = comp.get('baseline_cost_usd')
            log.info(f"  Advisor cost:  ${adv_c:.4f}" if adv_c else "  Advisor cost:  N/A (error)")
            log.info(f"  Baseline cost: ${base_c:.4f}" if base_c else "  Baseline cost: N/A (error)")
            log.info(f"  Savings:       {comp.get('cost_savings_pct', 'N/A')}%")
            log.info(f"  Advisor calls: {comp.get('advisor_calls_made', 'N/A')}")

    all_results["runs"].append(run_batch)
    all_results["last_updated"] = datetime.now().isoformat()

    with open(RESULTS_PATH, "w") as f:
        json.dump(all_results, f, indent=2)
    log.info(f"\nResults saved to {RESULTS_PATH}")

    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Advisor Strategy 48-hour test harness"
    )
    parser.add_argument(
        "--track",
        choices=["research_sweep", "financial_recon"],
        help="Run a single track (default: both)",
    )
    parser.add_argument(
        "--backend",
        choices=["openrouter", "max_oauth", "api"],
        default="openrouter",
        help="API backend (default: openrouter)",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip the direct-Opus baseline run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config and exit without API calls",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("Track A:", json.dumps(TRACK_A_CONFIG, indent=2))
        print("Track B:", json.dumps(TRACK_B_CONFIG, indent=2))
        print(f"Backend: {args.backend}")
        print(f"Results: {RESULTS_PATH}")
        print(f"Log:     {LOG_PATH}")
        raise SystemExit(0)

    CLIENT, BACKEND, ADVISOR_SUPPORTED = _build_client(args.backend)
    log.info(f"Backend: {BACKEND} | Advisor beta: {'YES' if ADVISOR_SUPPORTED else 'NO'}")

    tracks = [args.track] if args.track else None
    results = run_test(tracks=tracks, include_baseline=not args.no_baseline)

    # Print summary
    for comp in results.get("comparisons", []):
        adv_c = comp.get('advisor_cost_usd')
        base_c = comp.get('baseline_cost_usd')
        sav = comp.get('cost_savings_pct', 'N/A')
        print(f"\n{comp['track']}:")
        print(f"  Test:     ${adv_c:.4f}" if adv_c else "  Test:     N/A")
        print(f"  Baseline: ${base_c:.4f}" if base_c else "  Baseline: N/A")
        print(f"  Savings:  {sav}%")
