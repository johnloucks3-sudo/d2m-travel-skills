#!/usr/bin/env python3
"""
Hale Dispatcher Runtime — The actual model-routing engine.

Wires together:
- agents/hale_substrate_chain.py  (decision logic, Opus build)
- core/ai_infra/thunderbird_headless_spawn.py  (foolproof MAX OAuth caller)
- core/ops/dispatch_telemetry.py  (cost/usage tracking)

This is what callers should use for substrate-aware dispatch:

    from agents.hale_dispatcher_runtime import dispatch_with_telemetry
    result = dispatch_with_telemetry(
        request="Hale, what's the McLeod FPD status?",
        default_substrate="haiku",
    )
    # result["response"] = the actual model output
    # result["telemetry"] = the recorded event

Routes 80% of work through MAX OAuth (Sonnet/Opus/Haiku) at $0 marginal.
Falls back to API only when MAX rate-limited or for substrates not under MAX.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

_ROOT = Path("/home/john/Thunderbird")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.hale_substrate_chain import dispatch as _chain_dispatch
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
from core.ai_infra.hale_persona_loader import wrap_with_persona
from core.ops.dispatch_telemetry import log_dispatch


# Substrate name → headless model alias mapping
_MAX_OAUTH_MODELS = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
}


def _max_oauth_caller(substrate: str, request: str, channel: Optional[str] = None) -> tuple[str, str]:
    """Call a Claude model via headless MAX OAuth. Returns (response, executed_via).

    Wraps Sonnet/Opus calls with Hale persona so the model responds AS Hale.
    Haiku stays unwrapped (routine work — persona overhead would waste tokens).
    """
    if substrate not in _MAX_OAUTH_MODELS:
        return _fallback_caller(substrate, request)

    # Inject Hale persona for Sonnet/Opus tier (where persona-quality matters).
    # Skip for Haiku (routine/classification — persona context wastes tokens).
    if substrate in ("sonnet", "opus"):
        prompt = wrap_with_persona(request, channel=channel)
    else:
        prompt = request

    model_alias = _MAX_OAUTH_MODELS[substrate]
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=f"/tmp/hale_dispatch_{int(time.time() * 1000)}.txt",
        model=model_alias,
        task_name=f"dispatch_{substrate}",
        background=False,
        timeout=180,
    )

    if result["status"] == "COMPLETED":
        try:
            response = Path(result["output_file"]).read_text()
            return response.strip(), "max_oauth"
        except Exception:
            return f"[ERROR: output file unreadable: {result['output_file']}]", "error"

    # MAX failed — try API fallback if available, else return error sentinel
    return _fallback_caller(substrate, request, max_failure=result)


def _fallback_caller(substrate: str, request: str, max_failure: Optional[dict] = None) -> tuple[str, str]:
    """Stub fallback. Hook in DeepSeek / Gemini / OpenRouter here when needed."""
    err = ""
    if max_failure:
        err = f" (MAX failed: {max_failure.get('status')}, {max_failure.get('error', '')})"
    return (
        f"[FALLBACK PLACEHOLDER for substrate={substrate}{err}. "
        "Wire DeepSeek/Gemini caller here.]",
        "fallback_unimplemented",
    )


def dispatch_with_telemetry(
    request: str,
    default_substrate: str = "haiku",
    enable_supervisor: bool = True,
    skip_actual_call: bool = False,
) -> dict:
    """End-to-end dispatch with telemetry capture.

    Args:
        request: Raw request text.
        default_substrate: Substrate to use when no Hale-tier override fires.
        enable_supervisor: If False, skip Layer 3 entirely (testing).
        skip_actual_call: If True, simulate without actually calling a model
                          (useful for dry-run telemetry tests).

    Returns:
        Dict with: response, substrate_used, escalated, selection,
                   supervision, telemetry (the logged record), duration_s.
    """
    t_start = time.time()

    # Track which path was actually executed (set by call_model wrapper)
    execution_path = {"executed_via": "test" if skip_actual_call else "pending"}

    def _call_model(substrate: str, prompt: str) -> str:
        if skip_actual_call:
            return f"[SIM substrate={substrate} prompt_len={len(prompt)}]"
        response, executed_via = _max_oauth_caller(substrate, prompt)
        execution_path["executed_via"] = executed_via
        return response

    chain_result = _chain_dispatch(
        request=request,
        call_model=_call_model,
        default_substrate=default_substrate,
        enable_supervisor=enable_supervisor,
    )

    duration = time.time() - t_start

    telemetry_record = log_dispatch(
        request=request,
        response=chain_result["response"],
        substrate=chain_result["substrate_used"],
        selection_source=chain_result["selection"]["source"],
        selection_reason=chain_result["selection"]["reason"],
        executed_via=execution_path["executed_via"],
        escalated=chain_result["escalated"],
        duration_s=duration,
        supervision=chain_result.get("supervision"),
    )

    return {
        **chain_result,
        "duration_s": duration,
        "telemetry": telemetry_record,
    }


# ─── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Hale Dispatcher Runtime CLI")
    parser.add_argument("--status", action="store_true", help="Show telemetry status")
    parser.add_argument("--rollup", action="store_true", help="Generate daily rollup JSON")
    parser.add_argument("--dispatch", type=str, help="Dispatch a request and show result")
    parser.add_argument("--default", type=str, default="haiku",
                        help="Default substrate for routine requests")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate dispatch without calling a real model")
    args = parser.parse_args()

    if args.status:
        from core.ops.dispatch_telemetry import status_report
        print(status_report())
    elif args.rollup:
        from core.ops.dispatch_telemetry import daily_rollup
        print(json.dumps(daily_rollup(), indent=2))
    elif args.dispatch:
        result = dispatch_with_telemetry(
            args.dispatch,
            default_substrate=args.default,
            skip_actual_call=args.dry_run,
        )
        print(json.dumps({
            "substrate_used": result["substrate_used"],
            "selection_source": result["selection"]["source"],
            "selection_reason": result["selection"]["reason"],
            "escalated": result["escalated"],
            "duration_s": result["duration_s"],
            "executed_via": result["telemetry"]["executed_via"],
            "response_preview": result["response"][:200],
            "cost_actual": result["telemetry"]["cost_actual_usd"],
            "savings": result["telemetry"]["savings_usd"],
        }, indent=2))
    else:
        parser.print_help()
