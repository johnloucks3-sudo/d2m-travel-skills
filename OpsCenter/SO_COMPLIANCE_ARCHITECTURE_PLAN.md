# SO COMPLIANCE ARCHITECTURE ATTACK — IMPLEMENTATION PLAN
# Generated: 2026-06-18 | Thunderbird Wing, Dreams2Memories Travel, LLC
# Status: AWAITING COMMANDER APPROVAL — no code written
# Session: OODA Observe+Orient+Decide phase complete

---

## EXECUTIVE SUMMARY

🦅 EXECUTIVE SUMMARY

PROBLEM: Of 22 hard Standing-Order rules governing the Wing, 19 have no mechanical enforcement — they live as advisory prose in CLAUDE.md, AGENTS.md, and persona files, and the model is trusted to obey. The single live control (the MCP deny-list) covers only Claude Code's MCP tool names; the most dangerous rule of all — the absolute WF-17 client-send prohibition — is wide open on raw Bash/Python, browser automation, headless spawns, and OpenCode, exactly the surfaces with the highest violation risk.

SOLUTION: A single fail-closed policy engine (`core/policy/wing_policy.py`) backed by a canonical code rule registry, wired into every tool-capable surface — a Claude Code PreToolUse hook, the three Telegram gateway choke points, the headless-spawn wrapper, and a real OpenCode plugin — with a post-hoc audit as the backstop under the surfaces no engine can intercept. Enforcement lives ABOVE the six protected relay files; the primary build (Phases 1–3) requires no protected-file edit.

COMMANDER APPROVAL NEEDED FOR: (1) denylisting browser arbitrary-JS tools on the client-send path; (2) amending SO-2026-06-08 to add the engine's own files to the protected set; (3) the Phase 4 relay-file edits; (4) making the code registry canonical (this rewrites the 4 CLAUDE.md-family files = governance change); (5) acknowledging a correction to the task's premise that OpenCode cannot enforce — it can, and we will build that enforcement.

This is a RESEARCH/DESIGN paper. No code has been written. Build begins only on Commander approval of this plan.

================================================================
GOVERNING PRINCIPLE
================================================================

Enforcement an agent can Edit or Bash away is not enforcement. Every design choice below flows from that one truth. The engine must fail CLOSED (any error = DENY), must protect itself from deletion, and must scan the PAYLOAD of a tool call (command strings, URLs, recipients) — not merely match tool names, which would only re-cover the existing deny-list and enforce nothing new.

All three Commander gates are preserved and hardened, never relaxed: client send (WF-17), financial commitment, strategic decision. The engine makes them mechanical instead of advisory.

================================================================
PHASE 1 — CORE ENGINE + CLAUDE CODE PreToolUse HOOK
================================================================

NAME: Mechanical floor — the policy engine and its first enforcement surface.

OBJECTIVE: Stand up the single source of truth (`check()`) and prove it blocks the highest-risk gap — the raw Bash/Python `.send()` path — on Claude Code, including all headless `claude -p` children. Everything in Phases 2–4 depends on this engine; it is built first by necessity, not just priority.

SCOPE:
- `core/policy/rules_registry.py` — Python dataclasses (Rule, Decision, ActionType). Code, not JSON, because rules carry executable predicates and the module joins the protected set naturally. Encodes the 22 SO rules as predicates ordered DENY-before-GATE.
- `core/policy/wing_policy.py` — `check(action_ctx)` plus named wrappers (`check_draft_send`, `check_relay_action`, `check_telegram_send`, `check_spawn`). Top-level try/except returns DENY on ANY failure. Centralized self-disablement guard inspects command strings, file_path, and path args against PROTECTED_PATHS so switching Edit→sed→Write cannot evade it. Thin `--stdin` CLI entry for cross-language callers.
- `hooks/pretooluse_policy.py` — reads tool JSON from stdin, builds action_ctx, calls `check()`. Emits the explicit deny signal (deny-JSON on stdout, exit 0, or exit 2 + stderr) — never a bare non-zero exit, which Claude Code treats as a non-blocking error (fail-OPEN). A subprocess timeout guard wraps `check()`; timeout = deny.
- `.claude/settings.json` (PROJECT, not local/user) — register PreToolUse matchers for Bash, Edit|Write|MultiEdit, the playwright browser navigate/click/fill/type/evaluate tools, and the Gmail/draft MCP tools. MOVE browser_evaluate / browser_run_code_unsafe / Claude-in-Chrome javascript_tool to the permissions `deny` block (denylist, not policy-gate — arbitrary JS cannot be intent-scanned).
- Reconcile the settings.local.json drift that currently re-allows `mcp__claude_ai_Gmail__gmail_create_draft` (= johnloucks3), re-opening a closed gate.
- `hooks/posttooluse_audit.py` + `logs/policy_audit.jsonl` — the Option-3 backstop logger. Records every check result regardless of decision; foundation for the periodic sweep.

FILES MODIFIED: NEW: rules_registry.py, wing_policy.py, pretooluse_policy.py, posttooluse_audit.py. EDIT (non-protected): .claude/settings.json, settings.local.json. ZERO edits to any of the six protected files.

DEPENDENCIES: None. This is the foundation.

SUCCESS CRITERIA:
- A child `claude -p` Bash call attempting `service.users().messages().send()` or `python send_*.py` to a client recipient is BLOCKED under bypassPermissions (empirically verify — this is the load-bearing proof).
- A johnloucks3-recipient draft is GATED (blocked pending Commander), a client recipient DENIED, an internal (johnloucks3/susanna.loucks) send ALLOWED.
- A deliberately broken `wing_policy.py` (forced exception) produces DENY, not pass-through.
- An attempt to `Edit` or `Bash(sed)` against `.claude/settings.json` or the engine files is DENIED by the self-disable guard.
- Browser navigate to mail.google.com is intercepted; browser_evaluate is refused at the permission layer.

EFFORT: registry 4–6 h · wing_policy 4–5 h · CC hook + deny-signal correctness 3–4 h · browser denylist 0.5 h · audit logger 3–4 h · protected-set expansion + reconcile drift 1 h. PHASE 1 ≈ 16–21 h.

================================================================
PHASE 2 — TELEGRAM GATEWAY + HEADLESS SPAWN INTEGRATION
================================================================

NAME: Choke-point coverage — the autonomous injection and spawn paths.

OBJECTIVE: Close the relay-queue injection, the voice-transcribed `/approve` send, and the full-MCP headless spawn — the surfaces that act without a human in the loop. The Telegram gateway is NOT a protected file; direct import + guard is permitted.

SCOPE:
- `thunderbird_telegram_gw.py` — import wing_policy and call it at THREE non-negotiable sites: (1) `handle_approve`, before `drafts().send()` at ~L1125 — verify Commander-Review label + chain-completion marker + banned-phrase/dollar scan; this is the call that stops a transcribed "/approve" from publishing a client draft, which the COMMANDER_ID whitelist alone cannot. (2) `_drain_relay_queue` (~L1837), before `call_claude_engine` at 1870 — screen queued payloads for client-send/protected-file/PII intents, since `relay_send.enqueue()` writes with no sender verification. (3) `/agent` and `/ask` shell-outs — `check_spawn(prompt, model)` before dispatch. Plus a `check_telegram_send` wrap on the raw `sendMessage` for client-facing bots, leaving Commander-only D2MC2C traffic untouched.
- `core/ai_infra/thunderbird_headless_spawn.py`, `spawn_headless_claude` (~L143) — (a) pre-spawn `check_spawn` on the prompt; (b) ASSERT the child launches against the hook-bearing project settings dir and REJECT any flag that strips PreToolUse or repoints the settings dir (bypassPermissions is acceptable — the project hook still fires under it); (c) prepend a registry-generated policy banner (`summary_for_prompt()`) so the child both KNOWS the rules and cannot bypass them.
- Skill gates (ergonomic front doors, not the security boundary): `~/.claude/skills/send-telegram/`, `client-draft/`, `spawn-headless/` — each runs the relevant check as step one.
- ONE-LINE Signal note (NOT a phase): add a sender-allowlist guard `if sender != COMMANDER: log+return` to `thunderbird_signal_gw.py handle()`, mirroring the Telegram gate. Signal is LOW risk per the task and is not over-engineered — but it is live today with no sender check, mitigated only by a network binding a re-link defeats. The one-liner rides on this phase's spawn-wrapper work. No Signal phase, no extra build.

