# WF-17 NAMED WAIVER EXPANSION — Plan (T3, issues stated)
**Date:** 2026-07-06 · **Gate:** Commander Decision (Gate 4) · **Status:** DRAFT — awaiting approval, not implemented

**Directive:** Add Bryana Jarboe, Kim Westbrook, Stefanie Burcham, and Susan Loucks to the WF-17 waiver, alongside the existing Nancy Lyons exception — Dani/Hale send directly, no per-email Commander gate.

---

## 1. WHAT ALREADY EXISTS (don't rebuild it, extend it)

- **Nancy Lyons** — live exception (`SO_LYONS_WF17_EXCEPTION_PIPELINE_20260705`): Dani sends directly from d2mconcierge, johnloucks3 CC'd every message, Hale+Silver review every draft before send, third-person voice. This is the template.
- **Susan Loucks (susanna.loucks@gmail.com)** — already partially cleared: SO 2026-06-10 treats her as a **Wing-internal address**, no gate, for internal comms. But a **carve-out exists**: SO 2026-06-18 keeps "Loucks personal trip as D2M client" emails on WF-17, johnloucks3-only, specifically excluding susanna.loucks from that one lane. **This directive and that carve-out now overlap — flagged below as Issue 4, needs your call, not mine.**
- **Bryana, Stefanie, Kim Westbrook** — currently documented elsewhere as "guinea pig" test relationships with an explicit standing rule: *"WF-17 preserved... unless Commander waives per-send."* This directive IS that waiver, for all three, named and durable rather than per-send.

---

## 2. GENERALIZED MECHANISM (one build, five names)

Extend the Lyons pipeline into a **named-waiver allowlist**, not five separate one-offs:

