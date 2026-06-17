# Dani Bot Sandbox Plan — MISSION-255
# A7 Sterling | 2026-06-17 | PREPARE ONLY — not applied

## Executive Summary

The public-facing Dani Telegram bot shares the same `call_claude_engine()` function
with the Commander-only D2MC2C and HaleD2M bots. That shared function runs
`--dangerously-skip-permissions` on every invocation, which bypasses all Claude
permission gates for any user who can reach any of the three bots. For D2MC2C and
HaleD2M, which are Commander-only via hard user_id whitelist, the risk is low. For
Dani, which is "open to all — clients, prospects, anyone" (gateway line 2046), the
flag is an active attack surface: any member of the public gets a Claude instance with
zero permission constraints.

The fix is **not** to edit `call_claude_engine` in place. That would change behavior
for the Commander-only bots and is wider than the task. The fix is to parameterize the
shared function so Dani passes a sandboxed flag set while the Commander bots continue
unchanged.

---

## File and Line Map

| Item | Path | Lines |
|------|------|-------|
| Shared headless engine | `OpsCenter/thunderbird_telegram_gw.py` | 696-746 |
| Dani engine wrapper | `OpsCenter/thunderbird_telegram_gw.py` | 1681-1687 |
| Hale C2 engine wrapper | `OpsCenter/thunderbird_telegram_gw.py` | 1663-1669 |
| Hale chat engine wrapper | `OpsCenter/thunderbird_telegram_gw.py` | 1672-1678 |
| Startup self-test (D2MC2C only) | `OpsCenter/thunderbird_telegram_gw.py` | 1995-2032 |
| Systemd service | `~/.config/systemd/user/thunderbird-telegram-gw.service` | — |

---

## Before (current state)

`call_claude_engine` signature:
```python
def call_claude_engine(prompt: str, model: str = SONNET_MODEL) -> str:
```

subprocess.run call at lines 718-728:
```python
result = subprocess.run(
    [
        "/home/john/.local/bin/claude",
        "--model",
        model,
        "-p",
        "-",
        "--output-format",
        "text",
        "--dangerously-skip-permissions",   # <-- bypasses ALL permission checks
    ],
    input=prompt,
    ...
)
```

`dani_claude_engine` at lines 1681-1687:
```python
def dani_claude_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    prompt = _build_dani_claude_prompt(context_text, message)
    model = model_override or HAIKU_MODEL
    return call_claude_engine(prompt, model=model)   # inherits --dangerously-skip-permissions
```

---

## After (ready-to-apply change)

### Change 1 of 2 — Parameterize `call_claude_engine`

Replace lines 696-746 (the full function definition and signature):

OLD:
```python
def call_claude_engine(prompt: str, model: str = SONNET_MODEL) -> str:
    """
    Invoke Claude headless via `claude -p`.
    Uses Max OAuth — injects CLAUDE_CODE_OAUTH_TOKEN from credentials file
    because the systemd service env does not inherit the interactive session token.
    """
    env = dict(os.environ)
    # Strip stale API key — it overrides OAuth and causes "Invalid API key" rc=1.
    # Headless Claude uses OAuth via CLAUDE_CODE_OAUTH_TOKEN exclusively.
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_BASE_URL", None)  # Strip MAX proxy URL — breaks headless Claude
    _creds = Path.home() / ".claude" / ".credentials.json"
    if _creds.exists():
        try:
            _tok = json.loads(_creds.read_text()).get("claudeAiOauth", {}).get("accessToken")
            if _tok:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = _tok
        except Exception:
            pass

    try:
        # Use -p - (stdin) to avoid OSError: Argument list too long on large prompts
        result = subprocess.run(
            [
                "/home/john/.local/bin/claude",
                "--model",
                model,
                "-p",
                "-",
                "--output-format",
                "text",
                "--dangerously-skip-permissions",
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=ENGINE_TIMEOUT,
            env=env,
            cwd=str(THUNDERBIRD),
        )
        if result.returncode == 0:
            return result.stdout.strip()
        err = result.stderr.strip()
        log.error("Claude headless rc=%d: %s", result.returncode, err[:300])
        return f"[Engine error — Claude rc={result.returncode}]"
    except subprocess.TimeoutExpired:
        return "[Engine timeout — Claude exceeded limit]"
    except FileNotFoundError:
        return "[Engine error — claude binary not found]"
    except Exception as e:
        return f"[Engine error — {e}]"
```

