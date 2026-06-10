# Loucks Client Test — AAR Folder
## Guinea Pig Program · Dreams2Memories Travel · Active from 2026-06-10

---

## Mission
John & Susie Loucks are being treated as full D2M clients for their Silver Nova Mediterranean May 2027 voyage. Every communication produced by the Wing — and every piece of feedback from the Commander wearing his "customer" hat — is archived here for After-Action Review.

**Purpose:** Find what works, what feels wrong, what's missing. Every gap discovered here improves the system for real clients.

---

## How This Folder Works

| Subfolder | Contents |
|---|---|
| `sent/` | Every outbound email to John/Susie (HTML + metadata JSON) |
| `received/` | Every inbound email reply from either address |
| `feedback/` | Commander feedback given AS A CUSTOMER — onscreen, Telegram, email |
| `telegrams/` | Telegram exchanges related to the Loucks lifecycle |
| `forms/` | All intake/preference forms sent or received |

---

## Capture Rules

1. **Every outbound email** → auto-archived to `sent/` with filename `{TP}_{date}.html` + metadata JSON
2. **Every inbound reply** from johnloucks3@gmail.com or susanna.loucks@gmail.com → archived to `received/`
3. **Any onscreen comment from Commander in guinea-pig mode** → Hale writes to `feedback/` with date + channel tag
4. **Any Telegram message from Commander flagged as customer feedback** → archived to `telegrams/`
5. **Trigger phrase:** Any message containing "guinea pig", "as a customer", "as a client", or "feedback on the email" → Hale auto-captures to `feedback/`

---

## AAR Protocol
After each lifecycle touchpoint is SENT:
- Hale opens an AAR entry in `00_COMMS_LOG.md`
- Records: TP #, date sent, recipients, delivery confirmed, open status (if available), any response
- After Commander provides guinea-pig feedback: adds feedback verbatim + Hale analysis + lesson learned
- Lessons feed back into the canonical lifecycle template and dossier conventions

---

## Active Lifecycle TPs — Loucks Silver Nova May 2027

| TP | Description | Scheduled | Sent | Response | AAR Status |
|---|---|---|---|---|---|
| 0.5 | Validation + booking confirmation | Jun 11, 2026 | — | — | Pending send |
| 0.6 | Insurance review | Jun 24, 2026 | — | — | Not started |
| A.1 | Flight booking authorization | ASAP | — | — | Urgent |
| 1.1 | Voyage preview | Dec 2026 | — | — | Pending |
| … | … | … | — | — | … |

*Full TP table: D2M/lifecycle/Loucks_SilverNova_Mediterranean_May2027_Lifecycle.md*

---

*Owner: V. Hale, VCS · Thunderbird Wing · Created 2026-06-10*
