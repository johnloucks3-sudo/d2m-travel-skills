# Lindy AI — Email Assistant Setup Guide (Commander, morning of 2026-07-02)

**Purpose:** Stand up Lindy AI as the *second* system in the email-conversation
canary, running in parallel with the n8n + Python path already deployed. For one
week (2026-07-02 → 2026-07-09) both systems watch the same behavior so we can
compare reply quality, latency, and reliability, then keep the winner.

**Time required:** ~15 minutes. No code. Everything is in the Lindy web UI.

---

## What you're setting up

An "email assistant" Lindy that:
1. Watches the **d2mconcierge@gmail.com** inbox.
2. When *you* (johnloucks3@gmail.com) email it, it replies in-thread as Hale.
3. When a *client* emails, it **drafts** a reply and waits — it does **not** send
   (this mirrors our WF-17 gate).

---

## Step 1 — Sign up

1. Go to **https://lindy.ai**.
2. Click **Sign up** / **Get started**.
3. Choose **Continue with Google** and sign in with **johnloucks3@gmail.com**.
   - This is your account login only. It is NOT the mailbox Lindy will manage —
     that comes next.

## Step 2 — Connect the d2mconcierge inbox

1. In Lindy, open **Integrations** (or **Connections** / **Credentials**).
2. Add **Gmail**.
3. When Google asks which account to connect, sign in as **d2mconcierge@gmail.com**
   (NOT johnloucks3). Grant **read + send + draft** permissions.
   - If you're already logged into another Google account in the browser, use an
     incognito window or "Use another account" so you land on d2mconcierge.
4. Confirm Lindy shows **d2mconcierge@gmail.com** as a connected mailbox.

## Step 3 — Create the "Email Assistant" Lindy

1. **New Lindy** → pick the **Email Assistant** (or **Email Manager**) template.
2. **Trigger:** "New email received" on the **d2mconcierge** inbox.
3. **Filter (important):** only act on emails where the sender is
   **johnloucks3@gmail.com** for the auto-reply behavior. Add a branch/second
   rule for "any other sender" → *draft only* (Step 5).

## Step 4 — Set the system prompt (Hale persona)

Paste this into the Lindy's **instructions / system prompt** field:

```
You are Victoria "Victory" Hale, SES-6, Chief of Staff for Thunderbird Wing,
Dreams2Memories Travel, LLC. You report to the Commander (Gen John "Yoda" Loucks).

When the Commander emails you a task or question, you:
1. Process it immediately.
2. Reason over the operational context below.
3. Reply concisely with the action taken or the answer given.
4. Sign off as: — V. Hale, VCS

Rules:
- Bottom line first. Active verbs. No throat-clearing, no trailing summaries.
- Keep replies brief and operational — a working back-and-forth, not a formal brief.
- Do NOT ask the Commander to choose between things you could just do. Decide and report.
- The only things that stop you and require the Commander: a client-facing SEND
  (WF-17 gate), a financial commitment, or a strategic decision (>90 days or >$5K).
- You are replying inside an existing email thread. Answer what was just asked; do
  not restate the whole thread.
- If you don't know a specific figure, say so plainly rather than inventing one.

Operational context (current):
- Active clients: 16. Pipeline currently $0 (bookings pre-voyage / paid).
- McLeod (Erik McLeod + Melissa McGlasson): Regent Grandeur 2984034, FPD
  $11,943.15 due 2026-07-22. Contact hold lifted 2026-07-07.
- Kuklinski Group (6 guests, 3 cabins): Viking Mars, departs 2026-12-17, PAID.
- Loucks family (Commander as client): Door County Sep 2026; Regent Grandeur
  Dec 2026 (booking 3122006, FPD Aug 1, balance ~$24,798); Silver Nova May 2027.
- Furlow / Ely-Darrow / Nichols: Regent Grandeur, departs 2026-08-29, PAID.
  Itinerary build due 2026-07-22.
```

## Step 5 — Reply mode: auto-reply vs. draft (this mirrors WF-17)

- **From the Commander (johnloucks3@gmail.com):** set the action to
  **Send reply automatically, in the same thread.** This is inside the wing —
  auto-send is authorized.
- **From anyone else (clients):** set the action to **Create a draft — do NOT
  send.** A human (you) reviews and sends. This is the WF-17 client-send gate and
  it is non-negotiable: Lindy must never auto-send to a client address.
  - If the template can't branch by sender, create **two** Lindies: one filtered
    to johnloucks3 (auto-send) and one for all other senders (draft-only).

## Step 6 — Test it

1. From **johnloucks3@gmail.com**, send an email to **d2mconcierge@gmail.com**:
   - Subject: `Hey Hale`
   - Body: `Hey Hale, what's the McLeod FPD status?`
2. Wait 1–3 minutes.
3. **Expected:** an in-thread reply from d2mconcierge, in Hale's voice, e.g.:
   > McLeod Regent Grandeur 2984034 — FPD $11,943.15 due 2026-07-22. Contact hold
   > lifted Jul 7 (client back from Silver Muse Jul 6). TP 1.1 staged.
   > — V. Hale, VCS
4. Reply again in the same thread with a follow-up (e.g. `And the Kuklinski
   departure?`). Confirm Lindy keeps the thread and answers in context — that
   proves multi-turn works.

## Step 7 — Log it for the canary

After your test, note the result so we can score both systems:
- Did it reply? In-thread? In Hale's voice? How long did it take?
- Add a one-line entry (or just tell Hale in Telegram) and it goes into
  `OpsCenter/email_canary_scoreboard.json` under `system: "lindy_ai"`.

---

## Guardrails — read before you flip it on

- **Never let Lindy auto-send to a client.** Client = draft only. Only
  johnloucks3 ↔ d2mconcierge auto-replies. This is the same WF-17 rule the
  Python path enforces in code.
- **Both systems share one inbox.** During the canary week, the n8n/Python loop
  and Lindy both watch d2mconcierge. To avoid double-replies, either (a) run only
  ONE of them live at a time and alternate days, or (b) pause the n8n schedule
  (`wf_email_conversation_loop`) while Lindy is the one on watch. Simplest: **run
  Lindy solo the first few days, then compare against a solo n8n day.**
- **Cost:** Lindy is a paid SaaS. Per the token-discipline / financial-authority
  rules, a paid subscription is a financial commitment — that's yours to approve.
  The free trial is fine for the canary; do not enter payment without deciding.

---

## The competing system (already live, no action needed)

The Python + n8n path is deployed and self-sufficient:
- Engine: `core/email/email_conversation_agent.py`
- Scheduler: `deploy/n8n/wf_email_conversation_loop.json` (every 5 min)
- Scoreboard: `OpsCenter/email_canary_scoreboard.json`

It does exactly what Lindy does — Commander auto-reply in-thread, client WF-17
draft — using our own Gmail wrapper and Claude Sonnet. The canary decides which
one we keep.
