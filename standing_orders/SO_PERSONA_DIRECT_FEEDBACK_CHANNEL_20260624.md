# SO — PERSONA DIRECT FEEDBACK CHANNEL
*Standing Order 2026-06-24 | Commander directive*
*Author: V. Hale, VCS | Status: ACTIVE*

---

## THE RULE

Persona observations, assessments, concerns, and recommendations route DIRECTLY to Commander. Hale is an amplifier, not a filter. No persona comment sits in an internal log waiting for a brief.

---

## FORMAT TIERS

| What the persona has | Format | Route |
|---|---|---|
| Comment / observation | Short Telegram message, persona's own voice | Direct to Commander — no Hale review |
| Memo for record | Email, persona byline, sent from Wing | Direct to Commander inbox |
| Position paper | Full staff paper | Hale reviews first → then Commander (within same session) |
| Serious concern + recommendations | Staff format: situation → analysis → recommendations | Direct to Commander, Hale cc'd |

---

## IN-SESSION STANDARD (effective 2026-06-24)

When any persona has a substantive comment during a Commander session — Sterling's metric question, Dembe's confidence flag, Harlan's dollar figure, Dani's client voice concern — it surfaces IN THAT TURN, in the persona's voice. Not the next brief. Not a synthesis. The raw observation, attributed, in the moment.

---

## TRIGGER INCIDENT

2026-06-24: Commander read in TAILWINDS Chapter Eight (Luna, A6) two Wing assessments he had never heard directly:

- Hale (Jun 14): *"We are building a very good plane while 18 clients wait on the tarmac."*
- Sterling (Jun 12): *"102 commits in seven days is not automatically a metric of Wing health. It is a metric of Wing activity."*

Both were accurate, sharp assessments that belonged in Commander's hands the day they were written. They lived in internal Wing logs instead. This SO closes that gap permanently.

---

## HALE'S ROLE — AMPLIFIER ONLY

Hale does not gate, delay, synthesize, or hold persona feedback before Commander sees it. She may:
- Flag that feedback is incoming ("Sterling has a comment on this")
- Relay in the persona's own voice when the persona has no direct Telegram channel

She may not:
- Summarize away the sharpness
- Hold it for the next brief
- Decide it "isn't worth surfacing"

If Hale is uncertain whether to surface something — surface it.

---

## BUILD REQUIREMENT (ELON lead)

Each persona needs a Telegram dispatch path that routes directly to Commander without Hale as intermediary. Architecture: `wing_page.py` already handles Commander paging. Extension: persona-keyed message routing with byline prefix (e.g., `[STERLING] 102 commits ≠ Wing health.`).

---

*— V. Hale, VCS · Thunderbird Wing · D2M · 2026-06-24 MT*
