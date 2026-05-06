#!/usr/bin/env python3
"""
opencode_hale_shim.py — OpenCode integration shim for the Hale Dispatcher Runtime.

OpenCode subprocesses (DeepSeek V3.1 / Gemini Flash) run as the primary fast path
for Thunderbird ops tasks. This shim lets any OpenCode task check whether it should
escalate to Hale (Sonnet/Opus via MAX OAuth) before dispatching.

Usage (copy-paste into OpenCode task handlers):

    from agents.opencode_hale_shim import should_use_hale, dispatch_through_hale

    # Gate check — fast, no model call
    if should_use_hale(request):
        response = dispatch_through_hale(request, channel="opencode")
        # response is a plain string — write it to output file or return it
    else:
        # OpenCode native path (Gemini Flash / DeepSeek)
        response = my_native_engine(request)

Layer 1 keyword classification determines Hale-tier:
- Sonnet tier: "Hale", "strategy", "draft", "write", "voice", "decision", etc.
- Opus tier: "/opus", "/arbitrate", high-complexity flags
- Routine: everything else → stays on OpenCode native path

Cost note: Hale-tier calls go through MAX OAuth ($0 marginal on subscription).
Routine calls stay on OpenCode native path ($0.27/M DeepSeek or free Gemini).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path("/home/john/Thunderbird")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "OpsCenter") not in sys.path:
    sys.path.insert(0, str(_ROOT / "OpsCenter"))

from agents.hale_substrate_chain import select_substrate
from agents.hale_dispatcher_runtime import dispatch_with_telemetry


def should_use_hale(request: str) -> bool:
    """Return True if this request warrants Hale-tier routing (Sonnet or Opus).

    Fast call — no model invocation. Uses Layer 1/4 substrate classification.

    Args:
        request: The raw task text from OpenCode.

    Returns:
        True if substrate selection chose sonnet or opus; False for routine haiku/flash.
    """
    sel = select_substrate(request)
    return sel["substrate"] in ("sonnet", "opus")


def dispatch_through_hale(
    request: str,
    channel: str = "opencode",
    default_substrate: str = "haiku",
) -> str:
    """Dispatch a request through the Hale runtime and return the response string.

    Internally wires Layer 1 → Layer 4 substrate selection, MAX OAuth caller,
    Hale persona injection, and telemetry logging. Callers only see the response.

    Args:
        request: The raw task text.
        channel: Channel hint for persona injection ('opencode', 'telegram', 'email',
                 'claude_code'). Affects persona signaling in the prompt.
        default_substrate: Fallback substrate when neither Layer 1 nor Layer 4 fires.
                           Typically 'haiku' (routine) or 'sonnet' (if caller already
                           knows this is Hale-tier).

    Returns:
        Response string from the Hale model.

    Example:
        result = dispatch_through_hale("Hale, draft the McLeod follow-up", channel="opencode")
        # Returns the Hale-voiced response string
    """
    result = dispatch_with_telemetry(
        request,
        default_substrate=default_substrate,
    )
    return result["response"]
