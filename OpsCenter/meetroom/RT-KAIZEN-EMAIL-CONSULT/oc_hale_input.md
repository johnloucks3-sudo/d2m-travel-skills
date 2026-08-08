⚡ Wilco — Reading ground-truth files before writing my RT card.

Reading the annotated loop, the protected ingest file (read-only), and the task template layer to ground feasibility claims in actual repo
Reading the gmail send-path guards + locating the existing KAIZEN intake form and ticket infrastructure, since my feasibility claims depend on what's actually wired.
The intake server and runner already exist — that changes my feasibility picture. Reading the intake server's exact form/env/write behavior and the reply-in-thread guard before I write the card.
⚡ Done — ground truth loaded. Writing my RT card now.

All three seats' cards cross-check against real files; here is mine.

---

# HALE-OC Position Paper — KAIZEN Email Reply Loop & Form Intro
**RT-KAIZEN-EMAIL-CONSULT · Seat: OC (Jet/DeepSeek) · Reads: `email_conversation_agent.py`, `email_task_ingest.py` (PROTECTED, read-only), `task_templates.py`, `kaizen_intake_server.py`, `thunderbird_gmail.py` reply/draft guards.**

## BLUF
Both features are buildable **this session** by reusing existing non-protected plumbing — the pattern (two structurally-separate send paths, RFC822 Message-ID threading, draft-vs-send by trust tier) and all four KAIZEN bricks (`build_cc_task`/`write_ticket`/`read_open_tickets`, intake server, runner, report) already exist. The one real design decision is Q2, and my answer is: **draft-first for the initial answer, auto-send ONLY the follow-up, and never auto-send to an address the loop hasn't seen reply back from.** The follow-up loop is the *safe* auto-send; the initial answer to a form-typed address is the *unsafe* one.

---

## Q1 — Onboarding copy for the form (Dani's voice)

Concept: sits above the form, under a `⭐ Your own team of travel-AI consultants` eyebrow. For first-time staff who've never heard of the Wing. Short, no jargon, warm, "friends we'd serve for free" register.

> **You've got three consultants on call — and they're all yours.**
>
> Every ticket here lands with three welcome seats you get to pick from, depending on the job:
>
> - **CC (Claude)** — the judgment seat. Big builds, careful reasoning, writing that needs a real voice behind it. The one you ask when it has to be *thought through*.
> - **OC (DeepSeek)** — the $0 workhorse. Ops, scripts, running the routine that keeps this Wing turning — the fastest, never a watt of cost.
> - **AG (Gemini)** — the second pair of eyes, the deep researcher, the creative spark. The independent look that catches what the first pass missed — and the one who reads the miles of docs so you don't have to.
>
> Leave the "who should do it?" box to us if you're not sure — you're not signing for a stranger, they're your team. Fire off the ticket, and one of us picks it up and gets back to you here.
>
> *(Not sure what "elevated gates" means on the form? Leave it blank — comfort zone vs. zoom. That's exactly what we'd hope you'd do.)*

Kept it to ~140 words. The seat descriptions are honest to this session's actual model economy (OC `$0`, AG Google-billed, CC the judgment lane) — not embellishment.

## Q2 — Auto-send vs. draft for the reply loop

**Recommendation: TWO tiers, no single answer.** Don't propagate the dichotomy "auto-send whole thing or draft whole thing" — the loop has two different directions with two different risk profiles:

- **The initial answer to the submitter (to their self-typed address, cc Commander): DRAFT ONLY in v1.** `gmail_create_draft_sync()` → Commander click → actually. This preserves the WF-16 discipline that governs the entire existing pipeline. Reason: `auto-reply-in-thread` hard-blocks any non-Commander `to` (thunderbird_gmail.py:2422), and no function in this repo auto-sends AI text to a non-Commander address. Breaking that invariant on a "revolutionary" push — creating an auto-send path to an *arbitrary address typed into a form* — is the one-in-theamage move; and the loop functions identically with a draft in v1. The revolution (a reply from them becomes a new ticket) needs zero sending; it needs listening.
- **The follow-up answer (back to the thread we know a real person already replied from):** this is where auto-send is genuinely safe and should be on from day one. The thread address, a person by replying from their, — proof-by-return-path that this box exists, this person holds this thread — which is materially stronger Evidence than anything in the submit form. This is the "closed-loop" feel the Commander calls revolutionary: ticket → answer → their reply → new ticket → answer, no babysitting.

**Abuse scenario that worries me most (if anyone argues all-auto-send):** shared password holder submits a ticket with a *fake* `email` field pointing at any third party; auto-send fires an AI email to that address. Worth — a machine letter from concierge@d2mluxury.quest to a stranger's inbox, unbeknownst to the Commander. This is a **relay/impersonation vector** that does not exist today (drafts physically can't leave Gmail without the Commander). **Closures, if auto-send is authorized anyway:** (1) auto-send only when `From` of the inbound == `ticket[submitted_email]` exactly (identity match, the same test the intake form already runs at creation); (2) `gates==[]` only — no elevated-scope tickets ever auto-send; (3) rate cap (e.g. 3 auto-replies per ticket, 10/hr process-wide window); (4) reuse the existing intake-silencer — a `NOW`-urgency Commander-following Telegram on every auto-send with the body in it (mirror of `_looks_like_commander()` — the mismatched-submitter alert we already ship, kaizen_intake_server.py:180). And the fact that a follow-up-answer line begins at "the safe leg" and any auto-reply will never be answer #1.

