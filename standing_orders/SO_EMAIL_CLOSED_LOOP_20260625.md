# SO — EMAIL CLOSED-LOOP RESPONSE DOCTRINE
**Standing Order · 2026-06-25 · Commander John Loucks**
**Author:** Victoria "Victory" Hale, VCS — capturing Commander's verbatim intent

---

## COMMANDER'S VERBATIM REQUIREMENT (recorded 2026-06-25)

> "Give me the entire process from the time that an email from me hits the D2M inbox.
> I want to have assurance that what a directive gets done, what questions I asked get
> answered back, and that anything I send as a CC gets acknowledged and if there's an
> action needed to be done that it gets done. I also want my words to be recorded from
> this conversation because I am tired of saying what I want — somehow in computer
> language it needs to persist so that if there is another problem I can simply refer
> you back to the guidance."

---

## THE DOCTRINE (binding on all Wing instances)

### 1. DIRECTIVE (Commander sends to d2mconcierge with COS:/HALE: prefix)
- **Wing receives** → classifies as DIRECTIVE → creates P1 mission board entry
- **Wing executes** → routes to appropriate persona/agent for execution
- **Wing confirms back** → email reply to johnloucks3: "Done. [What was done]. [Where it landed]."
- **If blocked** → email reply stating the specific blocker and what Wing needs
- **No silent completions.** Every directive gets a completion email. No exceptions.

### 2. QUESTION (Commander asks something in email)
- **Wing receives** → classifies as QUESTION → dispatches to Wing agent for research
- **Wing answers back** → email reply to johnloucks3 with the answer
- **If uncertain** → states confidence level and what would resolve it
- **No silent reads.** Every question gets an answer email.

### 3. CC (Commander CCs d2mconcierge on a client send or external email)
- **Wing receives** → classifies as CC → acknowledges via email reply to johnloucks3
- **If action needed** → Wing executes + confirms back
- **If information only** → Wing acknowledges: "Logged. [What was noted]. [Where filed]."
- **No silent CCs.** Every CC gets an acknowledgment email.

### 4. INFORMATION FORWARD (Commander forwards article/news, no directive)
- **Wing receives** → classifies as INFORMATION → saves to intel/ + indexes in Qdrant
- **Wing confirms** → email or Telegram: "Saved to intel/[filename]. [One-line synthesis]."

---

## CLASSIFICATION MATRIX

| Commander writes to d2mconcierge | Wing classifies as | Wing does |
|---|---|---|
| `COS:` / `HALE:` + instruction | DIRECTIVE | Execute + email confirmation |
| `?` in body or "what", "how", "why", "can you", "find out" | QUESTION | Research + email answer |
| No prefix, forwarded CC email with no instruction | CC | Acknowledge + dossier update |
| Article/newsletter forward, no instruction | INFORMATION | Intel file + Qdrant index |
| Plain send, no prefix, no question | (exclude) | Self-loop prevention |

---

## CONFIRMATION EMAIL STANDARD

Every confirmation email back to Commander follows this format:

```
Subject: ✅ [Done/Answered/Logged]: [original subject shortened]

[What was received]
[What Wing did — specific, not vague]
[Where it landed — file path, mission ID, dossier section]
[Any follow-on action required from Commander — or "No action needed"]

— Hale · Thunderbird Wing · [timestamp]
```

**No trailing questions seeking permission.** The confirmation is terminal.
**No email rethreading back to the original sender.** Confirmations go to johnloucks3 only.

---

## WHERE THIS RUNS

- **Script:** `scripts/d2m_commander_digest.py` + `core/email/thunderbird_commander_inbox.py`
- **Timer:** `thunderbird-inbox-sweep.timer` (every 2 min on johnloucks3) + `d2m_commander_digest.py` (periodic on d2mconcierge)
- **Execution agent:** `OpsCenter/dispatch_and_email.py` (Wing agent dispatch)
- **Confirmation channel:** Email to johnloucks3 + Telegram

---

## REFERENCE — for future sessions

If a future Wing instance asks "what should happen when Commander emails d2mconcierge?", point it to this file. The answer is: **closed loop, always. No silent reads, no silent completions.**

*SO authored: 2026-06-25 · Victoria "Victory" Hale, VCS · Thunderbird Wing*
