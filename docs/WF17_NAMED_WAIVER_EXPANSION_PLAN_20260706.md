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

## 3. ISSUES STATED — per name, real, not smoothed over

**Issue 1 — Kim Westbrook has no contact info on file.** Her dossier (`dossiers/Westbrook_Brent_Kim_UPDATED.md`) shows email as `[TBD]` for both Kim and Brent. **The waiver can't function without an address.** Either you have it and it needs to go in the dossier, or this one waits on that first. Not a policy question — a data gap.

**Issue 2 — Stefanie Burcham is a prospect, not a booked client, and she's your sister.** Two things stack here: (a) sending "client product" style emails to someone with no active booking risks a sales-y tone that doesn't fit a prospect relationship; (b) she's family — the highest reputational stakes of the five names. Staff (Dani, in the earlier consult) recommended keeping her fully reviewed regardless of waiver status — not blocking the waiver, just flagging that "waived" shouldn't mean "less careful" for this one specifically.

**Issue 3 — Bryana and Susan may not fit the "Dani client-voice" track at all.** Nancy, Kim, and Stefanie are travel-concierge relationships — Dani's lane. Bryana (gift-tier friend, building her own travel business, uses Hale directly per your own framing) and Susan (family, "used to be in the wing," already has internal-address status) look more like a **Hale-direct-access track** than a Dani-client-voice track. Putting all five under one identical mechanism may be forcing two different relationship shapes into one box. **Recommend:** the WF-17 allowlist mechanism is shared (same file, same guard), but Bryana/Susan's correspondence runs through Hale's voice, not Dani's — same safety rail, different voice, matching how each of them actually uses the Wing.

**Issue 4 — Susan Loucks has an existing carve-out that conflicts with this, and only you can resolve it.** SO 2026-06-18 explicitly reserves "Loucks personal trip as D2M client" emails to johnloucks3 only, excluding susanna.loucks from that one lane — meaning if Susan books/travels as a D2M client alongside you, that specific correspondence stays gated to your inbox by design, not hers. **Question for you:** does this new waiver apply to Susan's general correspondence (family/friend coordination she handles) while the Loucks-trip carve-out stays intact underneath it? Or does this waiver supersede that carve-out entirely? I can't determine your intent here — this is the one place in this plan where I'm asking rather than deciding.

**Issue 5 — Vendor review still owed, now more relevant.** Dembe's finding from the earlier AgentMail consult stands: no security/DPA review has been done on AgentMail, and this waiver expansion means more real PII (five people, not one) flows through a service integrated same-day. ELON's answer: this is a 20-minute ask (AgentMail's own ToS/security page + a direct support question on retention/subprocessors), not a delay — running in parallel with the build, not blocking it.

---

## 4. WHAT DOESN'T CHANGE
- Everyone NOT on the named-waiver list stays fully WF-17 gated — no drift, enforced in code per Sterling.
- Financial commitment and Strategic (>90d/$5K) gates are untouched — this is a client-send gate waiver only.
- Bryana's separate ask (Wing-resources instruction manual, Hale-direct access) proceeds regardless of how Issue 3/4 resolve — it's not contingent on the WF-17 mechanism.

---

## 5. GATE 4 — YOUR CALL
Approve as written / Approve with Issue 4 resolved one way or the other / Revise / Hold Kim until contact info exists but approve the other four now.
