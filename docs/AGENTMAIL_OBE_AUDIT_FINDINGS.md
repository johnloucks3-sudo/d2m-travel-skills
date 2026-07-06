# AgentMail OBE Audit — Findings
**Date:** 2026-07-06 · Source: `docs/AGENTMAIL_BOLD_USES_AND_OBE_AUDIT_20260706.md` Part 2 (ELON, Weekly Kill Audit lens)

---

## Killed

**`scripts/send_cruise_tool_v2.py`, `scripts/render_nancy_lyons_email.py`**
Hand-rolled Lyons send scripts, superseded by `wf17_named_waivers.py`'s single enforcement point (`config/wf17_named_waivers.json` + `core/email/wf17_named_waivers.py`). Both scripts were already archived to `archive/retired_scripts/` (as `.retired`) prior to this session, commit `cb9455795` — "chore: retire hand-rolled Lyons send scripts, superseded by wf17_named_waivers.py". This audit re-verified the kill is clean:
- `grep -r "send_cruise_tool_v2\|render_nancy_lyons_email" --include="*.py" .` → zero hits in any `.py` file.
- Remaining references are historical only: `hale_decisions.md`, `docs/AGENTMAIL_BOLD_USES_AND_OBE_AUDIT_20260706.md`, `OpsCenter/state/STACK_FRESHNESS.md` / `stack_freshness_report.json` — all narrative/log mentions, not live code paths.

**Telegram long-form chunking — use case, not the function**
The chunking mechanism itself (`tg_send_chunks`, `OpsCenter/thunderbird_telegram_gw.py:515`) is still live code — no file to archive; there is no standalone `scripts/tg_send_chunks.py`. Deprecation is scoped to the *use case*: long-form content (briefs, sitreps) should route to AgentMail email (primary C2 as of 2026-07-06) rather than being sliced into 4096-char Telegram messages. Added a deprecation docstring note directly on `tg_send_chunks` pointing back to this audit. The function remains available for short multi-part Telegram sends — it is not removed.

## NOT Killed (explicit ELON warnings — do not touch)

- **`core/hale_bus/brain_bridge.py` claim-board.** Not replaceable by CONDOR/WIND emailing each other — the claim-board is a concurrency primitive (atomic claim, no double-work), email has no lock semantics.
- **Telegram as a channel.** Stays live per Channel Registry — the confirmed-delivery auto-execute mechanism checks both Telegram and email for a veto reply in real time; pulling Telegram halves that veto surface.
- **`core/email/d2m_agentmail_bridge.py`** (Gmail→AgentMail relay for Lyons). Patches a real scope gap (no `gmail.settings.sharing` OAuth grant). Future kill candidate only once true Gmail-side forwarding exists — not now.

## Follow-up — handed to Whetstone (A14)

1. Confirm the two same-session script kills are clean (no other references) — verification grep above found zero `.py` references; Whetstone to do an independent pass across non-`.py` config/state files if desired.
2. Fold the Telegram-chunking-for-long-content deprecation into weekly CI doctrine (`config/ci_registry.json` / CI sweep) so future long-form additions default to email, not Telegram chunking.