FILES MODIFIED: EDIT (non-protected): thunderbird_telegram_gw.py, thunderbird_headless_spawn.py, thunderbird_signal_gw.py. NEW: 3 SKILL.md files. ZERO protected-file edits.

DEPENDENCIES: Phase 1 (`check()` + wrappers must exist).

SUCCESS CRITERIA:
- A relay-queue entry instructing a client send is refused before reaching the Claude engine.
- A transcribed `/approve` on a draft lacking the Commander-Review label or chain marker is blocked with a Commander warning, not silently sent.
- A `/agent` spawn whose prompt says "email the client" is refused.
- A headless child's own Bash send is blocked (proves the inherited hook + settings-dir assertion).
- Signal inbound from a non-Commander sender is logged and dropped.

EFFORT: telegram 3 sites + sendMessage wrap 2–3 h · spawn pre-check + assertion + banner 2 h · skills 2 h · Signal one-liner 0.5 h. PHASE 2 ≈ 6.5–7.5 h.

================================================================
PHASE 3 — OPENCODE PLUGIN + AGENTS.md / REGISTRY REFERENCE
================================================================

NAME: OpenCode enforcement and the end of wording drift.

OBJECTIVE: Give OpenCode real, fail-closed enforcement and make the code registry the single source of truth that all governance markdown references rather than restates.

PREMISE CORRECTION (Commander, please note): The task names this phase "AGENTS.md + session startup," which encodes the assumption that OpenCode is advisory-only and cannot enforce. Verified inventory contradicts this: OpenCode's plugin SDK exposes `permission.ask` (a genuine deny/ask/allow gate) and `tool.execute.before` (arg mutation/abort). OpenCode CAN enforce mechanically — it simply has no plugin registered today, so it is SILENTLY advisory. I am building the plugin rather than settling for a startup notice. I surface this openly because it is the one place I override the task framing; it is a capability correction, not scope inflation.

SCOPE:
- `.opencode/plugin/wing_policy_plugin.js` — `tool.execute.before` shells out to `python3 core/policy/wing_policy.py --stdin` for every tool call; DENY/GATE aborts the tool. Fail-closed: subprocess error, timeout, or non-JSON = abort. `permission.ask` routes interactive requests through the same check.
- `opencode.json` — register the plugin via the `plugin` key (the file joins the protected set so the key cannot be silently dropped).
- `OpsCenter/state_bridge/session_startup_hook.py` — narrow added job ONLY: verify the plugin is registered and loaded; if absent, emit a loud "[POLICY] PLUGIN NOT LOADED — OC IS ADVISORY ONLY" warning into the briefing and to the audit log. It stays fail-soft and does NOT gate individual actions — per-action fail-closed lives in the plugin.
- AGENTS.md + the 4 CLAUDE.md-family files — REPLACE restated rules with a reference to `core/policy/rules_registry.py` as canonical. This is what actually kills the wording-drift root cause; without it Option 4 enforces but the prose keeps drifting. (Governance change — Commander decision below.)

FILES MODIFIED: NEW: wing_policy_plugin.js. EDIT (non-protected): opencode.json, session_startup_hook.py, AGENTS.md, CLAUDE.md ×4. ZERO protected-file edits.

DEPENDENCIES: Phase 1 (the `--stdin` CLI entry and `check()`).

SUCCESS CRITERIA:
- An OpenCode tool call attempting a client send is aborted by the plugin (fail-closed verified by forcing a subprocess error → abort).
- Plugin-load is confirmed in a live session; a deliberately unregistered plugin produces the loud advisory-only warning.
- A grep of the 4 CLAUDE.md files shows rule references, not restated rule text.

EFFORT: JS plugin + shell-out + opencode.json + load-verify 5–7 h (highest-uncertainty piece) · markdown→registry-reference rewrite 2 h. PHASE 3 ≈ 7–9 h.

================================================================
PHASE 4 — RELAY INTEGRATION (PROTECTED FILES — COMMANDER APPROVAL REQUIRED)
================================================================

NAME: Defense-in-depth at the relay boundary.

OBJECTIVE: Guard the call inside the relay layer itself. Phases 1–3 already cover relay indirectly (Bash-string scanning of `relay_send` invocations, the gateway `_drain_relay_queue` guard, and the audit). This phase adds the boundary guard inside the protected files — optional hardening, separated out precisely because it touches protected code.

SCOPE:
- `OpsCenter/relay_send.py` and `core/relay/wing_relay.py` — a one-line import plus a guard call before any send: `res = check_relay_action(target, message); if not res.allowed: raise PolicyViolation(res.message)`. No change to relay logic. Catches PII egress to OpenCode/DeepSeek and relay-borne client-send at the relay itself.

FILES MODIFIED: EDIT (PROTECTED — requires explicit Commander approval per SO-2026-06-08): relay_send.py, wing_relay.py. Claude Code (Hale) is the sole authorized executor.

DEPENDENCIES: Phases 1–3 complete; explicit Commander approval to touch protected files.

SUCCESS CRITERIA: A relay dispatch carrying client PII or a client-send instruction raises PolicyViolation and refuses, verified without altering legitimate internal relay traffic.

EFFORT: ≈ 2 h. Gated behind approval; not started until Phases 1–3 ship and Commander clears the protected-file edit.

================================================================
SESSION MAPPING (fits the 2–3 session constraint)
================================================================
- Session 1: Phase 1 + Phase 2 (~23–28 h of work, parallelizable across worker agents in clean file-disjoint lanes).
- Session 2: Phase 3 (~7–9 h, plus empirical fail-closed verification of plugin + hook).
- Session 3 (post-approval): Phase 4 protected-file edit (~2 h).
Total Phases 1–3 ≈ 30–37 h. Within the stated envelope.

================================================================
WHAT THIS ARCHITECTURE DOES NOT SOLVE
================================================================
1. Browser arbitrary-JS execution (browser_evaluate, browser_run_code_unsafe, Claude-in-Chrome javascript_tool). These can drive the Gmail/Telegram web UI to send and cannot be reliably intent-scanned — a send can be obfuscated in JS. The only real control is DENYLISTING them, which Phase 1 does. If ever re-allowed, the engine does not cover them.
2. OpenCode when the plugin is unloaded or its `plugin` key is dropped from opencode.json. OC enforcement is real only while the plugin loads; in the degraded state the startup hook warns loudly but cannot block — only the Option-3 audit catches violations after the fact.
3. Execution surfaces outside the five hooked entry points — a cron job, systemd unit, or background script that imports the Gmail service directly and routes through none of CC Bash / OC tool / telegram gw / headless spawn / relay. The engine enforces only where wired in.
4. WaveTerm / raw desktop terminal — a human or process typing `python` at an unhooked shell is outside Claude Code's hook context. Commander/human territory; accepted, not engineered against.
5. Regex / string brittleness — Bash-command scanning is evadable by aliasing, base64-piping to `python -c`, renaming a script, or dynamic call construction. Pattern matching is the floor, not the ceiling. The protected-path and recipient checks (which key on resolved targets, not just strings) plus the Option-3 audit are the compensating layers.