NEW:
```python
def call_claude_engine(
    prompt: str,
    model: str = SONNET_MODEL,
    extra_flags: list[str] | None = None,
) -> str:
    """
    Invoke Claude headless via `claude -p`.
    Uses Max OAuth — injects CLAUDE_CODE_OAUTH_TOKEN from credentials file
    because the systemd service env does not inherit the interactive session token.

    extra_flags: additional CLI flags inserted after --output-format text.
        Default (None) = ["--dangerously-skip-permissions"] — preserves existing
        Commander-bot behavior.
        Pass [] or ["--tools", ""] for sandboxed callers (e.g. public Dani bot).
    """
    if extra_flags is None:
        extra_flags = ["--dangerously-skip-permissions"]

    env = dict(os.environ)
    # Strip stale API key — it overrides OAuth and causes "Invalid API key" rc=1.
    # Headless Claude uses OAuth via CLAUDE_CODE_OAUTH_TOKEN exclusively.
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_BASE_URL", None)  # Strip MAX proxy URL — breaks headless Claude
    _creds = Path.home() / ".claude" / ".credentials.json"
    if _creds.exists():
        try:
            _tok = json.loads(_creds.read_text()).get("claudeAiOauth", {}).get("accessToken")
            if _tok:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = _tok
        except Exception:
            pass

    try:
        # Use -p - (stdin) to avoid OSError: Argument list too long on large prompts
        cmd = [
            "/home/john/.local/bin/claude",
            "--model",
            model,
            "-p",
            "-",
            "--output-format",
            "text",
        ] + extra_flags
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=ENGINE_TIMEOUT,
            env=env,
            cwd=str(THUNDERBIRD),
        )
        if result.returncode == 0:
            return result.stdout.strip()
        err = result.stderr.strip()
        log.error("Claude headless rc=%d: %s", result.returncode, err[:300])
        return f"[Engine error — Claude rc={result.returncode}]"
    except subprocess.TimeoutExpired:
        return "[Engine timeout — Claude exceeded limit]"
    except FileNotFoundError:
        return "[Engine error — claude binary not found]"
    except Exception as e:
        return f"[Engine error — {e}]"
```

### Change 2 of 2 — Pass sandboxed flags from `dani_claude_engine`

Replace lines 1681-1687:

OLD:
```python
def dani_claude_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    prompt = _build_dani_claude_prompt(context_text, message)
    # Haiku default — Sonnet on model_override or keyword escalation
    model = model_override or HAIKU_MODEL
    return call_claude_engine(prompt, model=model)
```

NEW:
```python
# MISSION-255: Dani is public-facing (open to all). Sandbox by passing --tools ""
# which disables all tool access. No tools = nothing to gate = --dangerously-skip-permissions
# is moot and is intentionally absent. Verified: RC=0, clean Dani voice 2026-06-17.
_DANI_SANDBOX_FLAGS: list[str] = ["--tools", ""]

def dani_claude_engine(
    context_text: str, message: str, model_override: str | None
) -> str:
    prompt = _build_dani_claude_prompt(context_text, message)
    # Haiku default — Sonnet on model_override or keyword escalation
    model = model_override or HAIKU_MODEL
    return call_claude_engine(prompt, model=model, extra_flags=_DANI_SANDBOX_FLAGS)
```

---

## What Is NOT Changed

- `hale_claude_engine` (line 1663) — Commander-only (D2MC2C), no change. Still gets
  `--dangerously-skip-permissions` via the default `extra_flags=None` path.
- `hale_chat_engine` (line 1672) — Commander-only (HaleD2M), no change. Same default.
- Startup self-test (line 2009) — Commander-only D2MC2C health probe. Intentionally
  untouched. Uses `--dangerously-skip-permissions` directly; that is correct because
  it tests the Commander-only engine, not the public path.
- All other callers of `call_claude_engine` (lines 1862, 1938) — retain default
  behavior.
- No protected files touched (email scanner, relay, inbox scanner).
- `mission_board.json` not touched.

---

## Why This Is Safer

### Current risk
`--dangerously-skip-permissions` tells Claude to skip ALL permission prompts for file
writes, bash execution, and any other tool use. On a public bot — one with no user_id
whitelist — any member of the public gets a Claude process with that flag active.
If Dani ever gains tools (MCP wires in, project-level tools detected, etc.), a
motivated caller can attempt adversarial tool invocation without any permission gate.
Even today, with no tools wired to Dani, the flag signals an architecture that does not
enforce least privilege on the highest-exposure surface in the Wing.

