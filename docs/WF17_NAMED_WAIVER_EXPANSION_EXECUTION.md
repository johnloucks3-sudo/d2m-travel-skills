# WF-17 Named Waiver Expansion — Execution Record
**Date:** 2026-07-06 · **Status:** LIVE · **Plan:** `docs/WF17_NAMED_WAIVER_EXPANSION_PLAN_20260706.md`

Implements Commander directive 2026-07-06: extend the Nancy Lyons WF-17 exception into a generalized, code-enforced allowlist covering 5 named individuals.

## Components

| File | Role |
|---|---|
| `config/wf17_named_waivers.json` | The allowlist. Adding a name here is a Commander-only action. Not on this list = standard WF-17 draft-and-hold, no exceptions. |
| `core/email/wf17_named_waivers.py` | Guard + single send path (`send_waived_client_email`). Looks up `get_waiver(to_email)`; raises `NotWaivedError` if the recipient isn't on the allowlist. Routes to the channel/voice the waiver record specifies, CCs the waiver's `cc` list, and logs a provenance stamp to `hale_decisions.md` on every send. |
| `core/email/dani_email_responder.py` | Dani-voice-track integration. Watches d2mconcierge Gmail inbox (`dani-email-responder.timer`, ~5 min cadence), matches inbound senders against `get_waiver()`, spawns a headless Claude in Dani's voice to draft a reply, then sends via `send_waived_client_email(in_reply_to_gmail_id=...)` to keep the exchange threaded. |
| `hale_email_responder.py` (prior build, 2026-07-06) | Same pattern, Hale-voice-track (Bryana, Susan), AgentMail channel. |

## Allowlist (5 individuals, 2 voice tracks)

| Name | Email(s) | Voice | Channel | Notes |
|---|---|---|---|---|
| Nancy Lyons | klyons3@bellsouth.net, nancylyons73@outlook.com | Dani | d2mconcierge Gmail | Original exception, CC ken@bellsouth.net + johnloucks3 |
| Kim Westbrook | crnakim@yahoo.com | Dani | d2mconcierge Gmail | Advisory only — self-books via Interline/Perx |
| Stefanie Burcham | stef@bbenefits.net | Dani | d2mconcierge Gmail | Commander's sister, Nexion-affiliated agent — peer voice, highest reputational stakes |
| Bryana Jarboe | bryanajarboe@gmail.com | Hale | AgentMail (hale-thunderbird@) | Gift-tier friend, Hale direct |
| Susan Loucks | susanna.loucks@gmail.com | Hale | AgentMail (hale-thunderbird@) | Wing-adjacent correspondence only — does NOT cover Loucks joint-trip-as-D2M-client lifecycle emails (SO 2026-06-18 carve-out, untouched) |

## Discipline enforced on every waived send
1. **CC johnloucks3@gmail.com** — hard-coded into every waiver's `cc` list; not optional per-send.
2. **Hale + Silver draft review before send** — process discipline (not code-enforced); documented in each waiver's `conditions`.
3. **Third-person voice** ("John and Susan have..." never "we"/"our") — voice discipline carried in persona prompts, not the guard.
4. **Provenance stamp to `hale_decisions.md`** — code-enforced. `_log_provenance()` fires unconditionally inside `send_waived_client_email`, before return, on every successful send. Cannot be skipped without bypassing the guard entirely.

## Verification (2026-07-06, this session)
Ran `get_waiver()` against all 6 allowlisted addresses (5 names, Nancy has 2 addresses) — all resolved to the correct waiver record. Ran against 3 non-allowlisted addresses — all correctly returned `None` (guard rejects, caller falls back to standard WF-17 draft-and-hold). No live sends triggered during verification; provenance log confirms real sends already occurred and logged for Bryana Jarboe and Kim Westbrook prior to this pass.

A temporary `TEST-DANI-RESPONDER-ONLY` allowlist entry (used to validate `dani_email_responder.py` against johnloucks3's own inbox during development) has been removed post-verification per its own `source` field ("removed after verification"). The provenance stamp from that test send remains in `hale_decisions.md` as an audit record — history is not edited.

## Metric
`unwaivered_sends` — target zero. Enforced structurally: the guard is the only send path with `send_channel` logic; there is no code path that sends to a non-allowlisted address without hitting the standard WF-17 draft-and-hold flow.
