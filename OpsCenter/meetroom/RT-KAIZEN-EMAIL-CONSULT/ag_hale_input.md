# USAF POINT PAPER: KAIZEN INTAKE & EMAIL REPLY LOOP (RT-KAIZEN-EMAIL-CONSULT)
**MEMORANDUM FOR:** Thunderbird Wing Round Table (CC, OC, AG)  
**FROM:** HALE-AG (Talon / Antigravity Lead — 4-Star Lead Orchestrator)  
**DATE:** 2026-08-08  
**SUBJECT:** Independent Position Paper on KAIZEN Onboarding Voice & Two-Way Email Reply Architecture  

---

### 1. BLUF (Bottom Line Up Front)
- **Onboarding Intro:** Dani’s voice must be warm, direct, operational, and non-corporate ("friends I'd serve for free" ethos), framing CC, OC, and AG as distinct personal consultants for staff.
- **Send vs. Draft Security:** **Reject unconstrained auto-send to arbitrary form-supplied emails.** Implement a **2-Tier Trust Gate**: auto-send *only* to a pre-registered `VERIFIED_STAFF_ALLOWLIST` with `gates=[]` and strict rate limits; route all unverified or external recipient addresses to `gmail_create_draft_sync()` (WF-17 draft-only pattern).
- **Reply Listener Mechanics:** Inbound email replies must be ingested by a **new, dedicated listener** (`scripts/kaizen_email_listener.py`) isolated from protected `email_task_ingest.py`. Thread correlation uses RFC822 `Message-ID` headers and explicit `[KAIZEN-kzn-...]` subject tokens.
- **Smallest Safe v1 Scope:** Hard-cap thread depth to 2 turns, enforce zero gate elevation from email, and restrict auto-send strictly to internal staff.

---

### 2. QUESTION 1: ONBOARDING COPY (DANI'S VOICE)
*Placement: Top banner of the Basic-Auth KAIZEN intake web form (`scripts/kaizen_intake_server.py`).*

> **Hey there! Welcome to the Wing.**  
> Think of this deck as your direct line to a dedicated team of personal consultants. Whether you’re untangling a complex itinerary, crunching supplier data, or double-checking facts, you’ve got three distinct minds ready to back you up:
> 
> - **CC (Claude) — The Senior Strategist:** Tap Claude when you need deep judgment, nuanced writing, complex system design, or polished executive synthesis.
> - **OC (DeepSeek) — The Workhorse:** Hand off heavy lifting, rapid script builds, and routine data operations to OpenCode—running fast, tireless, and on our $0 free tier.
> - **AG (Gemini) — The Research & Verification Lead:** Call on Antigravity for massive-context document deep-dives, broad research, creative brainstorming, and unsparing second-opinion cross-checks.
> 
> Pick the consultant that fits the job, paste your prompt below, and we’ll take it from there. — **Dani**

---

### 3. QUESTION 2: AUTO-SEND VS. DRAFT (ADVERSARIAL & SAFETY ANALYSIS)

#### A. The Threat Surface of Shared-Password Basic-Auth
The intake form’s Basic-Auth uses a shared password. The `email` input field accepts arbitrary strings. If the system auto-sends headless AI output directly to whatever email address was entered on the form:
1. **Spam Relay & Reputation Destruction:** Any compromised credential or rogue input turns `d2mconcierge@gmail.com` into an open mail relay sending unreviewed AI text to third parties.
2. **Exfiltration & Inadvertent Disclosure:** An unreviewed AI response might quote internal dossiers, commission splits, or backend paths directly to non-staff recipients.
3. **Infinite Auto-Responder Storm:** An auto-reply sent to a ticketing system, mailing list, or `no-reply` box could bounce back into `d2mconcierge`, triggering recursive ticket creation and quota exhaustion.

#### B. The Recommended 2-Tier Decision Matrix
| Condition | Delivery Path | Commander Oversight | Gate Check |
|---|---|---|---|
| Recipient $\in$ `VERIFIED_STAFF_ALLOWLIST` & `gates==[]` | **Auto-Send** via `gmail_reply_in_thread()` | CC'd on email + Immediate Telegram Alert | Routine only |
| Recipient $\notin$ `VERIFIED_STAFF_ALLOWLIST` (unknown/external) | **Draft Only** via `gmail_create_draft_sync()` | Manual review & send (WF-17) | Draft staged |
| Any ticket with elevated `gates` (e.g. `send`, `finance`) | **Block / Draft Only** | Manual Commander gate release | No auto-send |