### After the change
`--tools ""` disables all Claude tool access for Dani's subprocess. No tools available
= no permission prompts needed = `--dangerously-skip-permissions` is not present and
not needed. Dani's function — conversational text response — requires no tools. Verified
2026-06-17: RC=0, natural client-voice reply on identical prompt. The Commander-only
bots are unaffected.

---

## Residual Risk

1. **If Dani's prompt design ever needs a tool** (e.g., a future wire to email or
   calendar): `--tools ""` would silently kill it. The fix at that point is to replace
   `["--tools", ""]` with `["--allowedTools", "<specific-tool>"]` scoped to exactly
   what Dani needs. The `_DANI_SANDBOX_FLAGS` constant is the single place to update.

2. **Rate-limit masquerade**: The claude CLI returns "wrong model" errors on 429s.
   This behavior is unchanged by this fix. If Dani returns [Engine error] on a
   client message, check rate limits before assuming the sandbox is the cause.

3. **`--tools ""` and future MCP**: If project-level MCP tools are added to the
   `.claude.json` in THUNDERBIRD, `--tools ""` will also suppress those for Dani.
   Commander-only bots inherit project MCP normally. Monitor if adding Wing MCP tools
   ever causes Dani to stop responding to questions requiring lookups.

4. **This does not sandbox network access**: Claude's text generation has no network
   fence. Dani can still reference anything in her training data. The tool fence
   prevents _execution_ (bash, file writes, API calls via tools), not _generation_.

---

## Test Protocol — No Service Restart Required

The Commander can verify the change before restarting the live service:

```bash
# Step 1: Run the manual sandbox test (identical to the verified test 2026-06-17)
TOKEN=$(python3 -c "
import json; from pathlib import Path
creds = Path.home() / '.claude' / '.credentials.json'
print(json.loads(creds.read_text()).get('claudeAiOauth', {}).get('accessToken',''))
")

env -u ANTHROPIC_API_KEY -u ANTHROPIC_BASE_URL CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" \
  /home/john/.local/bin/claude \
  --model claude-haiku-4-5-20251001 \
  -p "You are Dani, a luxury travel concierge. A client asks: What cruises do you recommend? Reply in 2 sentences max." \
  --output-format text \
  --tools "" 2>&1; echo "RC=$?"
# Expected: RC=0, natural concierge reply, no tool attempts
```

```bash
# Step 2: Apply the two code changes to thunderbird_telegram_gw.py (per the
#          Before/After sections above)

# Step 3: Restart the service (the single final action)
systemctl --user restart thunderbird-telegram-gw.service

# Step 4: Verify service health
systemctl --user status thunderbird-telegram-gw.service

# Step 5: Tail logs for 60 seconds watching for engine errors
journalctl --user -u thunderbird-telegram-gw.service -f --since now
# Look for: "Engine self-test OK" and no [Engine error] lines

# Step 6: Send a test message to the Dani bot from a non-Commander account
#          (or Commander's own account works too — the sandbox applies regardless)
# Expected: Normal Dani concierge reply within ENGINE_TIMEOUT (60s)
```

---

## The Single Commander Action to Apply

After reviewing this document and agreeing the change is correct:

1. Apply the two edits to `/home/john/Thunderbird/OpsCenter/thunderbird_telegram_gw.py`
   (or direct Sterling to apply them in a supervised session).
2. Run the manual test (Step 1 above) to confirm RC=0 independently.
3. Execute: `systemctl --user restart thunderbird-telegram-gw.service`

That is the complete application sequence. The live D2MC2C and HaleD2M bots continue
operating without interruption during the restart (systemd brings the new process up
before killing the old one, and the 10s RestartSec provides clean rollover).

---

## A7 Metrics This Resolves

| KPI | Before | After |
|-----|--------|-------|
| Public-bot permission exposure | HIGH — skip-permissions on open bot | ZERO — tools disabled |
| Blast radius of skip-permissions | All 3 bots via shared function | Commander-only bots only (2 of 3) |
| Least-privilege compliance | FAIL | PASS |

Owner: A7 Sterling
Threshold: public-facing bots must not carry --dangerously-skip-permissions
Measurement cadence: weekly grep audit on commits (Baldrige Sunday sweep already runs this)