- `config/wf17_named_waivers.json` — the list. Adding a name here is the ONLY way to bypass WF-17; nothing else does. Sterling's finding from the earlier AgentMail exercise applies exactly here too: **an inbox or address is not send authority — only a name on this file is.**
- Send path (Dani or Hale) checks this file before any send. Not on the allowlist → drafts and holds, exactly like every other client, no exceptions, no judgment call at send time.
- Every waived send still carries: CC johnloucks3 (monitoring substitute for your click), Hale+Silver draft review before send, third-person voice discipline, and a provenance stamp (waiver name + date) logged to `hale_decisions.md`.
- Metric (Sterling's ask, same as the C2 Fabric exercise): `unwaivered_sends` — target zero, checked at the guard, not weekly.

This is a half-day build: one config file, one guard function, wired into the existing Dani send path. Not five separate builds.

---

## 3. ISSUES — STATUS AFTER COMMANDER INPUT (2026-07-06, same session)

**Issue 1 — RESOLVED.** Kim Westbrook's email confirmed: `crnakim@yahoo.com`. Updated in `dossiers/Westbrook_Brent_Kim_UPDATED.md` with source citation. Also noted per Commander: she books her own travel via Interline/Perx (airline-family + hospital perks) — channels D2M doesn't have access to. Relationship is advisory/pro-bono, not a transactional booking pipeline — this shapes what Dani would actually be corresponding about (trip ideas, planning help, NOT fare/booking transactions D2M can't execute anyway).

**Issue 2 — REFRAMED, not a concern anymore.** Commander correction: **Stefanie, Kim, and Nancy are friends and family, not sales prospects** — the "prospect tone risk" I flagged doesn't apply because there's no sales motion here at all. Specifics that change the picture:
- **Stefanie** — Commander's sister, and **she is herself a travel agent, affiliated with Nexion.** She's a peer in the industry, not a lead. Correspondence with her is professional-peer + family, not concierge-to-prospect.
- **Kim** — self-books via Interline/Perx (see Issue 1), close to Rondo, "almost family." D2M's role is advisory only.
- **Nancy** — books through her own travel partner, a friend in the industry. Same shape as Stefanie: peer + friend, not a funnel.
This actually *lowers* risk versus my original framing — there's no "convert the prospect" pressure that could push tone in a wrong direction. Dani's voice for all three should read as **friend/peer**, not **concierge selling a product**.

**Issue 3 — CONFIRMED by Commander ("Agree").** Bryana and Susan run on the Hale-direct-voice track. Nancy, Kim, and Stefanie stay on Dani's track (per existing Lyons precedent and the friend/peer reframe above). Same allowlist mechanism, two voices.

**Issue 4 — Commander wants further exploration + recommendations. Here they are:**

The SO 2026-06-18 carve-out (Loucks-trip-as-D2M-client emails → johnloucks3 only, excluding Susan) has no stated rationale on file beyond "that's how the waiver was scoped" — I checked the original decision record (`docs/superpowers/specs/2026-06-19-hale-autonomy-authority-map-design.md` PL-004/PL-006) and found no documented reason (no "surprise" logic, no explicit privacy concern — it reads as simply narrow-scoped to the account owner at the time).

**Recommendation A (narrower, matches "used to be in the wing" literally):** Treat today's directive as *reaffirming and formalizing* Susan's existing SO 2026-06-10 Wing-internal status — general correspondence, Wing-adjacent business she's involved in — onto the same named-waiver list for consistency and auditability. Leave the SO 2026-06-18 carve-out untouched: emails specifically about John & Susan's own trips as D2M clients still route to johnloucks3 only. Two scopes, no conflict, nothing lost. **This is my recommendation** — it does exactly what "used to be in the wing" describes (restore/formalize her Wing role) without touching a separate, deliberately-scoped rule that wasn't part of today's ask.

**Recommendation B (broader):** If you actually want Susan to also receive your joint trip lifecycle emails directly (not routed through you first), that's a real amendment to PL-004/SO 2026-06-18 specifically — a separate, explicit decision, not a side effect of this waiver. I'd want that stated on its own, since it changes who sees your shared trip planning first.

Recommend A unless you tell me otherwise — B is available if that's actually what you want.

**Issue 5 — RESOLVED. Vendor review complete, real findings, not a guess:**
- **SOC 2 Type II compliant** — 93 documented controls (security, availability, processing integrity, confidentiality, privacy), audited Aug–Nov 2025, full report available under NDA via their trust center (trust.delve.co/agentmail).
- **Published subprocessor list** (agentmail.to/legal/subprocessors, updated Jun 2026): AWS (infra), Svix (webhooks), Clerk (auth), Stripe (billing), PostHog (analytics), Vercel (hosting), Google/Slack (internal comms), Plain (support) — all named, reputable, US/EU-hosted.
- **DPA exists**, referenced as part of the binding Agreement in their ToS.
- **GDPR rights supported** — access, deletion, portability, rectification, on request to support@agentmail.cc.
- **One real gap found, not glossed over:** their published retention policy is boilerplate ("as long as necessary") — no fixed retention period stated for email content specifically. **Sent a direct question to support@agentmail.cc just now** (2026-07-06) asking for: (1) the specific retention period for message content/attachments, (2) whether a Free-tier account can get a signed DPA, (3) whether email content is used for training/analytics beyond delivery. Awaiting reply — will land in `hale-thunderbird@agentmail.to` and surface via the real-time listener already built.

Net: this is a real, audited, SOC2-Type-II vendor with a published subprocessor list — a materially different risk picture than "zero operational history," which was accurate for *our* usage history, not the vendor's own security posture. The one open item (exact retention period) is in flight, not blocking.

---

## 4. WHAT DOESN'T CHANGE
- Everyone NOT on the named-waiver list stays fully WF-17 gated — no drift, enforced in code per Sterling.
- Financial commitment and Strategic (>90d/$5K) gates are untouched — this is a client-send gate waiver only.
- Bryana's separate ask (Wing-resources instruction manual, Hale-direct access) proceeds regardless of how Issue 3/4 resolve — it's not contingent on the WF-17 mechanism.

---

## 5. GATE 4 — YOUR CALL
All 5 issues now resolved or have a stated recommendation. Only Issue 4 (Susan's carve-out) still needs your explicit pick: **Recommendation A (narrower, my default) or B (broader)**. Everything else — Kim's email, the friend/peer reframe, the Bryana/Susan Hale-voice split, the vendor review — is settled and ready to build.

Say the word (and A or B for Susan) and I build the allowlist mechanism + wire all five in this session.
