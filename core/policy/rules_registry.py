"""
Wing Policy Engine — Rules Registry
====================================
core/policy/rules_registry.py

THE single source of truth for Thunderbird Wing compliance enforcement.
CLAUDE.md and standing orders REFERENCE this file — they do not duplicate it.

Each Rule carries a Python predicate (callable: action_ctx dict -> bool). When
the predicate returns True, the rule's Decision applies. The REGISTRY tuple is
ordered DENY-before-GATE-before-ALLOW so that the first matching rule in
check() yields the most-restrictive applicable decision.

DESIGN INVARIANTS (do not break these — they are load-bearing for fail-closed):
  1. Every predicate confirms the ACTION CATEGORY first (is this actually an
     email send / draft create / relay dispatch / browser nav / bash send?).
     Only then does it apply the negative ("NOT in allowlist") or content test.
  2. No predicate may default to True on a missing key. A bare ctx like
     {'tool': 'Bash', 'command': 'ls -la'} must match NO restrictive rule.
  3. All key access via .get(). Predicates never raise on the minimal ctx.

action_ctx keys (all optional, accessed defensively):
  tool       : harness tool name (e.g. "Bash", "browser_navigate", "mcp__...create_draft")
  command    : shell command string (Bash)
  file_path  : target file for an edit/write/delete
  url        : navigation target (browser)
  recipient  : email recipient address
  payload    : message / draft body / text content
  platform   : "claude_code" | "opencode" | "telegram" | ...
  extra      : dict of structured hints. Recognized:
                 extra["action"] in {"email_send","draft_create","draft_send",
                                      "relay","telegram_send","spawn","browser"}
                 extra["account"]      : sending account ("d2mconcierge", ...)
                 extra["is_client"]    : bool — product is client-facing
                 extra["target"]       : relay dispatch target ("OC","CC","deepseek"...)
                 extra["weapons_free"] : bool — Weapons Free mode active
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Tuple

# ---------------------------------------------------------------------------
# Repo root — used to normalize protected paths to absolute canonical form.
# ---------------------------------------------------------------------------
REPO_ROOT = "/home/john/Thunderbird"


def _abs(rel: str) -> str:
    return os.path.normpath(os.path.join(REPO_ROOT, rel))


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"          # hard block, silent or logged
    GATE = "GATE"          # block + surface to Commander (NOT silent)


class ActionType(str, Enum):
    EMAIL_SEND = "email_send"
    DRAFT_CREATE = "draft_create"
    DRAFT_SEND = "draft_send"
    RELAY = "relay"
    TELEGRAM_SEND = "telegram_send"
    SPAWN = "spawn"
    BROWSER = "browser"
    FILE_WRITE = "file_write"
    BASH = "bash"
    ANY = "any"


# ---------------------------------------------------------------------------
# Protected paths — the policy engine is SELF-PROTECTING.
# 6 original relay/email-scanner files + 4 engine/config files = 10 total.
# Stored as absolute canonical paths.
# ---------------------------------------------------------------------------
_RELAY_PROTECTED = (
    "OpsCenter/run_commander_directive_sweep.py",
    "OpsCenter/dispatch_and_email.py",
    "OpsCenter/email_task_ingest.py",
    "core/email/thunderbird_commander_inbox.py",
    "OpsCenter/relay_send.py",
    "core/relay/wing_relay.py",
)

_ENGINE_PROTECTED = (
    "core/policy/wing_policy.py",
    "core/policy/rules_registry.py",
    ".claude/settings.json",
    "opencode.json",
)

# The 6 relay/email-scanner files (SO 2026-06-08) — used by PROTECTED-FILES-005.
RELAY_PROTECTED_PATHS = frozenset(_abs(p) for p in _RELAY_PROTECTED)

# All 10 protected files — used by SELF-DISABLE-001.
PROTECTED_PATHS = frozenset(_abs(p) for p in (_RELAY_PROTECTED + _ENGINE_PROTECTED))


# ---------------------------------------------------------------------------
# Within-wing email allowlist. Sends here do NOT trip the client-send gate.
# Membership = exact address match OR the "johnloucks3" substring clause.
# ---------------------------------------------------------------------------
INTERNAL_ALLOWLIST = frozenset({
    "johnloucks3@gmail.com",
    "susanna.loucks.d2m@gmail.com",
    "bryanajarboe@gmail.com",
    "rwestbrook3@gmail.com",
    "iamheer@gmail.com",
    "d2mconcierge@gmail.com",
    "concierge@d2mluxury.quest",
})

_INTERNAL_SUBSTRINGS = ("johnloucks3",)


# ---------------------------------------------------------------------------
# Helpers — all defensive: never raise on a minimal ctx.
# ---------------------------------------------------------------------------
def _s(ctx: dict, key: str) -> str:
    """Return ctx[key] as a lowercased string, '' if missing/None."""
    v = ctx.get(key)
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def _extra(ctx: dict) -> dict:
    e = ctx.get("extra")
    return e if isinstance(e, dict) else {}


def _action(ctx: dict) -> str:
    """Structured action discriminator, lowercased ('' if absent)."""
    a = _extra(ctx).get("action")
    return a.lower() if isinstance(a, str) else ""


def is_internal(recipient: Optional[str]) -> bool:
    """True iff recipient is a within-wing address (exact or substring clause)."""
    if not recipient or not isinstance(recipient, str):
        return False
    r = recipient.strip().lower()
    if r in INTERNAL_ALLOWLIST:
        return True
    return any(sub in r for sub in _INTERNAL_SUBSTRINGS)


def _normalized_path_candidates(ctx: dict) -> Tuple[str, ...]:
    """
    Collect candidate absolute paths from file_path and any path-like tokens in
    a bash command, normalized to canonical absolute form for comparison
    against PROTECTED_PATHS. Handles both absolute and repo-relative paths.
    """
    cands = []
    fp = ctx.get("file_path")
    if isinstance(fp, str) and fp.strip():
        cands.append(fp.strip())

    cmd = ctx.get("command")
    if isinstance(cmd, str) and cmd.strip():
        # pull out whitespace-separated tokens that look like paths
        for tok in re.split(r"[\s'\"=]+", cmd):
            if not tok:
                continue
            if "/" in tok or tok.endswith(".py") or tok.endswith(".json"):
                cands.append(tok)

    out = []
    for c in cands:
        c = c.strip().strip("'\"")
        if not c:
            continue
        if os.path.isabs(c):
            out.append(os.path.normpath(c))
        else:
            out.append(_abs(c))
    return tuple(out)


def _targets_protected(ctx: dict, protected: frozenset) -> bool:
    for cand in _normalized_path_candidates(ctx):
        if cand in protected:
            return True
    return False


# ---------------------------------------------------------------------------
# Email-send detection. A SEND is distinct from a draft-create.
# ---------------------------------------------------------------------------
_SEND_TOOLS = (
    "gmail_send_email", "send_client_email", "send_email", "messages_send",
    "gmail_send_draft", "send_message",
)


def _is_email_send(ctx: dict) -> bool:
    """True only when ctx genuinely represents an outbound email SEND."""
    if _action(ctx) in ("email_send", "draft_send"):
        return True
    tool = _s(ctx, "tool").lower()
    if any(t in tool for t in _SEND_TOOLS):
        # explicitly exclude create_draft tools that contain "send" by accident
        if "create_draft" in tool or "createdraft" in tool:
            return False
        return True
    return False


def _is_draft_create(ctx: dict) -> bool:
    if _action(ctx) == "draft_create":
        return True
    tool = _s(ctx, "tool").lower()
    return ("create_draft" in tool) or ("createdraft" in tool)


def _has_recipient(ctx: dict) -> bool:
    r = ctx.get("recipient")
    return isinstance(r, str) and bool(r.strip())


# ---------------------------------------------------------------------------
# Financial / negative-space content patterns (client-copy gates)
# ---------------------------------------------------------------------------
_NEGSPACE_TERMS = ("likely", "probably", "pending", "our understanding")

# a dollar figure like $1,234 or $24,798.00 or $480
_DOLLAR_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
# source tags that legitimize a dollar figure
_SOURCE_TERMS = ("portal", "tess", "dossier", "source:", "confirmed:")

# booking-number-like pattern (6+ digits, optionally with a -NN suffix)
_BOOKING_RE = re.compile(r"\b\d{6,}(?:-\d{1,3})?\b")
# crude "personal name" pattern: two Capitalized words in a row
_NAME_RE = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")


def _is_client(ctx: dict) -> bool:
    return bool(_extra(ctx).get("is_client"))


# ---------------------------------------------------------------------------
# Relay / PII detection
# ---------------------------------------------------------------------------
_OC_TARGETS = ("oc", "deepseek", "opencode")


def _relay_target(ctx: dict) -> str:
    t = _extra(ctx).get("target")
    if isinstance(t, str) and t.strip():
        return t.strip().lower()
    # fall back to scanning a relay command
    return ""


def _is_relay(ctx: dict) -> bool:
    if _action(ctx) == "relay":
        return True
    cmd = _s(ctx, "command").lower()
    return ("relay_send" in cmd) or ("wing_relay" in cmd)


def _payload_has_pii(ctx: dict) -> bool:
    p = _s(ctx, "payload")
    if not p:
        return False
    return bool(_BOOKING_RE.search(p) or _NAME_RE.search(p))


# ---------------------------------------------------------------------------
# Browser detection
# ---------------------------------------------------------------------------
_JS_TOOLS = ("browser_evaluate", "browser_run_code_unsafe", "javascript_tool")


def _tool_is(ctx: dict, *names: str) -> bool:
    tool = _s(ctx, "tool").lower()
    return any(n.lower() in tool for n in names)


# ---------------------------------------------------------------------------
# Bash mutating-operation detection (for SELF-DISABLE predicate).
# Only operations that actually WRITE or DELETE a file are considered mutating.
# Read-only ops (grep, cat, git add, git log, py_compile) are explicitly allowed.
# ---------------------------------------------------------------------------
_MUTATING_BASH_CMDS = frozenset({
    "rm", "rmdir", "unlink", "shred", "truncate", "dd", "mv", "install", "patch",
    "cp", "tee", "ln",   # cp overwrites dest; tee writes stdin to args; ln may replace
})
_BASH_INPLACE_RE = re.compile(
    r"\bsed\s+\S*-[iI]\S*"       # sed -i / sed --in-place variants
    r"|\bperl\s+-[pni]*i",           # perl -pi -e
    re.IGNORECASE,
)
def _bash_redirects_to_protected(cmd: str) -> bool:
    """True only when stdout redirect destination is a protected file."""
    for m in re.finditer(r'>{1,2}\s*(\S+)', cmd):
        target = m.group(1).strip("'\"")
        norm = (os.path.normpath(target)
                if os.path.isabs(target)
                else _abs(target))
        if norm in PROTECTED_PATHS:
            return True
    for m in re.finditer(r'\|\s*tee\s+(\S+)', cmd):
        target = m.group(1).strip("'\"")
        norm = (os.path.normpath(target)
                if os.path.isabs(target)
                else _abs(target))
        if norm in PROTECTED_PATHS:
            return True
    return False


_BASH_GIT_DESTRUCTIVE_RE = re.compile(
    r"\bgit\s+(?:checkout\s+--|restore\s+\S|reset\s+--hard\b)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Bash send / relay pattern detection
# ---------------------------------------------------------------------------
# matches: .send(  |  send_<word>.py  |  messages().send  |  drafts().send
_BASH_SEND_RE = re.compile(
    r"\.send\s*\(|send_[\w-]*\.py|messages\s*\(\s*\)\s*\.\s*send|drafts\s*\(\s*\)\s*\.\s*send",
    re.IGNORECASE,
)


def _is_bash(ctx: dict) -> bool:
    return _tool_is(ctx, "Bash")


# ---------------------------------------------------------------------------
# Spawn detection
# ---------------------------------------------------------------------------
def _is_spawn(ctx: dict) -> bool:
    if _action(ctx) == "spawn":
        return True
    return _tool_is(ctx, "spawn", "headless")


_SPAWN_SEND_TERMS = ("send to", "email")


# ===========================================================================
# Predicates — each confirms category FIRST, then applies the test.
# ===========================================================================

# 1. SELF-DISABLE-001 — DENY (mutating ops only for Bash; always blocks Edit/Write)
def _p_self_disable(ctx: dict) -> bool:
    tool = ctx.get("tool", "")

    # Edit / Write / MultiEdit always mutate — check file_path only
    if tool in ("Edit", "Write", "MultiEdit"):
        fp = ctx.get("file_path", "") or ""
        if not fp:
            return False
        norm = os.path.normpath(fp) if os.path.isabs(fp) else _abs(fp)
        return norm in PROTECTED_PATHS

    # Bash — only block if a protected path is targeted AND a mutating op is present.
    # Read-only ops (grep, cat, git add, git log, py_compile) fall through to False.
    if tool == "Bash":
        cmd = ctx.get("command", "") or ""
        if not cmd:
            return False
        # Step 1: does the command reference any protected path?
        if not any(cand in PROTECTED_PATHS for cand in _normalized_path_candidates(ctx)):
            return False
        # Step 2: is the operation mutating?
        tokens = re.split(r"[\s;|&]+", cmd.strip())
        first = tokens[0].split("/")[-1] if tokens else ""
        if first in _MUTATING_BASH_CMDS:
            return True
        if _BASH_INPLACE_RE.search(cmd):
            return True
        if _bash_redirects_to_protected(cmd):
            return True
        if _BASH_GIT_DESTRUCTIVE_RE.search(cmd):
            return True
        return False  # read-only op — allowed

    return False


# 2. WF17-CLIENT-SEND-001 — DENY (absolute client-send prohibition)
def _p_wf17_client_send(ctx: dict) -> bool:
    if not _is_email_send(ctx):
        return False
    if not _has_recipient(ctx):
        return False  # no recipient → cannot assert a client send
    return not is_internal(ctx.get("recipient"))


# 3. DRAFT-JL3-002 — GATE
def _p_draft_jl3(ctx: dict) -> bool:
    if not _is_draft_create(ctx):
        return False
    if not _has_recipient(ctx):
        return False
    return is_internal(ctx.get("recipient")) and ("johnloucks3" in _s(ctx, "recipient").lower())


# 4. PROTECTED-FILES-005 — DENY (the 6 relay files)
def _p_protected_files(ctx: dict) -> bool:
    return _targets_protected(ctx, RELAY_PROTECTED_PATHS)


# 5. PIPELINE-NEGSPACE-006 — GATE
def _p_negspace(ctx: dict) -> bool:
    if not (_is_draft_create(ctx) and _is_client(ctx)):
        return False
    p = _s(ctx, "payload").lower()
    if not p:
        return False
    return any(term in p for term in _NEGSPACE_TERMS)


# 6. PIPELINE-FINSOURCE-007 — GATE
def _p_finsource(ctx: dict) -> bool:
    if not (_is_draft_create(ctx) and _is_client(ctx)):
        return False
    p = _s(ctx, "payload")
    if not p:
        return False
    if not _DOLLAR_RE.search(p):
        return False
    low = p.lower()
    # dollar figure present AND no source tag anywhere in the copy
    return not any(s in low for s in _SOURCE_TERMS)


# 7. PII-EGRESS-011 — DENY
def _p_pii_egress(ctx: dict) -> bool:
    if not _is_relay(ctx):
        return False
    target = _relay_target(ctx)
    cmd = _s(ctx, "command").lower()
    target_is_oc = any(t in target for t in _OC_TARGETS) or any(t in cmd for t in _OC_TARGETS)
    if not target_is_oc:
        return False
    return _payload_has_pii(ctx)


# 8. BROWSER-ARBIT-JS — DENY
def _p_browser_js(ctx: dict) -> bool:
    return _tool_is(ctx, *_JS_TOOLS)


# 9. BROWSER-MAIL-NAV — GATE
def _p_browser_mail_nav(ctx: dict) -> bool:
    if not _tool_is(ctx, "browser_navigate"):
        return False
    url = _s(ctx, "url").lower()
    if not url:
        return False
    return ("mail.google.com" in url) or ("web.telegram.org" in url)


# 10. CONCIERGE-SEND-LIST-018 — DENY
def _p_concierge_send(ctx: dict) -> bool:
    if not _is_email_send(ctx):
        return False
    if _extra(ctx).get("account", "").lower() != "d2mconcierge":
        return False
    if not _has_recipient(ctx):
        return False
    return not is_internal(ctx.get("recipient"))


# 11. BASH-SEND-PATTERN — DENY
def _p_bash_send(ctx: dict) -> bool:
    if not _is_bash(ctx):
        return False
    cmd = _s(ctx, "command")
    if not cmd:
        return False
    return bool(_BASH_SEND_RE.search(cmd))


# 12. BASH-RELAY-CALL — GATE
def _p_bash_relay(ctx: dict) -> bool:
    if not _is_bash(ctx):
        return False
    cmd = _s(ctx, "command").lower()
    if not cmd:
        return False
    return ("relay_send" in cmd) or ("wing_relay" in cmd)


# 13. SPAWN-PROMPT-CHECK — GATE
def _p_spawn_prompt(ctx: dict) -> bool:
    if not _is_spawn(ctx):
        return False
    prompt = _s(ctx, "payload").lower()
    if not prompt:
        return False
    if any(term in prompt for term in _SPAWN_SEND_TERMS):
        return True
    # client-name-like pattern in spawn prompt
    return bool(_NAME_RE.search(_s(ctx, "payload")))


# 14. WEAPONS-FREE-GATES-019 — DENY (inviolable)
def _p_weapons_free_gates(ctx: dict) -> bool:
    """
    The three Commander gates survive Weapons Free. This rule fires only when
    Weapons Free is explicitly active AND one of rules 2/3/4's conditions holds
    — making the survival of those gates explicit and auditable. It NEVER fires
    on a benign ctx.
    """
    if not _extra(ctx).get("weapons_free"):
        return False
    return _p_wf17_client_send(ctx) or _p_draft_jl3(ctx) or _p_protected_files(ctx)


# ===========================================================================
# Rule dataclass
# ===========================================================================
@dataclass(frozen=True)
class Rule:
    id: str
    action_type: ActionType
    platforms: Tuple[str, ...]          # () == all platforms
    decision: Decision
    predicate: Callable[[dict], bool]
    message: str
    so_ref: str
    inviolable: bool = False            # survives Weapons Free / overrides

    def applies_to_platform(self, platform: Optional[str]) -> bool:
        if not self.platforms:
            return True
        if not platform:
            return True
        return platform.lower() in tuple(p.lower() for p in self.platforms)


ALL = ()  # all platforms


# ===========================================================================
# REGISTRY — ordered DENY (most restrictive) before GATE.
# check() returns on first match, so order encodes precedence.
# ===========================================================================
REGISTRY: Tuple[Rule, ...] = (
    # ---- DENY rules ----
    Rule(
        id="WEAPONS-FREE-GATES-019",
        action_type=ActionType.ANY,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_weapons_free_gates,
        message="Three Commander gates survive Weapons Free — no override.",
        so_ref="feedback_weapons_free_declaration.md",
        inviolable=True,
    ),
    Rule(
        id="SELF-DISABLE-001",
        action_type=ActionType.FILE_WRITE,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_self_disable,
        message="Wing policy engine is self-protecting — cannot edit/delete enforcement files.",
        so_ref="SO_EMAIL_SCANNER_PROTECT_20260608.md",
        inviolable=True,
    ),
    Rule(
        id="PROTECTED-FILES-005",
        action_type=ActionType.FILE_WRITE,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_protected_files,
        message="Protected files cannot be modified autonomously.",
        so_ref="SO_EMAIL_SCANNER_PROTECT_20260608.md",
        inviolable=True,
    ),
    Rule(
        id="WF17-CLIENT-SEND-001",
        action_type=ActionType.EMAIL_SEND,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_wf17_client_send,
        message="Client-send prohibition — Commander is sole send executor for client communications.",
        so_ref="SO_WF17_CLIENTSEND_PROHIBITION_20260530.md",
        inviolable=True,
    ),
    Rule(
        id="CONCIERGE-SEND-LIST-018",
        action_type=ActionType.EMAIL_SEND,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_concierge_send,
        message="Concierge direct sends limited to within-wing allowlist.",
        so_ref="SO_EMAIL_RULES_UPDATE_20260530.md",
    ),
    Rule(
        id="PII-EGRESS-011",
        action_type=ActionType.RELAY,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_pii_egress,
        message="PII fence: client PII cannot egress to OC/DeepSeek.",
        so_ref="hale_cos.md#PII-Fence",
    ),
    Rule(
        id="BROWSER-ARBIT-JS",
        action_type=ActionType.BROWSER,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_browser_js,
        message="Browser arbitrary-JS denylisted on client-send path.",
        so_ref="SO_PIPELINE_INTEGRITY_20260528.md",
    ),
    Rule(
        id="BASH-SEND-PATTERN",
        action_type=ActionType.BASH,
        platforms=ALL,
        decision=Decision.DENY,
        predicate=_p_bash_send,
        message="Bash send pattern detected — use WF-17 gate.",
        so_ref="SO_WF17_CLIENTSEND_PROHIBITION_20260530.md",
    ),
    # ---- GATE rules ----
    Rule(
        id="DRAFT-JL3-002",
        action_type=ActionType.DRAFT_CREATE,
        platforms=ALL,
        decision=Decision.GATE,
        predicate=_p_draft_jl3,
        message="Draft to johnloucks3 requires explicit Commander OK — hold at WF-17.",
        so_ref="SO_DRAFT_ROUTING_20260614.md",
    ),
    Rule(
        id="PIPELINE-NEGSPACE-006",
        action_type=ActionType.DRAFT_CREATE,
        platforms=ALL,
        decision=Decision.GATE,
        predicate=_p_negspace,
        message="Negative-space rule: unconfirmed facts banned in client copy.",
        so_ref="SO_PIPELINE_INTEGRITY_20260528.md#Rule1",
    ),
    Rule(
        id="PIPELINE-FINSOURCE-007",
        action_type=ActionType.DRAFT_CREATE,
        platforms=ALL,
        decision=Decision.GATE,
        predicate=_p_finsource,
        message="Financial figures require portal/TESS/dossier source.",
        so_ref="SO_PIPELINE_INTEGRITY_20260528.md#Rule4",
    ),
    Rule(
        id="BROWSER-MAIL-NAV",
        action_type=ActionType.BROWSER,
        platforms=ALL,
        decision=Decision.GATE,
        predicate=_p_browser_mail_nav,
        message="Browser navigation to mail/Telegram requires policy gate.",
        so_ref="SO_PIPELINE_INTEGRITY_20260528.md",
    ),
    Rule(
        id="BASH-RELAY-CALL",
        action_type=ActionType.BASH,
        platforms=ALL,
        decision=Decision.GATE,
        predicate=_p_bash_relay,
        message="Relay invocation — checking intent.",
        so_ref="SO_EMAIL_SCANNER_PROTECT_20260608.md",
    ),
    Rule(
        id="SPAWN-PROMPT-CHECK",
        action_type=ActionType.SPAWN,
        platforms=ALL,
        decision=Decision.GATE,
        predicate=_p_spawn_prompt,
        message="Spawn prompt contains potential client-send instruction.",
        so_ref="HEADLESS_CLAUDE_SPAWN_GUIDE.md",
    ),
)