BACKSTOP: The PostToolUse audit logger (built in Phase 1) plus a periodic sweep over logs/policy_audit.jsonl and Gmail Sent / Telegram outbound is the only net under the structurally-uncoverable surfaces above. It is not the primary gate — it is the net, and it is mandatory, not optional.

================================================================
COMMANDER DECISIONS REQUIRED
================================================================
1. DENYLIST browser arbitrary-JS tools on the client-send path (browser_evaluate, browser_run_code_unsafe, Claude-in-Chrome javascript_tool). The only decision with a real cost — it removes browser-driven send/compose convenience. There is no policy-gate alternative. RECOMMEND APPROVE: the convenience is rarely used; the gap is otherwise uncloseable.
2. AMEND SO-2026-06-08 to add wing_policy.py, rules_registry.py, .claude/settings.json, and opencode.json to the protected-file set (6 → 10 artifacts), with the hook denying edits to itself, settings.json, and the registry. Without this the enforcement layer is self-deletable and the whole build is theater. (Note: building the engine in Phase 1 carries zero risk to the existing six files; the SO amendment is the separate governance act.)
3. AUTHORIZE the Phase 4 relay-file edits (relay_send.py, wing_relay.py). Protected files; one-line guard each; defense-in-depth only — Phases 1–3 already cover relay indirectly.
4. DIRECT that core/policy/rules_registry.py become canonical, with the 4 CLAUDE.md-family files referencing rather than restating rules. This rewrites governance documents and is what actually ends the wording drift.
5. ACKNOWLEDGE the OpenCode premise correction — OC can enforce mechanically via a plugin, contrary to the "advisory-only" framing; Phase 3 builds that plugin rather than settling for a startup notice.

Holding at WF-17 posture: no code is written until you approve this plan. Standing by for your decisions on the five items above.

— V. Hale, VCS

---

## ADVERSARIAL VALIDATION NOTES

Verdict: option4_with_caveats

