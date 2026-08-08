BLUF: Commander's fix for the broken reply loop — a hotlinked "child form"
in the answer email, KAI# pre-filled, instead of relying on email-reply
threading. Real bug this solves: `kaizen_email_loop.py`'s draft is hosted
in the Commander's own `johnloucks3` Gmail account with `From:
johnloucks3@gmail.com` (needed so he can review/send from where he already
looks — see `gmail_create_draft_sync`'s `stage_in` doctring, SO
`SO_TP_DRAFT_ROUTING_20260620`). A reply from the recipient therefore lands
in HIS inbox, not `d2mconcierge@gmail.com`, which is the mailbox Pass 2
polls — the loop was structurally broken regardless of tone. Commander's
proposal replaces email-reply detection entirely with a web-form click.
Budget note: Commander is at 93% of a 5h window — keep this RT LEAN, one
round, tight cards, no padding.

## The proposal, as given
"When sending, include the KAI-reference number, include a hot link to a
related child form, with the KAI # pre-filled, nothing else needed but a
reply window."

## Ground truth

- `scripts/kaizen_intake_server.py` — the existing form (Basic-Auth, shared
  password). Fields: submitted_by, email, phone, origin, seat, spec,
  verify_step, gates.
- The routing bug is real and structural, not fixable by changing FROM
  address alone without giving up Commander review-visibility (his personal
  Gmail account has no verified send-as alias for the d2mluxury.quest
  domain — staging the draft in `d2mconcierge` instead would fix reply
  routing but move the draft somewhere he doesn't review from, per the
  existing SO).
- `core/email/kaizen_email_loop.py` Pass 2 (INBOUND) currently does the
  fragile part: subject-tag regex, RFC822 threading, `_strip_quoted_reply`,
  sender-match against `submitted_email`. A form-based reply makes all of
  that unnecessary — the parent link IS the correlation, no parsing needed.

## Questions — answer tight, no padding

1. **Does the child-form link fully replace Pass 2, or coexist as a
   fallback?** Commander's framing ("nothing else needed but a reply
   window") reads as full replacement. Confirm or push back.
2. **Child form shape.** Same fields as the main form, or a stripped
   version — just the KAI# (pre-filled, read-only) + a single reply text
   box + submit? What should be pre-filled vs asked again (submitted_by/
   email/phone — inherit from parent, or re-ask for a fresh identity
   check)?
3. **Auth model for the reply link.** The main form requires the shared
   password. Does the child-form link need the same Basic-Auth, or does the
   link itself (containing the KAI# as an unguessable-enough token) serve
   as sufficient authorization for THIS one ticket's reply? Real security
   call — say which and why.
4. **Mechanics.** New route on the same `kaizen_intake_server.py` (e.g.
   `GET /reply?parent=<ticket_id>` pre-filling a form, `POST` builds a
   child ticket same as today's Pass 2 logic) — confirm this is the right
   shape, or propose different.

Write your own card, short. CC will synthesize fast, show a lean plan, no
execution until Commander approves.
