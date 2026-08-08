BLUF: Commander wants two new KAIZEN intake features — (1) a Dani-voice
orientation intro on the form explaining what CC/OC/AG each offer, framed as
"your own personal consultants," for first-time staff users who know nothing
of the Wing; (2) an email reply loop — ticket answer emails to the submitter
(cc Commander), and a follow-up reply from them becomes a new ticket
automatically. He called this "a revolutionary capability" and wants an RT
position paper from all 3 seats plus a build plan shown on screen before any
execution — no self-execute past the plan stage.

## Ground truth already on disk — do not re-derive, build on this

**A near-identical two-way loop already exists and encodes the exact security
lesson this design must inherit:** `core/email/email_conversation_agent.py`.
Read it before proposing anything. Its hard constraint, verbatim from its own
docstring: **two structurally-separate send paths, no shared send function** —
Commander gets `gmail_reply_in_thread()` (auto-send, guarded to Commander
addresses only); anyone else gets `gmail_create_draft_sync()` (draft ONLY,
never auto-sent, Commander reviews+sends manually); unknown sender = default
deny (draft-or-skip, never auto-send). Threading uses the RFC822 `Message-ID`
header, not the Gmail API message id, so In-Reply-To/References nest right.

**`OpsCenter/email_task_ingest.py` is a PROTECTED FILE** (standing order
SO_EMAIL_SCANNER_PROTECT_20260608, do-not-modify without explicit Commander
authorization). Do not propose editing it. The new KAIZEN reply-loop must be
a new, separate listener/script that follows `email_conversation_agent.py`'s
PATTERN, not a change to that file.

**Who "any user (but me)" actually is matters for the security model.** Per
this session's own prior work, the intake form is Basic-Auth gated with a
SHARED password the Commander is handing to staff (Dani, Sterling, etc.) —
not the general public, not clients. That's a materially different trust
tier than `email_conversation_agent.py`'s "client / anyone else" bucket
(which drafts-only, never auto-sends). Staff with the shared password are
trusted enough to submit tickets and get real answers — but are they trusted
enough for AUTO-SEND of an AI-generated reply straight to an arbitrary email
address they typed into a form themselves? That's the central judgment call
this RT needs to resolve, not assume either way.

## Questions for the design (answer these explicitly, don't skip)

1. **Onboarding copy (Dani's voice):** Dani is D2M's client-voice/products
   persona (Maj. Danielle Moreau) — warm, direct, non-corporate, "friends I'd
   serve for free" mission ethos. Draft the actual intro copy for the form,
   explaining in plain language: what CC (Claude, judgment/build/synthesis),
   OC (DeepSeek, $0 free-tier build/ops), and AG (Gemini, independent-engine
   verification/research/creative) each bring — "like your own personal
   consultants," per the Commander's own framing. Keep it short — this sits
   above a web form, not a memo.
2. **Auto-send vs draft for the reply-loop:** given the trust-tier point
   above, recommend auto-send-to-submitter-cc-Commander vs draft-for-Commander
   -review-first, with your reasoning. If you recommend auto-send, name the
   abuse scenario that worries you most and how the design should close it
   (rate limit? require gates=[] only? Commander-visibility alert, like the
   one just shipped for mismatched submitter identity?).
3. **Follow-up-becomes-new-ticket mechanics:** how does an inbound reply get
   detected and turned into a new `build_cc_task()` ticket without touching
   the protected `email_task_ingest.py`? What identifies "this is a reply to
   a KAIZEN ticket thread" vs. an unrelated email arriving in the same inbox?
   (Message-ID threading, a subject-line tag, a dedicated inbox/alias?)
4. **What's the smallest safe first version?** Given "revolutionary
   capability" excitement, name what to explicitly NOT build in v1 (e.g.
   multi-hop follow-up chains, non-staff/external submitters, elevated-gate
   tickets via email) so the plan doesn't overreach on the first pass.

Write your own position-paper card. I'll synthesize all three (cross-checked
against real files/commits, same discipline as the point-paper compile
earlier today) into one document, plus a build plan shown on screen — no
execution starts until the Commander approves that plan.
