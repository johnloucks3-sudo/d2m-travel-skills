# AgentMail Bold Uses — Infrastructure Reference
**Date:** 2026-07-06 · Source: `docs/AGENTMAIL_BOLD_USES_AND_OBE_AUDIT_20260706.md` Part 1

---

## ⚠️ IMPORTANT — read before deploying anything new

Checked the repo before building: **Bold Uses #1–#4 and #6 were already built and
verified live earlier the same day** — commit `f3df55e85` ("feat(email): Bold Uses
1-6 built and verified live (Commander: GO!!!)"). This doc does not rebuild that
work. It:

1. Documents the 5 use cases from the audit (mapping the audit's 4 numbered items
   + the gift-tier generalization to the actual files, live or template),
2. Fills the 3 gaps that genuinely didn't exist: a rich HTML alert template, a
   CONDOR→WIND outbound compose helper, and a persona capacity-planning template,
3. Gives checklists for the parts that are capacity/cost-gated, not code-gated.

If you're picking this up fresh: **grep for the file paths below before writing
new code.** Most of this is already running.

---

## Use Case 1 — Cross-engine native email (CONDOR ↔ WIND)

**Status: LIVE, verified end-to-end 2026-07-06.**

| Direction | Mechanism | File |
|---|---|---|
| Inbound to WIND (from CONDOR or Commander) | Polls WIND inbox, spawns `opencode run --agent hale-oc`, sends reply | `core/email/wind_email_responder.py` |
| Outbound CONDOR → WIND (compose helper, new) | `send_to_wind(subject, text, html=None)` | `core/email/cross_engine_mail.py` |
| Outbound WIND → CONDOR (compose helper, new) | `send_to_condor(subject, text, html=None)` | `core/email/cross_engine_mail.py` |

**Addresses:** CONDOR = `hale-thunderbird@agentmail.to` · WIND =
`dreams2memories-80921@agentmail.to`. Both share one AgentMail account/API key
(`config/agentmail_credentials.json`); each engine sends from its own inbox,
never impersonates the other.

**How to compose/send (script/CLI context):**
```python
from core.email.cross_engine_mail import send_to_wind
send_to_wind(
    subject="Research request: Amadeus fare-watch validation",
    text="WIND — can you spot-check 3-5 Amadeus fare watches against Centrav "
         "historical data? MISSION-1514. Reply here with findings.",
)
```
From inside a live OpenCode session, prefer the native AgentMail MCP tools
already registered in `opencode.json` over shelling out to this helper.

**Deploy units:** `deploy/wind-email-responder.service` +
`deploy/wind-email-responder.timer` (poll interval 15 min per
`docs/AGENTMAIL_AUSTERITY_MEASURES_20260706.md`).

**⚠️ NOT a replacement for `core/hale_bus/brain_bridge.py`.** Email is a
conversation channel; brain_bridge is the concurrency primitive (atomic claim,
no double-work, queryable ownership). Use brain_bridge to assign/claim work.
Use email to discuss it, attach findings, or ask a question that doesn't need
a claim. This was ELON's explicit warning in the OBE audit — do not conflate
the two.

**Checklist before using in a new workflow:**
- [ ] Is this actually a claim/ownership question? → use brain_bridge, not email.
- [ ] Sender allowlist correct? (`wind_email_responder.py` only acts on mail
      from CONDOR or `johnloucks3@gmail.com` — arbitrary senders are ignored.)
- [ ] Standing CC to `johnloucks3@gmail.com` will fire automatically
      (`agentmail_client.py:_with_standing_cc`) — do not attempt to suppress it.

---

## Use Case 2 — Persona inbox infrastructure (Sterling, Dembe, Harlan, Reyes)

**Status: PARTIALLY LIVE.** Sterling is deployed and verified. Dembe/Harlan/Reyes
are template-only, gated on inbox capacity (not code).

| Persona | Address | Status |
|---|---|---|
| Sterling | `sterling-thunderbird@agentmail.to` | **ACTIVE** — real email in, correctly-voiced threaded reply out, verified live |
| Dembe | `dembe-thunderbird@agentmail.to` | `pending_capacity` |
| Harlan | `harlan-thunderbird@agentmail.to` | `pending_capacity` |
| Reyes | `reyes-thunderbird@agentmail.to` | `pending_capacity` |

**Files:**
- Live routing config: `config/persona_inboxes.json` (allowed senders +
  per-persona status; read by the responder engine every cycle)
- Capacity-planning template (new): `config/agentmail_personas.json` — cost
  model, the two free-tier alternatives already researched and rejected
  (Robotomail = trial-then-paid, AI Inbx = signups paused, both verified live
  2026-07-06), and the activation checklist per persona
- Responder engine: `core/email/persona_email_responder.py` — watches each
  `status: active` inbox, spawns a headless Claude in that persona's voice
  (reads the real persona file, e.g. `Personas/a7_sterling_personality.md`),
  sends the reply back
- Deploy units: `deploy/persona-email-responder.service` +
  `deploy/persona-email-responder.timer`

**Activation is a capacity decision, not a build decision.** AgentMail free
tier caps at 3 inboxes; all 3 are spoken for (CONDOR, WIND, Sterling). Next
persona needs either:
1. AgentMail Developer tier (10 inboxes, no cap) — **financial commitment,
   Commander's call**, or
2. A second free-tier provider — **Hale may self-serve** per the 2026-07-06
   standing authorization (Obstacle-Routing Protocol), but re-verify
   Robotomail/AI Inbx availability before assuming still blocked; they were
   checked same-day and may change.

**Onboarding checklist (per new persona, once a slot exists):**
- [ ] Create inbox: `AgentMailClient().create_inbox(username, display_name, client_id=f"inbox-{username}")`
- [ ] Add entry to `config/persona_inboxes.json` with `"status": "active"`
- [ ] Flip the matching entry in `config/agentmail_personas.json` to `"deployed"`
- [ ] Confirm `persona_file` path in the entry actually exists (`ls Personas/...`)
- [ ] Restart `persona-email-responder.timer` (or wait for next cycle)
- [ ] Send one real test email from `johnloucks3@gmail.com`, confirm a
      correctly-voiced threaded reply — this is the only real verification;
      an API "message sent" response is not (Obstacle-Routing Protocol,
      independent verification).

---

## Use Case 3 — Rich incident/alert emails (vs. terse Telegram)

**Status: LIVE (text) + template now available (HTML, new this session).**

| Component | File |
|---|---|
| Send function (plain text + attachments, verified live) | `core/email/rich_incident_email.py:send_incident_email()` |
| HTML render function (new) | `core/email/rich_incident_email.py:render_alert_html()` |
| Branded HTML template (new) | `scripts/agentmail_alert_template.html` |

**Design:** Telegram keeps the "look now" ping (per
`docs/TELEGRAM_AGENTMAIL_ROE_20260706.md` — Telegram/AgentMail veto-surface
doctrine, do not remove Telegram). This channel carries the substance: full
log excerpt, cert/credential detail, attached diff or screenshot.

**Template:** USAFA colors (cream `#f7f3ea` background, blue `#0000ff` ink,
navy `#003087` accent, Georgia font) per `SO_EMAIL_RULES_UPDATE_20260530`.
Table-based layout, all CSS inline, no external assets — Gmail-safe.
Severity badge color-codes P0 (red) / P1 (amber) / P2 (olive) / INFO (navy).

**Verified render test (this session):** filled the template with a sample
credential-expiration payload (regent_cookies_oa / ASPXAUTH, 41.3h expired) —
zero unfilled `{{...}}` placeholders, `html.parser` parses cleanly, table/tr/td
tags balance.

**Example — credential expiration alert with full detail in-email:**
```python
from core.email.rich_incident_email import send_incident_email

send_incident_email(
    subject="Regent OA cookie expired",
    summary="regent_cookies_oa (ASPXAUTH auth-gate) expired 41.3 hours ago. "
            "Affects OA-side portal pulls only.",
    severity="P0",
    details={
        "Credential": "regent_cookies_oa",
        "Cookie": "ASPXAUTH [auth-gate]",
        "Expired": "41.3h ago",
        "Last verified": "2026-07-04T14:22:00Z",
        "Affected": "OA-side Regent portal pulls",
    },
    log_excerpt="[2026-07-06 05:59:01] credentials_health_check: "
                "regent_cookies_oa STATUS=expired age=41.3h",
)
```
`html` is generated automatically whenever `details` or `log_excerpt` is
passed; omit both and it falls back to the original plain-text-only path
(unchanged, already verified live) — no caller of the old signature breaks.

**Checklist before sending an alert:**
- [ ] Severity matches the actual gate it should trip (P0 = client-affecting
      or wing-stopping per CI Razor-Sharp doctrine; P1 = degraded; P2 = watch)
- [ ] `details` dict has no PII beyond what the recipient (Commander) already
      has clearance for — this channel is internal, not client-facing
- [ ] Attachments (if any) are the actual evidence, not a summary of it

---

## Use Case 4 — Supplier/vendor correspondence protocol

**Status: LIVE (code), not yet exercised against a real vendor.**

**File:** `core/email/vendor_correspondence.py:send_vendor_inquiry()`

**Authority boundary (Hale's existing standing authority, unchanged by this
build):**

| In scope (Hale sends, no gate) | Out of scope (Commander first) |
|---|---|
| Rate check / availability question | Anything that could change a number |
| Documentation / itinerary request | Anything that commits to a booking |
| Status follow-up on an existing booking | Contract term changes |
| General informational inquiry | New vendor relationship first contact |

**Bright-line test (from `hale_cos.md`):** *if the conversation could result
in a number changing or a commitment being made — flag to the Commander
before sending.* This is not a new rule; `vendor_correspondence.py` is a new
channel for an authority that already existed.

**Domain caveat:** `@agentmail.to` is a cold domain for external commercial
correspondence — fine for relationships that already trust the Wing (an
existing hotel contact, a known DMC), risky for cold outreach until a
verified custom domain exists. Don't use this channel to cold-email a new
supplier; use the existing Gmail channels for that until domain auth is
fixed (same constraint already governing client-send-as, see
`SO_TP_DRAFT_ROUTING_20260620`).

**Pre-send checklist:**
- [ ] Transactional or informational only — re-read the bright-line test above
- [ ] Vendor already has an established relationship with the Wing (not cold)
- [ ] No dollar figure, date commitment, or contract term is being proposed
      *by the Wing* (asking "what's your rate for X" is fine; saying "we'll
      take X at $Y" is not)
- [ ] If genuinely unsure which side of the line this falls on: escalate to
      Commander before sending, don't guess

---

## Use Case 5 — Gift-tier pattern generalization (reusable onboarding)

**Status: LIVE.** `scripts/onboard_gift_tier_friend.py` — generalizes the
Bryana Jarboe pattern (named-waiver + Hale-voice + real tool access) already
proven with Bryana and Susan Loucks.

**The mechanism, reduced to its parts:**
1. **Named-waiver entry** in `config/wf17_named_waivers.json` — the ONLY
   thing that grants a send. `emails`, `cc` (always includes
   `johnloucks3@gmail.com`), `voice_track` (`"dani"` or `"hale"`),
   `send_channel`.
2. **Voice track decision** — is this relationship Dani's (client-adjacent,
   warm concierge register, d2mconcierge Gmail channel) or Hale's
   (gift-world friend, AgentMail channel, `agentmail_hale_thunderbird`)?
   Decided by: is there any travel-booking context (→ Dani) or is it a pure
   "friends I'd serve for free" relationship with no commercial shape (→
   Hale)?
3. **Scope note** — every waiver should state explicitly what it does NOT
   cover (see Susan Loucks' entry: covers general correspondence, does NOT
   cover Loucks-as-D2M-client lifecycle emails, which stay on the separate
   johnloucks3 carve-out).
4. **Real tool access** — the waived responder (`dani_email_responder.py` or
   `hale_email_responder.py`) spawns a headless Claude with full Wing MCP
   tool access in the assigned voice, not a canned-reply bot.

**Onboarding checklist for a new relationship:**
- [ ] Voice track: Dani or Hale? (see decision rule above)
- [ ] Scope: what does this waiver cover, and — as important — what does it
      explicitly NOT cover?
- [ ] Add entry to `config/wf17_named_waivers.json` (Commander-only action
      per that file's own `_doc` field — this is not something Hale adds
      unilaterally)
- [ ] CC `johnloucks3@gmail.com` on every message — standing, no exceptions
- [ ] Draft review pass (Hale + Silver) before any Hale-voice send
- [ ] Send the intro email itself via `scripts/onboard_gift_tier_friend.py`
      (introduces Grace/Hale/Dani and the live chat page, per the `grace-gift`
      skill pattern)

---

## Files touched this session

| File | Status |
|---|---|
| `scripts/agentmail_alert_template.html` | new |
| `core/email/rich_incident_email.py` | extended (backward-compatible — `render_alert_html()` added, `send_incident_email()` gained optional `severity`/`details`/`log_excerpt` kwargs) |
| `core/email/cross_engine_mail.py` | new |
| `config/agentmail_personas.json` | new (capacity template, does not replace `config/persona_inboxes.json`) |
| `docs/AGENTMAIL_BOLD_USES_INFRASTRUCTURE.md` | new (this file) |

No new services or timers were started. Everything above either reuses an
already-running deploy unit or is inert until explicitly invoked.
