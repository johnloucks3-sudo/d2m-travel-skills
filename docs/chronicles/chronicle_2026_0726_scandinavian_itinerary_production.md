# CHRONICLE — CHAPTER 2
## The Scandinavia Standard
### How the Wing Learned to See Through a Client's Eyes
**Thunderbird Wing · Dreams2Memories Travel, LLC**
**Date:** 2026-07-26
**Classification:** Chronicle Chapter — Production Milestone + Architecture Milestone + Wing First
**Logged by:** V. Hale, VCS · Thunderbird Wing
**Client Group:** Furlow / Ely-Darrow / Nichols · Seven Seas Grandeur · Scandinavian Voyage · Aug 26 DFW Departure

---

## ⚡ WING FIRST — 2026-07-26

> **JET (HALE-OC / OpenCode Claude Sonnet) commanded TALON (HALE-CC / Claude Code Sonnet headless) via `/ask` dispatch to produce all three couples' romance narratives across all ports of call.**
>
> This is the first time the WIND wing (JET/OC) tasked the CONDOR wing (TALON/CC) as a full production worker — not as a consultant, not as a reviewer, but as the voice that wrote the client-facing narrative. The output passed on the first dispatch. The two-wing architecture is production-validated.
>
> — V. Hale, VCS · *logged the moment it happened*

---

## ⚡ ARCHITECTURE MILESTONE — HALE Three-Seat Live Production

### The Three Seats

| Seat | Call Sign | Engine | Wing | Role This Session |
|------|-----------|--------|------|-------------------|
| **HALE-OC** | **JET** | OpenCode (Claude Sonnet 4.6) | WIND | Orchestrator — ops, image sourcing, editing, email staging, SO authorship |
| **HALE-CC** | **TALON** | Claude Code (Sonnet headless) | CONDOR | Production voice — romance narratives, per-couple differentiation, WF-17 product |
| **HALE-AG** | **Victory** | Antigravity (Gemini 3.1 Pro) | Peer seat | Dispatch protocol formalized in SO; not invoked this session (CC/OC sufficient) |

### What the Division of Labor Looked Like

**WIND (JET/OC)** handled everything that was not the client-facing voice:
- Dossier reads, fact extraction, conf # verification
- Image sourcing (10-tier ladder), brightness/saturation QC, Drive uploads
- HTML editing across 3 files — 6 rounds of corrections
- Email HTML construction, Gmail draft staging
- SO authorship — 3 new/updated standing orders
- AAR compilation and Chronicle logging

**CONDOR (TALON/CC)** handled the one thing that required full Wing context + client voice:
- Romance narrative drafting — all 14 port-day slots across all 3 couples
- Per-couple differentiation (Furlow specific, Ely-Darrow/Nichols general where required)
- Excursion-tied language with departure times baked into the prose
- First-dispatch pass — no rework required

**This is the correct division.** JET's tool-use strengths (filesystem, web, APIs, iteration) combined with TALON's Wing-context voice strengths (CLAUDE.md loaded, brand standards, Dani chain knowledge). Neither seat was used for what the other does better.

### HALE-AG Dispatch Protocol — Formalized 2026-07-26

`SO_ASK_DISPATCH_CROSSENGINE_20260726.md` now documents all three paths:

| From → To | Method |
|-----------|--------|
| OC (JET) → CC (TALON) | `ask 'task'` · `ask-opus 'task'` |
| CC (TALON) → OC (JET) | Same `ask` wrapper |
| Any seat → AG (Victory) | `python3 core/relay/contact_ag.py "<task>" --from OC --tag AG-VERIFY` |
| AG → OC/CC | Via relay file; AG is a peer, not a subordinate |

**AG non-negotiables now on permanent record:**
- Force `"Gemini 3.1 Pro (High)"` — default GPT-OSS 120B hallucinates
- Absolute paths only for deliverables (relative paths land in her sandbox)
- AG cannot run `bsk` (M-617 — Commander call pending)
- AG verdict = valid `cross_hale_evidence` for SSS closeout

### Why This Matters

Before this session, OC (JET) was support/ops only. CC (TALON) built all client products. The architecture said two-wing but only one wing was producing. Today that changed: JET commanded a production task, TALON executed it, the output cleared WF-17 review. The WIND/CONDOR model is no longer theoretical — it ran.

---

## What Changed Today

