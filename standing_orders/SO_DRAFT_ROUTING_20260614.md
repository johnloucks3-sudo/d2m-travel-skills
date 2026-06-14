# STANDING ORDER — EMAIL DRAFT ROUTING & ACCOUNT DISCIPLINE
## SO-DRAFT-ROUTING-20260614 · Issued: 2026-06-14 · Commander: John "Yoda" Loucks
## Authored by: Victoria Hale, SES-6 (COS) · Supersedes: informal 2026-06-04 rule

---

## AUTHORITY

Commander directive. Binds ALL Wing instantiations: Claude Code, OpenCode, Telegram/DeepSeek, headless spawns, all agents and personas. No exceptions.

---

## THE RULE — THREE CASES, NO AMBIGUITY

### Case 1 — Internal Wing communications (reports, briefs, intel, staff papers)
**Action: DIRECT SEND to johnloucks3@gmail.com. No draft step. No gate.**
This is within-Wing communication. The Commander's inbox is the delivery point.
Examples: morning briefs, EOD reports, incubator digests, intel sweeps, sitreps, staff papers, commission reports, overnight ops logs.

### Case 2 — Client-facing products (itineraries, validation emails, proposals, lifecycle TPs)
**Action: DRAFT in d2mconcierge. Label: THUNDERBIRD-Commander-Review. WF-17 gate. Commander sends.**
The Wing drafts. The Commander reviews. The Commander sends. Always.
Never use johnloucks3 for client drafts. Never send from any account without Commander approval.

### Case 3 — Draft to johnloucks3 (Commander's personal review before sending as John)
**Action: DRAFT in johnloucks3. Label: WING-PERSONAL-DRAFT. ONLY on explicit Commander OK.**
Explicit signals: "draft to johnloucks3" / "put in my drafts" / "I want to review before sending" / "OK to draft to johnloucks3" or similar unambiguous language.
Without explicit Commander OK → default to Case 1 (direct send) or Case 2 (d2mconcierge draft), never create a johnloucks3 draft silently.

---

## ROUTING TABLE — QUICK REFERENCE

| Product type | Draft account | Label | Send authority |
|---|---|---|---|
| Internal brief / report / intel | ~~draft~~ → **DIRECT SEND** | — | Wing sends |
| Client-facing product | d2mconcierge | THUNDERBIRD-Commander-Review | Commander only |
| Personal email, Commander review requested | johnloucks3 | WING-PERSONAL-DRAFT | Commander only |
| susanna.loucks@gmail.com (internal) | — | — | Wing may send directly (SO 2026-06-10) |

---

## WHY THIS EXISTS

**Original 2026-06-04 trigger:** Claude Code desktop created drafts in johnloucks3 that went unread — the draft folder is not monitored. Briefs and intel sat in drafts, never reaching the Commander. The fix was a hard default: internal comms = direct send, always.

**2026-06-14 amendment:** Restored draft capability for the one legitimate use case — when the Commander explicitly wants to review an email before it sends from his personal account. The gate is explicit Commander language, not inference.

**The failure mode this prevents:** Silent drafts accumulating in johnloucks3 that look like deliveries but are never seen. "Direct send or explicit draft — nothing silent" is the principle.

---

## ENFORCEMENT

- Every Wing instantiation carries this rule. No persona may create a johnloucks3 draft without the explicit Commander signal.
- AGENTS.md Hard Rule #1 references this SO.
- CLAUDE.md "Email Routing" table references this SO.
- Sterling audits at Sunday Baldrige sweep: any johnloucks3 draft created without WING-PERSONAL-DRAFT label = violation.
- Hale logs any exception invocation in `hale_decisions.md`.

---

## REFERENCES

- SO_EMAIL_RULES_UPDATE_20260530.md — full email routing and signature standards
- SO_WF17_CLIENTSEND_PROHIBITION_20260530.md — WF-17 client send gate
- `AGENTS.md` Hard Rule #1 (amended 2026-06-14)
- `memory/feedback_johnloucks3_no_drafts.md` — condensed rule for memory system

---

*SO-DRAFT-ROUTING-20260614 · Effective immediately · All 8 Hale instantiations · All Wing agents*