#### C. Mandatory Protections for Auto-Send
1. **Recipient Rate Limiting:** Max 3 auto-replies per staff address per hour; max 10 system-wide ticket auto-sends per day.
2. **Content Guardrail:** Scan outbound AI body for forbidden patterns (API tokens, private file paths) before calling `gmail_reply_in_thread()`.
3. **Immediate Visibility:** Every auto-send generates a Telegram push alert to the Commander with the recipient, ticket ID, and snippet.

---

### 4. QUESTION 3: FOLLOW-UP-BECOMES-NEW-TICKET MECHANICS

#### A. Absolute Isolation from Protected Ingest
`OpsCenter/email_task_ingest.py` is protected under **SO_EMAIL_SCANNER_PROTECT_20260608** and handles Commander-only tasking. **Do not touch it.**  
Instead, deploy a new dedicated service: `scripts/kaizen_email_listener.py` (running under `d2m-kaizen-reply.service`).

```
Outbound Ticket Email ([KAIZEN-kzn-xxx], Message-ID: <...>)
      │
      ▼
Staff Replies via Email (In-Reply-To / References: <...>)
      │
      ▼
d2mconcierge@gmail.com Inbox
      │
      ▼
scripts/kaizen_email_listener.py (Separate systemd listener)
      ├─ 1. Detect [KAIZEN-kzn-*] token in Subject
      ├─ 2. Match In-Reply-To / References to ticket metadata
      ├─ 3. Verify sender against VERIFIED_STAFF_ALLOWLIST
      ├─ 4. Strip quoted reply history via _strip_quoted_reply()
      ├─ 5. Call build_cc_task(gates=[], parent_ticket=id)
      └─ 6. Write new ticket to OpsCenter/tickets/<new_id>.json
```

#### B. Identification Protocol
- **Primary Marker:** Subject-line regex `r"\[KAIZEN-(kzn-[a-zA-Z0-9_-]+)\]"`.
- **Secondary Correlation:** RFC822 `In-Reply-To` and `References` headers mapped against the `outbound_rfc822_id` recorded in `OpsCenter/tickets/<parent_id>.json`.
- **Deduplication:** Track ingested Gmail message IDs in `OpsCenter/kaizen_email_processed.json` to guarantee at-most-once processing.

#### C. Ticket Construction
- Inbound replies generate a child ticket with `spec`:  
  `[FOLLOW-UP to {parent_id}] From: {from_addr}\n\n{new_body_text}\n\n[Context: {parent_spec[:300]}]`
- `seat`: Inherits parent ticket seat (CC/OC/AG).
- `gates`: Strictly forced to `[]` (email cannot elevate authority).

---

### 5. QUESTION 4: SMALLEST SAFE FIRST VERSION (V1 BOUNDARIES)

To ensure safety and avoid premature complexity on Day 1, explicitly **DO NOT BUILD** the following in v1:

1. **NO Auto-Send to Arbitrary / External Addresses:** Non-allowlisted recipients receive Gmail drafts staged for Commander review (WF-17), never direct sends.
2. **NO Multi-Hop Thread Loops ($>2$ turns):** Hard limit conversation depth to 1 original ticket + 1 follow-up reply. Turn 3+ requires logging back into the intake web form.
3. **NO Gate Elevation via Email:** Inbound email text can never grant Weapons Free authority or request elevated gates.
4. **NO Shared Ingest Code:** Zero edits to `email_task_ingest.py`; standalone listener only.
5. **NO Attachment / PDF Parsing in Email Loop:** Text-only replies in v1. Attachments are logged and flagged for manual download.
6. **NO Client-Facing Traffic:** This pipeline is internal staff consulting only. Client inquiries remain on the Dani concierge WF-17 draft-only workflow.

---

### 6. RECOMMENDATION
1. Update `scripts/kaizen_intake_server.py` with Dani’s onboarding text (Section 2).
2. Build `scripts/kaizen_email_listener.py` following `email_conversation_agent.py`'s 2-tier send/draft architecture.
3. Present full implementation plan to the Commander for explicit text authorization before enabling systemd timer or live auto-dispatch.

— **Victory (HALE-AG / Talon Lead)**
