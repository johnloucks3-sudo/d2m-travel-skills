"""
Wing Policy Engine — Enforcement Core
=====================================
core/policy/wing_policy.py

The single enforcement entry point for all Thunderbird Wing high-risk actions.
Every integration imports `check()` from here. Rules live in rules_registry.py.

FAIL CLOSED: any exception anywhere in evaluation yields a DENY. The engine
never throws to its caller — a broken policy engine must block, not pass.

Usage:
    from core.policy.wing_policy import check
    result = check({"tool": "Bash", "command": "python3 scripts/send_client.py"})
    if not result.allowed:
        ...  # blocked (DENY) or surfaced to Commander (GATE)

CLI:
    echo '{"tool":"Bash","command":"ls -la"}' | python3 -m core.policy.wing_policy --stdin
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import Optional

try:
    # normal package import
    from .rules_registry import REGISTRY, Decision
except ImportError:  # pragma: no cover - direct-script fallback
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from core.policy.rules_registry import REGISTRY, Decision


_AUDIT_LOG = "/home/john/Thunderbird/logs/policy_audit.jsonl"


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------
@dataclass
class PolicyResult:
    allowed: bool
    decision: str                 # "ALLOW" | "DENY" | "GATE" | (Decision value)
    rule_id: Optional[str]
    message: str
    require_gate: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


_ALLOW_RESULT_KW = dict(
    allowed=True,
    decision=Decision.ALLOW.value,
    rule_id=None,
    message="",
    require_gate=False,
)


def _deny_error(detail: str) -> PolicyResult:
    """Fail-closed result for any internal failure."""
    return PolicyResult(
        allowed=False,
        decision=Decision.DENY.value,
        rule_id="POLICY-ERROR",
        message=f"Policy engine failed closed: {detail}",
        require_gate=True,
    )


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------
def check(action_ctx: dict) -> PolicyResult:
    """
    Evaluate action_ctx against the REGISTRY. Returns a PolicyResult.

    - Iterates REGISTRY in order (DENY rules first, GATE next).
    - First rule whose predicate(ctx) is True determines the decision.
    - No rule matches → ALLOW.
    - ANY exception → fail closed (DENY, rule_id POLICY-ERROR).
    """
    try:
        if not isinstance(action_ctx, dict):
            return _deny_error("action_ctx is not a dict")

        platform = action_ctx.get("platform")

        for rule in REGISTRY:
            try:
                if not rule.applies_to_platform(platform):
                    continue
                if rule.predicate(action_ctx):
                    if rule.decision == Decision.DENY:
                        result = PolicyResult(
                            allowed=False,
                            decision=Decision.DENY.value,
                            rule_id=rule.id,
                            message=rule.message,
                            require_gate=False,
                        )
                    elif rule.decision == Decision.GATE:
                        result = PolicyResult(
                            allowed=False,
                            decision=Decision.GATE.value,
                            rule_id=rule.id,
                            message=rule.message,
                            require_gate=True,
                        )
                    else:  # ALLOW rule explicitly matched
                        result = PolicyResult(rule_id=rule.id, **{
                            k: v for k, v in _ALLOW_RESULT_KW.items() if k != "rule_id"
                        })
                    _safe_audit(action_ctx, result)
                    return result
            except Exception as pred_err:  # a single predicate failing → fail closed
                return _deny_error(f"predicate {rule.id} raised: {pred_err}")

        result = PolicyResult(**_ALLOW_RESULT_KW)
        _safe_audit(action_ctx, result)
        return result

    except Exception as e:  # outer guard — nothing escapes
        return _deny_error(repr(e))


# ---------------------------------------------------------------------------
# Named wrappers
# ---------------------------------------------------------------------------
def check_relay_action(target: str, message: str, platform: str = "claude_code") -> PolicyResult:
    return check({
        "tool": "relay",
        "command": f"relay_send({target!r}, ...)",
        "payload": message,
        "platform": platform,
        "extra": {"action": "relay", "target": target},
    })


def check_telegram_send(chat_id, text: str, bot: str = "", platform: str = "telegram") -> PolicyResult:
    return check({
        "tool": "telegram_send",
        "payload": text,
        "recipient": str(chat_id),
        "platform": platform,
        "extra": {"action": "telegram_send", "bot": bot, "chat_id": chat_id},
    })


def check_draft_send(draft_id: str, recipient: str, platform: str = "claude_code") -> PolicyResult:
    # A SEND of an existing draft — subject to the client-send prohibition.
    return check({
        "tool": "gmail_send_draft",
        "recipient": recipient,
        "platform": platform,
        "extra": {"action": "draft_send", "draft_id": draft_id},
    })


def check_spawn(prompt: str, model: str = "", platform: str = "claude_code") -> PolicyResult:
    return check({
        "tool": "headless_spawn",
        "payload": prompt,
        "platform": platform,
        "extra": {"action": "spawn", "model": model},
    })


# ---------------------------------------------------------------------------
# Prompt summary — for injection into headless spawn prompts
# ---------------------------------------------------------------------------
def summary_for_prompt() -> str:
    """Compact human-readable rule summary, one line per rule."""
    lines = ["WING POLICY ENGINE — enforced rules (core/policy):"]
    try:
        for rule in REGISTRY:
            lines.append(f"{rule.decision.value}: [{rule.id}] — {rule.message}")
    except Exception:
        lines.append("(rule registry unavailable — all high-risk actions DENIED by default)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audit — best effort, never raises
# ---------------------------------------------------------------------------
def _safe_audit(action_ctx: dict, result: "PolicyResult") -> None:
    try:
        log_to_audit(action_ctx, result)
    except Exception:
        pass


def log_to_audit(action_ctx: dict, result: "PolicyResult") -> None:
    """Append a JSONL audit line. Best-effort; swallows all errors."""
    try:
        # redact payload to a length marker so PII is not written to the audit log
        ctx_safe = {}
        for k, v in (action_ctx or {}).items():
            if k == "payload" and isinstance(v, str):
                ctx_safe[k] = f"<payload len={len(v)}>"
            elif k == "extra" and isinstance(v, dict):
                ctx_safe[k] = {ek: ev for ek, ev in v.items() if ek not in ("payload",)}
            else:
                ctx_safe[k] = v
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "ctx": ctx_safe,
            "result": result.to_dict() if hasattr(result, "to_dict") else str(result),
        }
        os.makedirs(os.path.dirname(_AUDIT_LOG), exist_ok=True)
        with open(_AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        # never raise from the audit path
        return


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------
def _main(argv) -> int:
    if "--summary" in argv:
        print(summary_for_prompt())
        return 0
    if "--stdin" in argv:
        try:
            raw = sys.stdin.read()
            ctx = json.loads(raw) if raw.strip() else {}
        except Exception as e:
            res = _deny_error(f"bad stdin json: {e}")
            print(json.dumps(res.to_dict()))
            return 0
        res = check(ctx)
        print(json.dumps(res.to_dict()))
        return 0
    # default: print summary
    print(summary_for_prompt())
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
