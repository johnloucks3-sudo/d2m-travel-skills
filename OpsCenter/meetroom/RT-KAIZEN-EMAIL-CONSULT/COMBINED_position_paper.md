# POSITION PAPER — KAIZEN Onboarding + Two-Way Email Reply Loop
## RT-KAIZEN-EMAIL-CONSULT · CC synthesis of CC + AG + OC, real disagreement surfaced

**BLUF:** Both features are buildable this session, reusing existing
plumbing (`email_conversation_agent.py`'s two-path pattern, the 4 live
KAIZEN bricks). One genuine design disagreement between AG and OC on
auto-send — CC's call: **OC's design wins**, explained below. Plan follows
in a separate document; no build starts without your explicit approval.

---

## Q1 — Onboarding copy (Dani's voice)

Both AG and OC drafted real copy. OC's reads closer to Dani's established
voice (warm, direct, no corporate gloss) and is tighter. Adopting OC's as
the base, lightly cleaned:

> **You've got three consultants on call — and they're all yours.**
>
> Every ticket here lands with three seats you get to pick from, depending
> on the job:
>
> - **CC (Claude)** — the judgment seat. Big builds, careful reasoning,
>   writing that needs a real voice behind it. Ask CC when it has to be
>   *thought through*.
> - **OC (DeepSeek)** — the $0 workhorse. Ops, scripts, the routine work
>   that keeps this Wing turning — fast, and never a dollar of cost.
> - **AG (Gemini)** — the second pair of eyes. Deep research, massive
>   documents, the independent look that catches what the first pass
>   missed.
>
> Not sure who should do it? Leave it to us — you're not signing for a
> stranger, they're your team. Send the ticket, and one of us picks it up
> and gets back to you.
>
> *(Not sure what "elevated gates" means? Leave it blank — that's exactly
> what we'd hope you'd do.)*
> — Dani

## Q2 — Auto-send vs. draft (the real disagreement)

**AG's proposal:** a new `VERIFIED_STAFF_ALLOWLIST` — auto-send to anyone
on it, draft-only otherwise.

**OC's proposal:** draft-only for every *initial* answer (to a
self-typed address), auto-send only for the *follow-up* leg — once
someone has already replied from an address, that reply IS proof they
control the mailbox, which is stronger evidence than anything the intake
form can assert at submission time.

**CC's call: OC's design.** AG's allowlist requires inventing and
maintaining a new piece of trusted state — who adds an address to it, by
what mechanism, is itself undesigned and becomes a second attack surface.
OC's design needs no new list: trust is earned structurally (a real reply
from a real inbox), the same principle `email_conversation_agent.py`
already uses to distinguish Commander from everyone else. It also means
v1 ships with **zero new auto-send paths on day one** — the first answer
to any ticket is always a draft, full stop, and the only thing that can
ever ­auto-send is a reply to a thread the recipient already opened
themselves.

**Safeguards adopted from both papers regardless of which leg sends**
(AG and OC substantively agree here):
- Sender-match required: auto-send only fires if the reply's `From`
  exactly matches the ticket's `submitted_email`.
- `gates` must be `[]` — no elevated-scope ticket ever auto-sends.
- Rate cap (OC: 3 auto-replies/ticket, 10/hr process-wide).
- Every auto-send fires the existing `NOW`-urgency Commander Telegram
  (reuse of the mismatched-submitter alert shipped earlier today).
- Content guardrail scan (AG) before any send — no API tokens, no
  internal file paths, no dossier contents leak into an outbound line.

## Q3 — Follow-up-becomes-new-ticket mechanics

AG and OC converge on the shape; OC's version is adopted as primary
(it verified against the real, current file layout live, including
`thunderbird_gmail.py`'s existing send guards):

- New file: `core/email/kaizen_email_loop.py` — same poll/read pattern as
  `email_conversation_agent.py` (its read-side helpers are reusable; this
  new file is NOT protected). **Zero edits to the protected
  `email_task_ingest.py`.**
- Detection: subject tag `[KAI-<ticket_id>]` on the outbound answer,
  matched on inbound reply (strip `Re:`/`Fwd:`, look for the tag) —
  primary key. RFC822 `Message-ID`/`In-Reply-To` as secondary
  corroboration.
- Sender check: reply `From` must equal the parent ticket's
  `submitted_email`, or it's an alert, not a new ticket (someone else
  replying into the thread is treated as suspicious, not routed).
- New ticket built via `build_cc_task(..., require_checkable=True)` —
  OC's correct catch: the intake form's `require_checkable=False` is a
  human-typed-into-a-form carve-out; a machine-triggered ticket from an
  email listener must keep the hard gate.
- `seat` and `gates` inherited read-only from the parent — an email can
  never change who executes or grant elevated authority.
- `verify_step` inherited from the parent (already passed the checkable
  gate once; email text can't reliably produce a new one).
- Dedup via processed-message-ID tracking, same bounded pattern as
  `email_conversation_agent.py`.

## Q4 — Smallest safe v1 (explicit NOT-build list)

Both papers converge closely; combined list:

1. **No multi-hop chains** — one hop only (parent + one follow-up = one
   new ticket). Every later reply in the same thread creates a flat new
   ticket pointed at the same parent, not a nested chain.
2. **No gate elevation via email** — `gates` are inherited read-only,
   never parsed from email text.
3. **No external submitters** — only converts replies whose sender
   matches a ticket's recorded `submitted_email`.
4. **No auto-completion of the parent ticket** — a follow-up doesn't mark
   anything "done"; status changes stay a human/runner action.
5. **No attachments / non-text bodies** — text-only replies in v1.
6. **No new inbox or alias** — reuse the existing `d2mconcierge` inbox
   plus the subject tag; a dedicated inbox is a later increment, not
   needed to close the loop.
7. **No client-facing traffic** — internal, password-authenticated staff
   only. Client inquiries stay on the existing Dani/WF-17 draft-only path.

---

*Full unedited seat cards: `ag_hale_input.md`, `oc_hale_input.md`,
`cc_hale_input.md` in this same RT session directory.*