Failure modes identified:
1. SELF-DISABLEMENT (highest risk): wing_policy.py and .claude/settings.json hook config are both reachable via the allow-listed Bash(*)/Edit(*) — any agent can delete the hook or neuter the registry in one line. Enforcement an agent can edit away is not enforcement. They MUST join the 6-file protected set and the hook must deny edits to itself + settings.json + the registry.
2. FAIL-OPEN: if wing_policy.py throws, is missing, or times out and the hook treats non-zero/empty as pass-through, a traceback becomes an open gate. Hook must fail CLOSED (deny on any policy error).
3. MCP-ONLY MATCHERS: if the PreToolUse matcher only catches MCP tool names, it duplicates the existing deny list and leaves the Bash send path (line 187) and browser path fully open — the engine looks deployed but enforces nothing new.
4. BROWSER ARBITRARY-JS EVASION: browser_evaluate, browser_run_code_unsafe, and Claude-in-Chrome javascript_tool (all allow-listed) can drive the Gmail/Telegram web UI to send. Arbitrary JS cannot be reliably scanned for intent — a send can be obfuscated. Defeats both Bash-scanning and any Python-script scanner.
5. OPENCODE PLUGIN UNLOADED: OC enforcement is real (permission.ask/tool.execute.before exist) but ABSENT today (no plugin registered). If the plugin file is missing, fails to load, or opencode.json drops the plugin key, OC silently reverts to advisory with no fail-closed signal.
6. HEADLESS CHILD CONFIG DRIFT: a spawned claude -p inherits PROJECT settings (good — proven), but if a spawn passes skip/bypass flags or points at a different settings dir, the child's own Bash drops escape. Spawn wrapper must guarantee the hook-bearing project settings are loaded and not stripped.
7. REGEX BRITTLENESS: command-string scanning for .send( / send_*.py is bypassable by aliasing, base64-piping to python -c, renaming a script, or constructing the call dynamically. Pattern matching is necessary but not sufficient.
8. CONFIG-DRIFT RE-ALLOW: settings.local.json already re-allows mcp__claude_ai_Gmail__gmail_create_draft (=johnloucks3), violating the no-drafts-to-johnloucks3 SO — proof that allow-lists drift back open over time even with policy intent.

Surfaces Option 4 cannot cover:
1. Browser arbitrary-JS execution (browser_evaluate, browser_run_code_unsafe, Claude-in-Chrome javascript_tool) — can send via the Gmail/Telegram web UI and cannot be reliably intent-scanned. Only real control is DENYLISTING these tools, not policy-gating them.
2. OpenCode when the policy plugin is unloaded/unregistered — structurally advisory until and unless the plugin is present and loads; no mechanical backstop if it's absent.
3. Any execution surface outside the five named entry points — a cron job, systemd unit, or background script that imports the Gmail service directly and isn't routed through a hooked process (CC Bash, OC tool, telegram gw, headless spawn) sees no policy. The engine only enforces where it is wired in.
4. WaveTerm / desktop terminal — a human or process typing python at a raw shell outside Claude Code's hook context is unhooked (though this is human-Commander territory, not autonomous agent risk).
5. Voice-transcribed /approve in the telegram gateway — the COMMANDER_ID whitelist is the only guard; a transcribed approval still publishes a client draft unless handle_approve itself calls wing_policy (which is why that specific call site is non-negotiable).

Mandatory constraints for success:
1. PreToolUse hook must live in PROJECT settings (.claude/settings.json), not local/user — so it is inherited by all headless children. EMPIRICALLY VERIFIED: child claude -p was blocked by a project PreToolUse hook under bypassPermissions+skipDangerousModePermissionPrompt. This constraint is met by construction but must not be moved to a child-overridable location.
2. Matchers must scan Bash command STRINGS (.send(, send_*.py, relay_send, claude -p, telegram sendMessage) AND browser MCP navigate/click/evaluate TARGETS (mail.google.com, web.telegram.org). MCP-tool-name matching alone is decorative — it only re-covers what the deny list already covers.
3. wing_policy.py MUST fail CLOSED: any exception, missing file, or timeout = DENY. A traceback must never equal an open gate.
4. wing_policy.py + the rule registry + .claude/settings.json hook block MUST be added to the protected-files set (joining the existing 6), and the hook must DENY edits to itself, settings.json, and the registry. Enforcement an agent can Edit/Bash away is not enforcement.
5. Browser arbitrary-JS tools (browser_evaluate, browser_run_code_unsafe, Claude-in-Chrome javascript_tool) on the CLIENT-send path must be DENYLISTED, not policy-gated — they cannot be intent-scanned.
6. OpenCode enforcement is real but ABSENT: a .opencode plugin implementing permission.ask + tool.execute.before, registered via the plugin key in opencode.json, shelling out to wing_policy.py, MUST be written and load-verified — or OC stays advisory. (This contradicts the task's CRITICAL CONTEXT claim that OC has no hook equivalent; side with the verified inventory finding.)
7. telegram gw must import wing_policy and call it at THREE sites: handle_approve (before drafts().send line 1125), _drain_relay_queue (before call_claude_engine), and /agent + /ask shell-outs — no edit to protected relay_send.py/wing_relay.py required.
8. Combine with Option 3 (post-hoc audit) as the BACKSTOP for the uncoverable surfaces (browser JS, OC-when-plugin-unloaded, unhooked cron/systemd paths). Option 3 is not the primary gate but is the only net under structurally-uncoverable execution.
9. The code RULE REGISTRY must become the single source of truth; the 4 CLAUDE.md files reference it rather than restating rules — this is what actually kills the 3-file wording drift root cause. Without this, Option 4 enforces but the drift persists.
10. Headless spawn wrapper must guarantee children load the hook-bearing project settings and must NOT pass flags that strip PreToolUse.

---

## RULE CATALOG SUMMARY

Total hard rules identified: 22
Rules with NO enforcement today: 19
Highest risk surface: Raw-Python / headless-spawn / OpenCode email-send path: the MCP deny_list in /home/john/.claude/settings.json blocks only Claude Code's MCP send tool names, but core/email/thunderbird_gmail.py exposes direct service.users().messages().send() functions (gmail_send_from_wing, gmail_send_email, send_client_email) callable from raw Python, OpenCode, and headless spawns with zero gate — so the single most critical rule (WF-17 absolute client-send prohibition, RULE-CLIENT-SEND-001) plus the d2mconcierge recipient allow-list (RULE-CONCIERGE-SEND-LIST-018) are wide open on exactly the surfaces the task flags as highest-violation-risk. This gap is doctrinally widened by 'Weapons Free' (RULE-WEAPONS-FREE-GATES-019), which suspends the only live code gate (the pre-commit hook) and leaves the three inviolable Commander gates protected by advisory prose alone.

TOP CRITICAL RULES (advisory only today):
  [RULE-CLIENT-SEND-001] The Wing/AI may NEVER execute a send to any client address under any circumstance; Commander is the sole executor of all client communications (WF-17 is content approval, not execution delegation). — governs: email_send — platforms: Claude Code, OpenCode, relay, Telegram bots, Grace, Signal, headless
  [RULE-PROTECTED-FILES-005] Six email-scanner/relay files (run_commander_directive_sweep.py, dispatch_and_email.py, email_task_ingest.py, thunderbird_commander_inbox.py, relay_send.py, wing_relay.py) MUST NOT be modified autonomously by any non-Claude-Code agent; relay change requests to Claude Code and wait for explicit proceed. — governs: other — platforms: Claude Code, OpenCode, relay, headless
  [RULE-PIPELINE-NEGSPACE-006] Negative-Space Rule: if a fact is not confirmed in a primary source (dossier, portal, TESS), it does not appear in a client email; 'likely/pending/probably/our understanding' are banned in client copy. — governs: draft_create — platforms: Claude Code, OpenCode, headless
  [RULE-PIPELINE-FINSOURCE-007] Financial Hard-Source Rule: dollar amounts, balances, and FPDs in client emails must trace to portal/TESS/dossier (never a memo); portal is authoritative on conflict; discrepancy resolved or flagged before WF-17. — governs: draft_create — platforms: Claude Code, OpenCode, headless
  [RULE-DATA-SUBSTITUTION-009] NEVER give one client's number/data when the Commander asked about a different client; say 'I don't have it, pulling it' rather than substituting the nearest figure. — governs: other — platforms: Claude Code, OpenCode, Telegram bots, Signal, headless
  [RULE-CONCIERGE-SEND-LIST-018] Direct sends from d2mconcierge without WF-17 are limited to a fixed allow-list (johnloucks3, susanna.loucks, bryanajarboe, rwestbrook3, iamheer); WF-17 survives for ALL other client addresses. — governs: email_send — platforms: Claude Code, OpenCode, headless
  [RULE-WEAPONS-FREE-GATES-019] Even under a 'Weapons Free' declaration (all production gates suspended), the three Commander gates remain inviolable: client send (WF-17), financial commitment, strategic direction; plus the 6 protected files unchanged. — governs: other — platforms: Claude Code, OpenCode, Telegram bots, Signal, headless

---

## ARCHITECTURE DESIGN

The advisor confirms my read. Writing the design now.

## CORE POLICY ENGINE

**Location:** `core/policy/wing_policy.py` — the single mechanical enforcement point. Imported, never copied. All four CLAUDE.md/AGENTS.md files *reference* this module; none restate rules (this kills the 3-file wording drift root cause).

**Rule registry — single source of truth:** `core/policy/rules_registry.py` (Python dataclasses, not JSON). Python over JSON because rules need executable predicates (e.g. "URL host in {mail.google.com, web.telegram.org}"), and a code module joins the protected-files set naturally and is import-validated at load.

```python
# core/policy/rules_registry.py
from dataclasses import dataclass
from enum import Enum
from typing import Callable

class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    GATE = "gate"          # blocked pending Commander; not a silent allow

class ActionType(Enum):
    CLIENT_SEND = "client_send"
    DRAFT_CREATE = "draft_create"
    FINANCIAL_COMMIT = "financial_commit"
    PROTECTED_FILE_EDIT = "protected_file_edit"
    SELF_DISABLE = "self_disable"          # touches the engine itself
    BROWSER_NAV = "browser_nav"
    BROWSER_ARBITRARY_JS = "browser_arbitrary_js"
    RELAY_DISPATCH = "relay_dispatch"
    PII_EGRESS = "pii_egress"              # to OC/DeepSeek
    SHELL_EXEC = "shell_exec"

@dataclass(frozen=True)
class Rule:
    id: str                    # "WF17-CLIENT-SEND", "SELF-DISABLE", "DRAFT-JL3"
    action_type: ActionType
    platforms: frozenset       # {"claude_code","opencode","telegram","headless","relay"}
    decision: Decision         # default decision when predicate matches
    predicate: Callable[[dict], bool]   # (action_ctx) -> True if rule applies
    message: str               # shown to Commander on block
    so_ref: str                # "SO_WF17_CLIENTSEND_PROHIBITION_20260530.md"

REGISTRY: tuple[Rule, ...] = (...)   # ordered; DENY rules evaluated before GATE
```

Rules are organized **by action_type primarily, with a platform filter** — one rule can bind multiple platforms. The matcher (hook side) maps a raw tool invocation to an `action_ctx` dict; the registry decides. This separates *detection* (platform-specific, in each integration) from *policy* (central, here).

**Interface:**

```python
# core/policy/wing_policy.py
PROTECTED_PATHS = frozenset({
  # existing 6
  "OpsCenter/relay_send.py", "core/relay/wing_relay.py",
  "OpsCenter/run_commander_directive_sweep.py", "OpsCenter/dispatch_and_email.py",
  "OpsCenter/email_task_ingest.py", "core/email/thunderbird_commander_inbox.py",
  # NEW — the engine cannot be edited away
  "core/policy/wing_policy.py", "core/policy/rules_registry.py",
  ".claude/settings.json", "opencode.json",
})

@dataclass
class PolicyResult:
    allowed: bool
    decision: Decision
    rule_id: str | None
    message: str
    require_gate: bool          # True => block + surface to Commander

def check(action_ctx: dict) -> PolicyResult:
    """
    action_ctx keys (subset per platform):
      tool: str                # "Bash" | "Edit" | "browser_navigate" | mcp name
      command: str | None      # Bash command string
      file_path: str | None    # Edit/Write target
      url: str | None          # browser navigate/click target
      recipient: str | None    # email/telegram target
      payload: str | None      # message/draft body (for PII scan)
      platform: str
    Returns PolicyResult. MUST NOT raise — internal try/except wraps everything
    and returns deny on any failure.
    """

# Convenience wrappers used at named call sites:
def check_relay_action(target, message) -> PolicyResult: ...
def check_telegram_send(chat_id, text, bot) -> PolicyResult: ...
def check_draft_send(draft_id, recipient) -> PolicyResult: ...
def check_spawn(prompt, model) -> PolicyResult: ...
```

**Fail-closed contract (the load-bearing detail):** `check()` itself contains a top-level `try/except Exception` that returns `PolicyResult(allowed=False, decision=DENY, rule_id="POLICY-ERROR", ...)`. But fail-closed is only real if the *caller's* block signal is correct — see the hook section. Missing import, missing registry, timeout, or traceback inside `check()` → DENY.

**Self-disablement guard lives inside `check()`, not in the matcher.** A single `PROTECTED_PATHS` predicate inspects `command` (for `rm`/`mv`/`sed`/`>`/`tee` targeting a protected path), `file_path` (Edit/Write), and any path argument — so switching from Edit to `Bash(sed ...)` to `Write` cannot evade it. This is why the guard is centralized.

## CLAUDE CODE INTEGRATION (PreToolUse)

**Hook script:** `hooks/pretooluse_policy.py` (Python, matching the existing `hooks/post_tool_dossier.py` pattern). Registered in **`.claude/settings.json`** (PROJECT, not local/user) so it is inherited by every headless `claude -p` child — empirically verified that a project PreToolUse hook blocks children even under `bypassPermissions`.

```json
"PreToolUse": [
  { "matcher": "Bash",            "hooks":[{"type":"command","command":"python3 /home/john/Thunderbird/hooks/pretooluse_policy.py"}] },
  { "matcher": "Edit|Write|MultiEdit", "hooks":[{...same...}] },
  { "matcher": "mcp__playwright__browser_navigate|mcp__playwright__browser_click|mcp__playwright__browser_evaluate|mcp__playwright__browser_run_code_unsafe|mcp__playwright__browser_fill_form|mcp__playwright__browser_type", "hooks":[{...}] },
  { "matcher": "mcp__claude_ai_Gmail__gmail_create_draft|mcp__dreams2memories__gmail_create_draft|mcp__dreams2memories__draft_client_email", "hooks":[{...}] }
]
```

**Matcher catches the TOOL; the hook scans the PAYLOAD.** This is the explicit anti-decorative requirement. The hook reads the tool invocation JSON from stdin, builds `action_ctx`, and calls `wing_policy.check()`:
- `Bash` → scan `command` string for `.send(`, `send_*.py`, `relay_send`, `claude -p ... --dangerously-skip`, `telegram ... sendMessage`, `python -c`, base64-pipe patterns, and protected-path mutations.
- `Edit|Write` → scan `file_path` against `PROTECTED_PATHS` (covers self-disablement).
- `browser_navigate|click|fill_form|type` → scan `url`/target for `mail.google.com`, `web.telegram.org` (the send-via-web-UI path).
- Gmail/draft MCP → scan recipient (johnloucks3 draft → GATE per SO; client recipient → DENY).

**Block mechanism (fail-closed correctness):** the hook emits the explicit deny signal, **not** a bare non-zero exit. PreToolUse blocks via `exit code 2` (stderr → model) OR JSON `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}` on stdout with exit 0. A generic traceback exiting 1 is treated as a *non-blocking error* — i.e. fail-OPEN — which is exactly what's forbidden. Therefore:

```python
# hooks/pretooluse_policy.py  (pseudocode)
def main():
    try:
        ctx = build_ctx(json.load(sys.stdin))
        result = wing_policy.check(ctx)
    except Exception as e:                     # import error, bad stdin, anything
        emit_deny(f"POLICY-ERROR fail-closed: {e}")  # -> deny JSON + exit 0
        return
    if result.allowed:
        sys.exit(0)
    emit_deny(result.message)   # writes deny JSON, exit 0 (or exit 2 + stderr)
```

The wrapper converts **every** exception/timeout/missing-import into the deny signal. A subprocess timeout guard wraps the `check()` call; timeout → deny.

**On violation:** block the tool + return `result.message` (includes `rule_id` + `so_ref`) to the model so it self-corrects, AND for `require_gate=True` actions append the standard "Surfacing to Commander — held at WF-17 gate" line. The PostToolUse audit hook (Option 3 backstop) logs every check result regardless of decision to `logs/policy_audit.jsonl`.

**Browser arbitrary-JS:** `browser_evaluate`, `browser_run_code_unsafe`, and any Claude-in-Chrome `javascript_tool` on the client-send path are **DENYLISTED in settings.json permissions** (moved to `deny`), not policy-gated — arbitrary JS cannot be reliably intent-scanned. The matcher above is a second layer, but the permission deny is the real control.

## OPENCODE INTEGRATION

**Overriding the task premise.** The task's platform constraint says OpenCode has "NO hook equivalent." Per the validation findings and my own inventory check (`.opencode/` exists with `node_modules`; `opencode.json` exists), this is wrong — **OC has real enforcement via `permission.ask` + `tool.execute.before`.** I side with the verified inventory. The startup-hook-only answer would be the decorative version.

**Primary enforcement (NEW build):** `.opencode/plugin/wing_policy_plugin.js` implementing:
- `tool.execute.before(input, output)` — for every tool call, shell out to `python3 core/policy/wing_policy.py --stdin` (a thin CLI entry on the module), pass the action_ctx as JSON, parse the `PolicyResult`. On DENY/GATE → throw / reject to abort the tool. **Fail-closed:** if the subprocess errors, times out, or returns non-JSON → abort (deny).
- `permission.ask` — gate interactive permission requests through the same check.

Registered via the **`plugin` key in `opencode.json`** (joins protected set so the key can't be silently dropped). If the plugin file is missing or fails to load, OC has no mechanical backstop — that is the honest residual (see WHAT THIS DOES NOT SOLVE).

**Secondary / load-verification layer:** `OpsCenter/state_bridge/session_startup_hook.py` (already runs every OC session, already fail-SOFT/exits 0 by design — I do not bolt fail-closed onto it). Its added job is narrow: verify the plugin is registered in `opencode.json` and loaded; if absent, emit a loud `[POLICY] PLUGIN NOT LOADED — OC IS ADVISORY ONLY` warning into the session briefing and to `logs/policy_audit.jsonl`. It does **not** gate individual actions — per-action fail-closed lives in `tool.execute.before`.

**AGENTS.md reference:** AGENTS.md states (referencing, not restating rules) "All policy is enforced by `core/policy/wing_policy.py` via the `.opencode` plugin. If the startup briefing shows PLUGIN NOT LOADED, you are advisory-only — do not send to clients, do not touch protected files, surface to Commander." This keeps OC aware even in the degraded state.

## RELAY INTEGRATION (Phase 2 — requires Commander approval)

`relay_send.py` and `wing_relay.py` are protected files. They are not modified in Phase 1. **Proposed Phase 2 change (Claude Code executes, Commander approves):**

```python
# top of OpsCenter/relay_send.py and core/relay/wing_relay.py
from core.policy.wing_policy import check_relay_action
# inside the dispatch function, before any send:
res = check_relay_action(target, message)
if not res.allowed:
    raise PolicyViolation(res.message)   # fail-closed; relay refuses
```

This is a one-line import + guard call — it does not change relay logic. It catches PII egress to OC/DeepSeek and relay-borne client-send attempts at the relay boundary itself. **Documented as a discrete Commander-approval item; not built in Phase 1.** Until approved, relay is covered only indirectly (Bash-string scanning of `relay_send` invocations by the CC hook) plus the Option-3 audit.

## TELEGRAM GW INTEGRATION

`thunderbird_telegram_gw.py` is not protected — direct import + guard. **Three non-negotiable call sites** (line numbers from current file):

1. **`handle_approve` (before `svc.users().drafts().send(...)` at line 1125):**
```python
res = check_draft_send(draft_id, recipient)
if not res.allowed:
    tg_send(TOKEN_D2MC2C, COMMANDER_ID, f"BLOCKED: {res.message}")
    return
```
This is the site that stops a voice-transcribed `/approve` from publishing a client draft — the COMMANDER_ID whitelist alone is insufficient because a transcribed approval still reaches here.

2. **`_drain_relay_queue` (line 1837, before `call_claude_engine` at 1870):** `check_relay_action` on the queued payload before it becomes a Claude dispatch — stops PII egress and unvetted relay content.

3. **`/agent` and `/ask` shell-outs (the `call_claude_engine` paths ~1676/1685/1695):** `check_spawn(prompt, model)` before dispatch — catches client-send instructions injected via these commands.

No edit to protected `relay_send.py`/`wing_relay.py` is required for any of this — the guards live in the gateway. A general `check_telegram_send()` also wraps the raw `sendMessage` at line 438 for the client-facing bots, leaving Commander-only D2MC2C traffic unaffected.

## HEADLESS SPAWN INTEGRATION

`core/ai_infra/thunderbird_headless_spawn.py`, function `spawn_headless_claude` (line 143). Two responsibilities:

1. **Pre-spawn check:** `check_spawn(prompt, model)` scans the prompt for client-send / financial-commit / protected-file instructions before the child launches. DENY → refuse to spawn, log, return error.

2. **Guarantee the hook reaches the child** (the config-drift failure mode): the wrapper MUST launch the child against the hook-bearing PROJECT settings dir and MUST NOT pass any flag that strips PreToolUse. Add an assertion that `--settings`/working dir resolves to `/home/john/Thunderbird/.claude/settings.json` and reject `extra_args` containing skip/bypass-of-hooks flags. (`bypassPermissions` is fine — empirically the project hook still fired under it — but a different settings dir or an explicit hook-disable flag is rejected.)

3. **Inject policy summary into the child prompt:** prepend a short, registry-generated banner — `wing_policy.summary_for_prompt()` returns the current DENY/GATE rule list (one source of truth) so the child *knows* the rules in addition to being hook-enforced. Defense in depth: the child knows (prompt) and cannot bypass (inherited PreToolUse hook).

## SKILL GATES

Dedicated skills under `~/.claude/skills/` are the **ergonomic, opt-in front door** for high-risk actions — they run the policy check as the first step of invocation, so the *intended* path is always vetted. They are NOT the security boundary (a skill can be bypassed by calling the API directly — the PreToolUse hook remains the real gate).

- `~/.claude/skills/send-telegram/SKILL.md` — runs `check_telegram_send()` before any `sendMessage`; refuses client-bot sends.
- `~/.claude/skills/client-draft/SKILL.md` — enforces draft routing: client → d2mconcierge + `THUNDERBIRD-Commander-Review` label; johnloucks3 draft → GATE (Commander explicit OK); internal → direct send allowed.
- `~/.claude/skills/spawn-headless/SKILL.md` — wraps `spawn_headless_claude` with the pre-spawn check + settings-dir assertion.

Skills make compliance the path of least resistance; the hook makes non-compliance impossible on hooked surfaces. Both, not either.

## WHAT THIS DOES NOT SOLVE

Faithful to the validation `cannot_cover` list:

1. **Browser arbitrary-JS execution** (`browser_evaluate`, `browser_run_code_unsafe`, Claude-in-Chrome `javascript_tool`) — can drive the Gmail/Telegram web UI to send and cannot be reliably intent-scanned (a send can be obfuscated in JS). The *only* real control is DENYLISTING these tools on the client-send path, which the design does. If they are ever re-allowed, this engine does not cover them.
2. **OpenCode when the plugin is unloaded/unregistered** — OC enforcement is real *only while the plugin loads*. If `.opencode/plugin/wing_policy_plugin.js` is missing, fails to load, or the `plugin` key is dropped from `opencode.json`, OC reverts to structurally advisory. The startup hook emits a loud warning but is fail-soft and cannot block actions. No mechanical backstop in that state except the Option-3 post-hoc audit.
3. **Execution surfaces outside the five hooked entry points** — a cron job, systemd unit, or background script that imports the Gmail service directly and is not routed through CC Bash / OC tool / telegram gw / headless spawn / relay sees no policy. The engine enforces only where wired in. Mitigation: Option-3 audit scans `logs/policy_audit.jsonl` and Gmail Sent for un-vetted sends after the fact.
4. **WaveTerm / raw desktop terminal** — a human or process typing `python` at an unhooked shell is outside Claude Code's hook context. This is Commander/human territory, not autonomous-agent risk, and is accepted.
5. **Voice-transcribed `/approve`** — guarded specifically by the `handle_approve` call site (#1 above). If that one call is ever removed, the COMMANDER_ID whitelist is the only guard and a transcribed approval would publish a client draft. That call site is therefore treated as non-negotiable and `handle_approve`/its file should be considered for the protected set in a later phase.
6. **Regex/string brittleness** — Bash-command scanning is bypassable by aliasing, base64-pipe to `python -c`, renaming a script, or dynamic call construction. Pattern matching is necessary but not sufficient; the protected-path and recipient checks (which key on resolved targets, not just strings) plus the Option-3 audit are the compensating layers.

**Backstop (Option 3):** PostToolUse audit hook + a periodic sweep over `logs/policy_audit.jsonl` and Gmail Sent / Telegram outbound is the *only* net under the structurally-uncoverable surfaces (browser JS, OC-when-plugin-unloaded, unhooked cron/systemd). It is not the primary gate; it is the net.

## ESTIMATED BUILD TIME PER COMPONENT

| Component | Est. | Notes |
|---|---|---|
| `core/policy/rules_registry.py` (dataclasses + initial rule set) | 4–6 h | Encoding existing SOs as predicates is the real work |
| `core/policy/wing_policy.py` (`check()` + wrappers + fail-closed + self-disable guard + CLI entry) | 4–5 h | |
| `hooks/pretooluse_policy.py` + settings.json registration + deny-signal correctness | 3–4 h | Verifying exit-2 vs JSON-deny block mechanism empirically is mandatory |
| Browser-JS denylist (settings.json permissions move) | 0.5 h | |
| Telegram GW — 3 call sites + `sendMessage` wrap | 2–3 h | Not protected; direct edit |
| Headless spawn — pre-check + settings-dir assertion + prompt banner | 2 h | |
| `.opencode/plugin/wing_policy_plugin.js` (`tool.execute.before` + `permission.ask`) + opencode.json registration + load-verify in startup hook | 5–7 h | JS plugin + Python shell-out; the highest-uncertainty piece |
| Skill gates (3 SKILL.md) | 2 h | Ergonomic layer |
| Option-3 audit (PostToolUse logger + sweep script) | 3–4 h | Backstop |
| AGENTS.md / 4×CLAUDE.md — replace restated rules with registry reference | 2 h | This is what actually kills wording drift |
| Add engine files to protected set + protect settings.json/opencode.json/registry via the hook | 1 h | |
| **Phase 1 total** | **~30–40 h** | |
| **Phase 2 — Relay import (Commander approval + CC execution)** | **2 h** | Separate, gated |

**Build order:** registry → wing_policy → CC hook (prove block mechanism) → browser denylist → telegram → spawn → OC plugin → skills → audit → docs/protection. The CC hook and OC plugin are the two pieces where fail-closed correctness must be empirically verified before declaring deployed; everything else rides on a working `check()`.

---

## SYNTHESIS

The advisor confirms my read and sharpens the priority ordering. Let me write the synthesis directly as my final response.

## COMPLIANCE ARCHITECTURE AUDIT — SYNTHESIS FOR THE COMMANDER
*Thunderbird Wing, Dreams2Memories Travel, LLC · Chief of Staff synthesis · 2026-06-18*

**Bottom line up front:** 19 of 22 SO rules have NO mechanical enforcement — they live as advisory prose in CLAUDE.md, AGENTS.md, and persona files, and the model is trusted to obey. The one real control (the MCP deny list) governs a single tool path and is bypassable by Bash, raw Python, browser automation, or any headless child. Option 4 (PreToolUse/plugin policy engine) is the right architecture, confirmed with caveats — but the caveats are non-negotiable preconditions, not nice-to-haves. The most important single truth in this audit: **enforcement an agent can Edit or Bash away is not enforcement.** Get that wrong and the whole build is theater.

---

## TOP ENFORCEMENT GAPS (priority ordered)

Ranked by: reaches a client/external human × recurs across platforms × cannot be closed by a simple deny-list.

**1. Raw Bash/Python Gmail `.send()` path — the single most dangerous gap.**
- Rules: RULE-CLIENT-SEND-001 (the absolute WF-17 client-send prohibition), RULE-CONCIERGE-SEND-LIST-018, plus financial/signature/Pipeline Rules 1/4/5 on the send path.
- Platforms: Claude Code, OpenCode, headless spawns — every surface that can run Python.
- The mechanism: `scripts/hale_send_direct.py` line 187 and ~15 sibling `send_*.py` scripts call `service.users().messages().send()` directly. Reachable via `Bash(*)`, which is allow-listed under `bypassPermissions`. The MCP deny list does not touch this path — it is decorative against any agent that drops to Bash.
- Attachment point: PreToolUse Bash hook scanning command strings for `.send(`, `messages().send`, `drafts().send`, `send_*.py`; plus a shared `send_guard.py` that checks recipient against the internal allowlist (johnloucks3, susanna.loucks) and refuses client addresses absent a logged Commander waiver.

**2. Browser-automation send — the path that survives the obvious fix.**
- Rules: RULE-CLIENT-SEND-001, Telegram channel discipline, all send-gates.
- Platforms: Claude Code (playwright MCP + Claude-in-Chrome, both allow-listed in settings.local.json).
- The mechanism: `browser_evaluate`, `browser_run_code_unsafe`, and Claude-in-Chrome `javascript_tool` can drive the Gmail/Telegram web UI to click Send. This defeats BOTH the MCP deny list AND any Bash/Python script scanner.
- Attachment point: **DENYLIST these tools on the client-send path — do not policy-gate them.** Arbitrary in-page JS cannot be reliably intent-scanned; a send can be obfuscated. This is the one gap where pattern matching is structurally insufficient. (Carries a real cost — see Key Decisions.)

**3. Headless spawn wrapper — the highest-leverage single attachment point.**
- Rules: all 3 Commander gates, RULE-PROTECTED-FILES-005, RULE-CLIENT-SEND-001, RULE-HEADLESS-SPAWN-012.
- Platforms: every bot/persona surface — Telegram `/agent`, Signal, OpenCode dispatch all funnel through `core/ai_infra/thunderbird_headless_spawn.py`.
- The mechanism: `spawn_headless_claude()` verifies only infrastructure (OAuth, daemons). It injects ZERO SO context and hands the full default MCP config. CLAUDE.md and the persona @-refs load only in INTERACTIVE sessions — headless `claude -p` children do not auto-load them, so spawned agents have full Gmail/Drive/TESS reach with no enforced knowledge of any gate.
- Attachment point: at the wrapper — (a) inject a mandatory gates+protected-files system preamble on EVERY spawn (not caller-optional), (b) default to a hardened MCP config that strips client-send and protected-file-write tools unless explicitly justified, (c) guarantee children load the hook-bearing PROJECT settings and never pass flags that strip PreToolUse.

**4. OpenCode policy plugin — full capability, zero deployment.**
- Rules: RULE-CLIENT-SEND-001, RULE-DRAFT-J3-002, RULE-PII-FENCE-011, T2-AAR-no-email, RULE-CREATIVE-CHAIN-015.
- Platforms: OpenCode.
- **Correction to the task premise:** OpenCode is NOT missing a hook equivalent. The plugin SDK exposes `permission.ask` (returns `deny`/`ask`/`allow` — a genuine content-aware deny gate) and `tool.execute.before` (mutates args). The capability is full. The deployment is zero — no plugin is registered (`no plugin key` in either opencode.json; no `.ts`/`.js` file outside node_modules). Until `.opencode/plugin/d2m_policy.ts` is written, registered, AND load-verified, OC reverts silently to advisory with no fail-closed signal.
- Attachment point: author and register the plugin; it shells out to the shared `wing_policy.py`. This sits ABOVE the protected relay files — no protected-file edit required.

**5. Telegram `/approve` — WF-17 enforced only as "Commander pressed the button."**
- Rules: RULE-CLIENT-SEND-001, creative-chain/Pipeline content rules, stationery SO.
- Platforms: Telegram gateway (relay/messaging layer).
- The mechanism: `handle_approve()` (L1068-1134) publishes a client-facing Gmail draft with NO recipient check, NO chain-completion check, NO confidence/Harlan/stationery verification. Only guard is the COMMANDER_ID whitelist. The legacy fallback (L1125) does a raw `drafts().send()` with no stationery. Voice-transcribed approvals route through the same handler — a transcribed "/approve" ships the draft.
- Attachment point: import `wing_policy` and call it at the TOP of `handle_approve()` before any `drafts().send()` — verify THUNDERBIRD-Commander-Review label + chain-completion marker + banned-phrase/dollar-figure scan; block and warn rather than silently send. Gateway is NOT protected — this edit is permitted.

**6. Relay-queue drain — unauthenticated injection into the Claude engine.**
- Rules: RULE-CLIENT-SEND-001, RULE-PROTECTED-FILES-005.
- Platforms: relay/messaging layer (most autonomous, non-human injection point).
- The mechanism: `_drain_relay_queue()` (L1837-1900) reads any `to==CC, status==pending` entry from `relay_queue.jsonl` and feeds it to `call_claude_engine()`. `relay_send.enqueue()` writes these with NO sender verification — the COMMANDER_ID check applies only to live Telegram `@CC:` directives, not to file-queue items. OpenCode or any process that can append to the queue can drive the Claude engine.
- Attachment point: policy check inside `_drain_relay_queue()` before `call_claude_engine()` — screen relayed content for SO-protected intents (client-send, protected-file edits) and refuse/flag.

**7. Signal gateway — LIVE, no sender allowlist, full-tool spawn.**
- Rules: RULE-CLIENT-SEND-001, 3 Commander gates.
- Platforms: persona/bot layer (Signal C2 — confirmed running, 3 services + Docker up).
- The mechanism: `thunderbird_signal_gw.py handle()` dispatches ANY inbound message to a tool-capable headless Sonnet and replies to whoever sent it. There is NO COMMANDER_ID-equivalent check — the only mitigation is the 127.0.0.1 network binding. A number re-link, group add, or second registered number opens a tool-capable Hale to an unauthorized party.
- Attachment point: add an explicit `if sender != COMMANDER: log+return` allowlist mirroring the Telegram gate — single highest-leverage Signal fix; plus the hardened spawn-wrapper MCP config (gap 3).

**8. Telegram `/agent` — detached full-MCP spawn gated by identity only.**
- Rules: 3 Commander gates, RULE-CLIENT-SEND-001, RULE-PROTECTED-FILES-005.
- Platforms: persona/bot layer.
- The mechanism: `/agent` Popens a detached headless Hale with full MCP tools and `--dangerously-skip-permissions`. The COMMANDER_ID gate protects WHO spawns, not WHAT the spawned agent may do. A Commander request phrased "reply to the client" lets the headless agent execute a client send directly.
- Attachment point: restricted MCP config + hard system-prompt preamble at `telegram_async_agent.py` spawn (resolved by fixing gap 3 at the wrapper).

**9. Self-disablement — the gap that voids all the others.**
- Rules: meta — protects RULE-PROTECTED-FILES-005 and the entire enforcement layer.
- Platforms: all.
- The mechanism: `wing_policy.py`, the `.claude/settings.json` hook block, and the rule registry are all reachable via allow-listed `Bash(*)`/`Edit(*)`. Any agent can delete the hook or neuter the registry in one line.
- Attachment point: these three artifacts MUST join the 6-file protected set, and the hook MUST deny edits to itself, settings.json, and the registry. The engine MUST fail CLOSED — any exception, missing file, or timeout = DENY.

**10. Config-drift re-allow of `gmail_create_draft` (johnloucks3).**
- Rules: RULE-DRAFT-J3-002 (no silent drafts to johnloucks3).
- Platforms: Claude Code.
- The mechanism: global settings.json DENIES cloud `gmail_create_draft`; settings.local.json ALLOWS it — local wins. Cloud Gmail MCP authenticates johnloucks3, so this re-opens a closed gate. Proof that allow-lists drift back open even with policy intent.
- Attachment point: reconcile the deny lists AND add a `wing_policy` predicate rejecting johnloucks3-recipient drafts — mechanical enforcement, not config hygiene.

---

## STRUCTURAL CONSTRAINTS

**Protected files do not protect the action.** Six files (relay_send.py, wing_relay.py, run_commander_directive_sweep.py, dispatch_and_email.py, email_task_ingest.py, thunderbird_commander_inbox.py) are edit-protected by SO 2026-06-08. Critical distinction: protected-from-editing is NOT guarded-at-invocation. They can still be CALLED via Bash with zero runtime check. **The architecture must guard the call, not the file** — and the good news is enforcement lives ABOVE these files (the gateway consumer for relay drain, the OC plugin hook for OC bash calls). **No edit to any protected relay file is required** for the primary build. Defense-in-depth inside those files is optional and would itself need Claude Code + Commander approval.

**OpenCode HAS hooks — the task premise is wrong, and the verified inventory wins.** This is the single most important correction. OC's `permission.ask`/`tool.execute.before` are a real content-aware deny layer. The constraint is not "OC can't enforce" — it is "OC enforces nothing until a plugin is written, registered via the plugin key, and load-verified." Treat plugin-load verification as a hard gate; absent it, OC is silently advisory.

**Headless spawns don't inherit interactive context.** CLAUDE.md and persona @-refs auto-load only in interactive Claude Code. `claude -p` children get rules only if the caller inlines them as prose. This is why the spawn wrapper is the highest-leverage attachment point — it is the mandatory single funnel for every tool-capable agent, and it carries zero conduct policy today. EMPIRICALLY VERIFIED: a child `claude -p` IS blocked by a PROJECT-level PreToolUse hook even under bypassPermissions — so the hook must live in `.claude/settings.json` (project), never in a child-overridable location.

**The rule registry must become the single source of truth.** Today rules are restated across 4 CLAUDE.md-family files, which is the root cause of wording drift. The code registry must be canonical; the markdown files reference it rather than restate it. Without this, Option 4 enforces but the drift persists.

**Surfaces the engine cannot reach (these define the Option 3 backstop):** browser arbitrary-JS (denylist, can't scan); OC when the plugin is unloaded; any cron/systemd/background script that imports the Gmail service outside a hooked process; raw desktop-terminal Python (human-Commander territory). The engine enforces only where it is wired in.

---

## OPTION 4 RECOMMENDATION — CONFIRMED, WITH CAVEATS

Option 4 (PreToolUse hook on Claude Code + permission.ask plugin on OpenCode + policy calls at the three Telegram gateway sites, all shelling to a shared fail-closed `wing_policy.py` backed by a canonical rule registry) is the correct architecture. It is the only option that closes the Bash/Python send path, the relay-queue injection, and the headless-spawn multiplier — the gaps that advisory prose cannot touch. **Confirmed `option4_with_caveats`.**

The caveats are preconditions, not refinements. The build is incomplete — and in places actively dangerous (looks deployed, enforces nothing) — unless ALL of these hold:

1. **Fail CLOSED.** Any exception/missing-file/timeout in `wing_policy.py` = DENY. A traceback must never equal an open gate.
2. **Self-protection.** `wing_policy.py` + settings.json hook block + rule registry join the protected set; the hook denies edits to itself, settings.json, and the registry.
3. **Matchers scan the right things.** Bash command STRINGS (`.send(`, `send_*.py`, `relay_send`, `claude -p`, `telegram sendMessage`) AND browser MCP navigate/click/evaluate TARGETS (mail.google.com, web.telegram.org). MCP-tool-name matching alone merely re-covers the existing deny list — decorative.
4. **Browser arbitrary-JS tools are DENYLISTED, not policy-gated.**
5. **OC plugin is written, registered, and load-verified** — or OC stays advisory with no fail-closed signal.
6. **Gateway calls wing_policy at all three sites:** `handle_approve` (before L1125 send), `_drain_relay_queue` (before engine), `/agent`+`/ask` shell-outs.
7. **Spawn wrapper guarantees** children load hook-bearing project settings and never strip PreToolUse.
8. **Option 3 (post-hoc audit) runs as the BACKSTOP** under the structurally-uncoverable surfaces (browser JS, OC-plugin-down, unhooked cron/systemd). Not the primary gate — the only net under what cannot be intercepted.
9. **Rule registry is canonical;** the 4 markdown files reference it. This kills the drift root cause.

Pattern-matching is necessary but not sufficient — aliasing, base64-piping to `python -c`, dynamic call construction, and script renaming all evade regex. That residual is exactly why caveats 4 (denylist) and 8 (audit backstop) exist. Accept the architecture knowing pattern matching is the floor, not the ceiling.

---

## KEY DECISIONS FOR COMMANDER

1. **Approve denylisting browser arbitrary-JS tools on the client-send path** (`browser_evaluate`, `browser_run_code_unsafe`, Claude-in-Chrome `javascript_tool`). This is the only decision with a real cost attached: it removes browser-driven send/compose convenience. There is no policy-gate alternative — arbitrary JS cannot be intent-scanned. Recommend: approve. The convenience is rarely used; the gap is otherwise uncloseable.

2. **Approve adding `wing_policy.py`, the settings.json hook block, and the rule registry to the protected-file set** (expanding SO 2026-06-08 from 6 to 9 artifacts). Without this, the enforcement layer is self-deletable and the entire build is theater.

3. **Confirm enforcement lives ABOVE the protected relay files — no protected-file edit needed for the primary build.** The Commander decision here is about editing the *non-protected* Telegram gateway (permitted) and authoring the OC plugin — not about touching relay_send.py/wing_relay.py.

4. **Direct that the code rule registry become canonical** and the 4 CLAUDE.md-family files reference rather than restate it. This is what actually kills wording drift; without it Option 4 enforces but drift continues.

5. **Authorize the Signal gateway sender allowlist immediately** — it is the lowest-effort, highest-leverage single fix. The gateway is LIVE today with no sender check, mitigated only by a network binding that a re-link or second number defeats.

6. **Acknowledge the Option 3 audit backstop is mandatory, not optional** — it is the only coverage under browser JS, OC-when-plugin-down, and any unhooked cron/systemd/background import path. The engine enforces only where wired in; the audit is the net under everything else.

---

*This document was generated by a multi-agent Opus workflow (OODA Observe phase).*
*Build does NOT begin until Commander approves this plan.*
*Next step: Commander reviews → "proceed" → Wing executes Phase 1.*
