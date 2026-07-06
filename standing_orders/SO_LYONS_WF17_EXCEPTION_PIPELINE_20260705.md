# SO — Nancy Lyons WF-17 Exception: Draft → Silver → Hale → Send Pipeline
## Standing Order 2026-07-05 · Dreams2Memories Travel, LLC · Thunderbird Wing

---

## SCOPE

**Applies ONLY to correspondence with Nancy Lyons** (klyons3@bellsouth.net) and Ken Lyons (kenlyons73@bellsouth.net). Does not generalize to any other client. Does not retire or soften WF-17 anywhere else — every other client stays exactly where WF-17 has them: draft-and-hold for Commander review and send.

**Why this exception exists:** Nancy is friend-service/pro-bono, outside the Wing, not a revenue client. Commander authorized Dani (A3) to correspond with her directly (2026-07-05, verbal, Claude Code session) as a deviation from `SO_WF17_CLIENTSEND_PROHIBITION_20260530.md`, replacing his personal send-click with a two-check gate.

---

## THE PIPELINE (mandatory, every message, no exceptions)

```
1. DRAFT     → Dani composes, staged in johnloucks3 Gmail (THUNDERBIRD-Commander-Review label)
2. COMMANDER → reviews, edits directly in the draft if desired (first pass may need format cleanup —
               see NOTE below)
3. SILVER    → before/after conditions check (see CHECKLIST) — verdict written in his voice, visible
4. HALE      → reviews Silver's verdict + the draft itself, writes approval (or holds with reason)
5. SEND      → only after BOTH Silver PASS (or flagged-not-blocking) AND Hale approval — executed via
               `scripts/send_d2mconcierge_email.py`, From d2mconcierge@gmail.com (corrected 2026-07-05,
               was johnloucks3 — see AMENDMENT below), never a raw unreviewed send
```

## AMENDMENT 2026-07-05 (same day) — SEND-FROM ACCOUNT + BRANDING

**Commander directive:** "Change Dani send account to d2m vs johnloucks3. ALL AI sending should be
from d2m or else we get the spam, phishing warnings." Reasoning: automated API sends from John's
personal johnloucks3 inbox risk Google's own abuse/spam detection on his personal account — a
different and more serious risk than the earlier SPF/DKIM gap that justified moving TO johnloucks3
in the first place (`SO_TP_DRAFT_ROUTING_20260620`).

**Resolution — d2mconcierge@gmail.com threads the needle:** real Gmail-hosted address (no custom-domain
SPF/DKIM/DMARC gap — avoids the iCloud-bounce problem) AND not John's personal inbox (avoids the
automation/spam-flag risk on his account). **From now on: Dani sends to Nancy/Ken FROM
d2mconcierge@gmail.com. johnloucks3@gmail.com stays CC'd for monitoring — it is never the From.**

**Formatting — Commander directive, same thread:** "no formatting came thru, HALE AI conversations
need a completely different formatting, maybe in line with the D2M logo." Every email in this pipeline
now uses the canonical D2M dark-navy branded template (`scripts/d2m_email_builder.py` wrapping
`storage/templates/d2m_canonical_darknavy.html`) — never bare/unstyled HTML again. Template includes
Dani's full signature block and the Commander's complete signature block at the very bottom (name,
title, phone, email, website, logo) per his directive: **"remember to add my complete signature block
at the very bottom. No human wants a total AI email yet."**

**Template fix (same session):** Dani's sig-block mailto was pointing at `concierge@d2mluxury.quest`
(the flagged custom domain) — corrected to `d2mconcierge@gmail.com` to match the new send-from account.
Commander's sig block was missing the `www.d2mluxury.quest` line present in his real complete signature
(`storage/signatures/commander_d2m_sig.html`) — added.

**Known gap, not yet fixed:** ~18 legacy per-TP-touchpoint template files (`storage/tp_templates/*.html`,
`storage/signatures/dani_sig.html`, `storage/d2m_gold_standard_template.html`) still reference the old
`concierge@d2mluxury.quest` mailto. The canonical template (the one this pipeline and
`d2m_email_builder.py` actually use) is fixed. The legacy files are backlog — flagged, not silently left.

**No message to Nancy/Ken skips a step.** If Silver holds, the message does not go — Hale does not override a Silver HOLD on this pipeline without Commander sign-off (this is the one place Silver's authority binds Hale directly, per his mandate as independent eye).

---

## SILVER'S CHECKLIST (before/after conditions — run every time)

**BEFORE (ground truth the draft must be checked against):**
- [ ] Every "booked/confirmed" claim traces to an actual confirmed booking (portal/TESS), not planner clutter or stale tags
- [ ] Every dollar figure traces to a primary source (GYG/PE/SS listing, verified same-session where possible) — flag, don't assert, if two sources disagree
- [ ] Addressing correct: To klyons3@bellsouth.net (Nancy), Cc kenlyons73@bellsouth.net (Ken) + johnloucks3@gmail.com (Commander monitor) — every time, no exceptions
- [ ] Voice check: third person about John & Susie ("John and Susie have/will..."), never "we"/"our" — Dani is staff, not a travel companion
- [ ] No financial commitment implied on Dani's or D2M's behalf

**AFTER (what the message puts into the world):**
- [ ] Does this email create an expectation Nancy/Ken could act on wrongly (wrong price, wrong tour, wrong date)?
- [ ] Does anything here look like a WF-17 gate is being bypassed for someone other than Nancy? (scope check)

**Verdict format:** PASS / PASS-WITH-NOTE (send proceeds, note logged for follow-up) / HOLD (send does not proceed until resolved). Silver's verdict is visible in the Hale response to Commander — never buried.

---

## NOTE — MAILBOX ROUTING (Commander flagged 2026-07-05)

This first message sent From `johnloucks3@gmail.com` (per `SO_TP_DRAFT_ROUTING_20260620` — client drafts stage/send from johnloucks3 for now, deliverability reasons). Commander noted this is "the wrong mailbox for a Dani send" in spirit — Dani doesn't yet have her own send identity distinct from the Commander's own inbox. Accepted for now, first-time exception. **Open item:** whether Dani correspondence with Nancy should eventually move to a dedicated send-as identity once domain auth (SPF/DKIM/DMARC on d2mluxury.quest) is fixed — tracked, not solved by this SO.

---

## LOG

Every message sent under this pipeline gets one line in `hale_decisions.md` under this SO's heading: date, Silver verdict, Hale approval, message ID.

**First use:** 2026-07-05, message_id `19f339fc8c58a0f7`. Silver: PASS-WITH-NOTE (Paros/Naoussa $40 vs $45 listing discrepancy, non-blocking). Hale: approved. Sent.

---

*Authored: Hale (Claude Code), per Commander directive 2026-07-05. Supersedes nothing — additive exception to SO_WF17_CLIENTSEND_PROHIBITION_20260530.*