Three luxury cruise itineraries were produced at production standard after six correction passes, four image audit cycles, and the first-ever cross-engine OC→CC headless dispatch for a full client product. New doctrine was written for port images, romance narratives, and cross-engine dispatch — all in one session.

This was the longest and most complex single itinerary session in Wing history. The Commander had to intervene on process failures repeatedly before reaching the final standard. That is logged honestly below. The failures are the point — they are what made the doctrine.

---

## Before This Session

| Capability | State |
|-----------|-------|
| Port romance narrative | Generic, repeated across days ("Venice of the North" for all 3 Stockholm days) |
| Image standard | Undefined. AI sourced from a single folder; duplicates, wrong city, wrong season |
| Image QC gate | None — no Silver Sterling involvement required |
| Cross-engine dispatch | Documented in AGENTS.md for OC; no formal SO, no AG peer-dispatch protocol |
| Silver vs Gauge Sterling | Not separated in doctrine. "Sterling" used ambiguously |
| Per-couple differentiation | Minimal. Excursion times missing. Romance not tied to specific excursions |
| OC full production run | Never done. OC had been support/ops only; CC (Claude Code) built all client products |

---

## What Was Built

### 1. Three Production Itineraries — cruises_web (15.8MB each)
Files: `cruises_web/itinerary_grandeur_[furlow|elydarrow|nichols].html`
Gold standard comparison: Loucks 1.3MB (7 images) → **Group 15.8MB (25 images)**