**An aside, labeled opinion** — I'd push the Commander strongly that even the "revolutionary" feel is preserved under draft-first for the initial answer. One click. The revolution is the loop, not the send latency. This is the same discipline that let `email_conversation_agent.py` keep its two-path structure without ever relaxing it. Don't invent a precedent under enthusiasm.

## Q3 — Follow-up → new ticket mechanics (my lane)

**Fully buildable this session; zero changes to protected `email_task_ingest.py`.**

- **New standalone script `core/email/kaizen_email_loop.py`** — same poll pattern as `email_conversation_agent.py` (reuse its *read-side* helpers freely: `fetch_unread`, `_strip_quoted_reply`, `_extract_addr`, `mark_read` — it is NOT protected; custom MODULE is separate). NO shared send function — write-side uses `gmail_create_draft_sync()` only. New reader installed as a systemd user timer vs `kaizen_monitor`, mirroring in 2-min-tick cadence of the ingest the protocol leaves alone.
- **Detection — subject tag is the primary key, RFC822 state secondary.** When the initial answer email goes out, the subject line about the entity gets a deterministic tag: `[KAI-<ticket_id>]` (e.g. `[KAI-kzn-20260808100000-abc123] Your ticket: ...`). The listener needs only an O(1) match: strip `Re:/Fwd:`, look for `KAI-<ID>` in the subject; not found → **whole-we skip** (never a new ticket). The tag is the cheapest, most disambiguation-strong identifier and needs no lookup. Residual reference in state (do not pick):
- **Corroborate with sender check**: the ticket's `submitted_email` must equal the reply `From`. That filters "someone else replies to our inbox with a spoofed KAIZEN subject" — an alert, not a ticket.
- **New ticket construction** (`build_cc_task` + `write_ticket`, both live in the unprotected `task_templates.py`):
  - `seat` = **same as parent ticket** (no seat-changing by email, submitter didn't pick in a reply).
  - `verify_step` = **parent's existing** (passed our `is_checkable` gate once; reuse it — can't extract a new checkable line from email reliably).
  - `gates` = parent's — **actual `[]` for follow-ups is not assumed**, need the parent's actual file; remember to top: carry with it.
  - `spec` = stripped follow-up body (use `_strip_quoted_reply`), prepended with `CONTEXT (follow-up to <parent_id>, submitted: <ticket>)` so the executing engine has parent context without a lookup — and note `:` `.md` at `origin: kaizen-email-reply` + `parent_ticket_id` fields (the schema is `build_cc_task`-written file; adding two keys at write is a safe patch — no edits to existing files).
  - **Require-checkable=True** (programmatic caller → strong gate; the intake server's `require_checkable=False` is a human-passing carve-out, wrong for a machine).
- **No auto-answer to Commander as new ticket unless the reply itself is a fresh ask.** The loop-only responds to this ticket thread — a direct requirement; otherwise unrelated mail landing in d2mconcierge (conf / unread) is never turned into tickets.
- `state`/`_processed_ids` — same bounded dedup pattern as `email_conversation_agent.py`.

**On "dedicated inbox or alias":** skip it for v1. Ethically, the single `d2mconcierge` inbox + subject-tag is the robust discriminator; creating a new alias/inbox is a Drive/Gmail-infrastructure increment you don't need to build to close the loop. The dedicated inbox only matters if unread-functional ambiguity gets garbage-heavy later — keep as a later allow; don't build it now.

## Q4 — Smallest safe v1 (NOT-build list)

The talent is already impressive without these; they are noise that defeats the safe subset:

1. **No multi-hop chains.** A reply-to-a-reply-to-a-reply is *not* flattened/nested within v1 handling: support exactly one hop (original parent ticket + one follow-up = one new ticket). Every later reply in the same thread creates a **flat** new ticket pointed at the current parent — no chain resolution.
2. **No elevated-gate tickets / email gate changes.** Gate editing is impossible from email; `gates` come from the form and are inherited read-only. An email saying "NOW >$5K" changes nothing.
3. **No external submitters.** Loop only converts tickets whose submitter is already a trusted holder of the password AND whose reply `From` matches a ticket's recorded `submitted_email`. No strangers, ever.
4. **No auto-completion of the parent ticket.** A follow-up arrival is not "done" — the parent stays exactly as it is until a human *reported* or closed child/doesn't touch status. Anti-theater discipline.
5. **No attachments / non-text reply bodies.** The loop strips content and tickets only the plain-text reply (existing `_strip_quoted_reply` handles this).
6. **No new inbox/alias infrastructure.** Single existing inbox + deterministic subject tag, per Q3.
7. **No seats beyond CC-by-parent (the follow-up's executing seat is inherited)** in v1.

**Resulting v1 = 3 files, all added, zero compiled protected/enumeration edits:** `kaizen_intake_server.py` gets the intro-copy block above a new span (its only edit — and it's not in the protected list), `core/email/kaizen_email_loop.py` added as the listener, and its systemd timer/unit file. Reuse the draft-zero module to `gmail_create_draft_sync` and the runner exists today on `OpsCenter/tickets/`. That's a half-framework-session build, plan on one screen, Commander-approve, execute.

`— HALE-OC (DeepSeek v4), Round Table card`