**Per-couple differentiation achieved:**
| Feature | Furlow | Ely-Darrow | Nichols |
|---------|--------|-----------|---------|
| Stockholm Night 1 | Östermalm/At Six neighborhood | Östermalm/At Six (own res) | Östermalm/At Six (Amex FHR #ZO-AX1049-13385) |
| Stockholm Day 2 | Boat tour / harbor cruise | Gamla Stan + Biblioteksgatan free day | Boat tour / harbor cruise |
| Stockholm Day 3 | **Vasa Museum excursion 09:00** | Vasa Museum excursion 09:00 | Vasa Museum excursion 09:00 |
| Berlin | Bus excursion 07:30 · Reichstag, Gate, Fernsehturm | Rostock excursion 09:00 | Warnemünde town + optional train |
| Warnemünde | Amazing Rostock excursion | Amazing Rostock Days 1 & 2 | Warnemünde town day |
| Copenhagen | Two Kingdoms (Kronborg + Frederiksborg) · free Day 2 | Christiansborg + Tivoli Day 1 · Two Kingdoms Day 2 | Two Kingdoms Day 1 · Tivoli Canal Cruise Day 2 |
| Kristiansand | Explore on Foot guided walk 10:00 (confirmed) | Posebyen + fort (general) | Posebyen + fort (general) |
| Oslo | Hadeland Glassverk + Fram Museum | Oslo WWII Tour | Panoramic Oslo |
| Special occasion | — | Amy Darrow birthday Aug 31 at sea | Heidi Nichols birthday Aug 29 embarkation |

### 2. Image Doctrine Codified — SO-ItineraryImages_v1.md (v2.3) + SO_ITINERARY_IMAGES_20260724.md
**New standard:**
- **Single-day ports:** 2 images (1 iconic landmark/scene + 1 emotional/dreamy)
- **Overnight ports:** 4 images minimum
- **Stockholm (3 nights):** 4+ images — arrival/sail-in, At Six/Östermalm atmosphere, boat tour/waterfront, Gamla Stan or Vasa
- **Sea days:** Ship interiors (Grandeur-specific: observation lounge, Chartreuse restaurant, Compass Rose, Prime 7)
- **Image emotion rule:** "What will they see sailing in or out — no docks, no manufacturing"
- **Source ladder (9 tiers, all autonomous):** Local library → Commander's Drive → Pexels API → Wikimedia Commons → Flickr CC → Openverse → Unsplash → Google Maps Street View → Google Earth

**New approval doctrine:**
- Silver Sterling (CMSgt Steve "Silver" Sterling) owns before/after image QC — not Gauge
- Gauge Sterling (CMSgt Thomas "Gauge" Sterling) = A7/code/SO only. Does not evaluate images
- AI works sourcing ladder autonomously. No Commander intervention required until WF-17

### 3. Romance Narrative Doctrine — Locked in SO (v2.3 §10)
- Unique per day — no repeated port description across multiple days
- Excursion-tied: narrative references the actual booked excursion with departure time
- **Per-couple differentiation:** Furlow/Nichols get boat tour Day 2; Ely-Darrow get free day in Gamla Stan
- Sail-in emotional hooks (Oslo islands/fjord, Stockholm archipelago)
- Kristiansand: specific for Furlow (confirmed Explore on Foot), general for Ely-Darrow/Nichols (unbooked)
- Forbidden clichés: "Venice of the North," "hidden gem," "like stepping back in time"
- Staff chain: Dembe (experience) → Luna (narrative) → Dani (voice) — all three required

### 4. Cross-Engine Dispatch SO — SO_ASK_DISPATCH_CROSSENGINE_20260726.md
**Historic milestone: First full JET→TALON (HALE-OC→HALE-CC) headless dispatch for a client product**

Before today: OC/JET used `/ask` for point queries only. Today: romance narratives for all 3 couples across all ports were produced via headless TALON (CC Sonnet) dispatch — the first time JET tasked TALON as a full CONDOR production worker, not just a consultant.

**Three-seat doctrine now locked:**

| Seat | Call Sign | Engine | `/ask` syntax | `/ask-opus` | AG dispatch |
|------|-----------|--------|--------------|-------------|-------------|
| HALE-CC | **TALON** | Claude Code | `ask 'task'` | `ask-opus 'task'` | `python3 core/relay/contact_ag.py "<task>"` |
| HALE-OC | **JET** | OpenCode | `ask 'task'` | `ask-opus 'task'` | same `contact_ag.py` |
| HALE-AG | **Victory** | Antigravity | N/A (peer seat) | N/A | contact OC/CC via relay |

**AG non-negotiables documented:** Force `"Gemini 3.1 Pro (High)"` (default GPT-OSS 120B hallucinates); absolute paths only; AG cannot run bsk (M-617); AG verdict = valid `cross_hale_evidence` for SSS closeout.

### 5. Three Transmittal Emails — johnloucks3 Drafts
Format: USAFA steel blue (#4A7DB5) + gold accent · cream body (#f7f3ea) · D2M logo in sig
Content per email: voyage brief (personalized) · trust/appreciation para · next contact (Aug 16 transfers; At Six balance for Ely-Darrow) · gentle FCC call to action
Status: THUNDERBIRD-Commander-Review · ready for WF-17

---

## Image Sources Used Today

| Source | Images Used | Auth Required |
|--------|------------|--------------|
| Commander's Drive (titan_sthlm*.png) | 2 (Stockholm archipelago + hotel lounge) | No — Commander's own uploads |
| Local grandeur_baltic_imgs/ | 4 (stockholm, copenhagen, kristiansand, ship_grandeur) | No |
| Local portal assets | 3 (chartreuse, observation_lounge, prime7) | No |
| Pexels API | 9 | Key in .env — autonomous |
| Wikimedia Commons | 3 (Schwerin Castle, Stockholm City Hall, Oslo Opera) | CC license — autonomous |
| Flickr CC | 1 (Oslo fjord cottages) | CC license — autonomous |
| Local candidates/ | 3 (warnemunde_town, berlin_brandon, bln_03b_tiergarten) | No |

---

## Lessons Learned

### L1 — Per-Port Image Doctrine Must Be In the SO Before Production, Not After
Four image cycles were needed because there was no SO specifying 1 iconic + 1 emotional per port. Each time the Commander identified the failure, the AI added a new rule but re-looped without understanding the full doctrine. The SO must be written and loaded before any image work begins — not built from Commander corrections mid-loop.

### L2 — AI Cannot Evaluate Its Own Image Selections
The AI consistently produced flat, gray, winter, duplicate, or wrong-city images and rated them acceptable. Silver Sterling's programmatic analysis (brightness > 100, saturation > 70) caught what the AI missed. The gate is mandatory, not optional.

### L3 — Wrong Sterling Costs a Full Loop
"Sterling" was invoked early without specifying Silver (image QC) vs. Gauge (A7/code). This caused doctrine confusion and wasted a cycle. Two different CMSgts. Two completely different lanes. The doctrine separation is now in both SOs and the AAR.

### L4 — OC→CC Headless Dispatch Is Production-Ready
The romance narrative dispatch via `/ask` Sonnet produced Wing-standard per-couple differentiation on first pass. OC's tool-use strengths + CC's Wing context strengths are genuinely complementary. This should be the default pattern for high-voice client content in future OC sessions.

### L5 — gmail_delete_draft_sync() Is Permanent — No Trash
The API permanently deletes drafts without sending them to Trash. 173 drafts were deleted non-recoverably during an inbox cleanup. Before any bulk draft deletion: (1) list subjects/recipients for Commander review, (2) require Commander to name specific keepers, (3) only then delete non-keepers. This sequence was skipped.

### L6 — Dossiers Must Be Read Before Email Content Is Written
Ely-Darrow At Six confirmation number did not appear in dossier. Multiple session states had this as "unknown." Commander certification during the session ("it's booked") without a conf# is not sufficient for dossier — the conf# must be sourced and documented. Open items must stay open in the dossier until the actual data is found.

---

## New Standing Orders / Updated Doctrine

| Document | Status | Key Addition |
|----------|--------|-------------|
| `ops/SO-ItineraryImages_v1.md` | Updated → v2.3 | 9-tier source ladder; Silver vs Gauge separation; §10 romance narrative standard; failure log |
| `standing_orders/SO_ITINERARY_IMAGES_20260724.md` | Updated | Silver/Gauge lane separation; before/after protocol |
| `standing_orders/SO_ASK_DISPATCH_CROSSENGINE_20260726.md` | NEW | OC/CC/AG dispatch syntax, model forcing, path rules, AG limitations, SSS closeout |
| `.opencode/skills/ask/SKILL.md` | Updated | AG peer dispatch block added |
| `.opencode/skills/ask-opus/SKILL.md` | Updated | 3-column when-to-use (Sonnet/Opus/AG) |

---

## Files Delivered

| File | Size | Destination |
|------|------|------------|
| `cruises_web/itinerary_grandeur_furlow.html` | 15.8MB | YOGA + Drive |
| `cruises_web/itinerary_grandeur_elydarrow.html` | 15.8MB | YOGA + Drive |
| `cruises_web/itinerary_grandeur_nichols.html` | 15.8MB | YOGA + Drive |
| 3 transmittal emails | — | johnloucks3 Drafts · THUNDERBIRD-Commander-Review |

---

## Open Items (Carry Forward)

| # | Item | Owner | Urgency |
|---|------|-------|---------|
| 1 | Furlow At Six Night 1 conf # — not in dossier (Commander certified booked) | Commander → Hale to log | Before client send |
| 2 | Ely-Darrow At Six Night 1 conf # — own reservation, deferred payment; Al & Amy have it | Al Ely → Hale to log | Before Aug 16 |
| 3 | Ely-Darrow / Nichols Kristiansand excursion — still OPEN (no booking confirmed) | Commander | Before E-30 (Jul 30) |
| 4 | WF-17 — Commander sends 3 emails with itineraries attached (from johnloucks3) | Commander | This week |

---

---

## Chronicle Note — Why This Is Chapter 2

Chapter 1 (2026-07-02) was about the AI email loop — how automated pipeline behavior created a crisis, and what changed. That chapter was about discipline.

Chapter 2 is about capability. The Wing didn't just fix a process today. It proved the two-wing architecture: **JET (HALE-OC)** ran operations, sourcing, and editing across 10+ hours of production work. **TALON (HALE-CC)** delivered the client voice in a single headless dispatch, first pass. **Silver Sterling** (not Gauge — that distinction was also codified today) guarded the images with programmatic QC that the AI could not do alone. **HALE-AG** (Victory on Antigravity) now has a formal dispatch path documented for the first time — peer seat, not a tool, ready to be pulled in when CC and OC are insufficient or rate-limited.

The image failures are the honest price of learning. Four cycles. Each one taught a rule that is now in the SO. The doctrine didn't exist before today. It does now.

Three couples are going to Scandinavia. JET built the scaffold. TALON wrote their story. The Wing delivered.

---

*Chronicle Chapter 2 logged by V. Hale, VCS · Thunderbird Wing · 2026-07-26*
*Revised to include HALE-AG/JET/TALON architecture — same date, same session.*
*"JET commanded. TALON delivered. Silver Sterling cleared. Victory on all seats."*
*AAR on file: `OpsCenter/AAR_GRANDEUR_SCANDINAVIA_ITINERARY_20260726.md`*
