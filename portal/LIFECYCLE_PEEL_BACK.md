# LIFECYCLE PEEL-BACK
## Kuklinski Group — Viking Mars | Panama Canal & Central America | Dec 17-27, 2026
### Thunderbird OS — Dreams2Memories Travel, LLC | D2M-LC-KUKLINSKI-2026

**Document purpose:** Machine-readable and human-readable four-layer breakdown of every lifecycle touchpoint. Each touchpoint is dissected at four layers: what the client sees, who acts and how, which code runs, and what moves where.

**Classification:** INTERNAL — Wing Operations  
**Owner:** Col Victoria Hale, COS  
**Last updated:** 2026-04-19  

---

## REFERENCE: STATUS CODES

| Code | Meaning |
|------|---------|
| SENT | Delivered to client |
| OVERDUE | Past due — immediate action required |
| ACTIVE_SEARCH | Research window open |
| PENDING | Future window not yet started |

## REFERENCE: LAYER DEFINITIONS

- **Layer 1 — Client View:** What lands in the client's inbox; what they see, feel, and are asked to do.
- **Layer 2 — Staff View:** Which persona triggers, what they produce, how it flows through the wing before delivery.
- **Layer 3 — Code View:** Which `.py` file handles execution, which function runs, which MCP tool or API is called.
- **Layer 4 — Data Flow:** What data enters the process, what is produced, where outputs are stored.

---

## PHASE 0 — ONBOARDING

---

### TP 0.5 — Welcome / Validation
**Status:** SENT  
**Send Date:** Apr 17, 2026  
**Owner:** A3 Dani  

#### Layer 1 — Client View
An elegantly formatted email arrives from concierge@d2mluxury.quest. Navy banner, cream background, blue ink. It confirms all three booking references by name, announces the D2M team, and welcomes the group to the Viking Mars Panama Canal voyage. Kyle Kuklinski is addressed as the primary contact. The tone is warm, crisp, and certain — no hedging, no corporate boilerplate. The email validates that Dreams2Memories has the details and is on watch.

#### Layer 2 — Staff View
Hale triggers Dani for the welcome/validation send on Apr 17. Dani aggregates guest data from the dossier, formats the email using D2M stationery template, and runs it through her voice calibration. Hale runs the WF-17 gate (logo, sig block, stationery, sign-off). Product surfaces to Commander as draft in d2mconcierge plus copy to johnloucks3 at 0600. Commander approves. Dani executes send to all 6 guests via concierge@d2mluxury.quest.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| Voice matching | `core/email/thunderbird_dani_voice.py` → `match_voice_profile()` |
| Booking validation | `core/client/thunderbird_validation.py` → `validate_booking_data()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — all 6 guest names, emails, booking refs, payment status |
| Data in | `storage/cache/client_context/kuklinski_context.json` |
| Processing | Validation confirms 3 booking refs, $21,244 paid, all fields present |
| Output | Draft created in d2mconcierge Gmail |
| Output | Email sent from concierge@d2mluxury.quest to all 6 guest emails |
| Output | Dossier email log updated — TP 0.5 status set to SENT |

---

### TP 0.6 — Insurance Discussion
**Status:** OVERDUE (sprint window Apr 18-25 missed; send date Apr 28 passed)  
**Owner:** A3 Dani  

#### Layer 1 — Client View
Kyle Kuklinski receives a personal email from Dani presenting travel protection options tailored to the group's voyage. The email is clear about the stakes — 6 guests, ages 41-81, traveling internationally over 10 nights — without being alarmist. Specific coverage levels are summarized with pricing. A clear call to action asks Kyle to choose a tier or schedule a call.

#### Layer 2 — Staff View
Hale flags TP 0.6 as OVERDUE — sprint window Apr 18-25 has passed. Immediate escalation: Dani is tasked to produce the insurance proposal NOW. Dani pulls age data from the dossier (ages 41 to 81 — Joshua Morton is highest risk at age 80), identifies appropriate travel protection products, formats the email with coverage summaries and pricing. Hale runs WF-17. Surfaces to Commander urgently. Commander approves. Send executed.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| Voice matching | `core/email/thunderbird_dani_voice.py` → `match_voice_profile()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — guest DOBs (ages 41-81), travel dates, booking total |
| Data in | Insurance product catalog / pricing matrix |
| Processing | Dani formats age-tiered coverage options; A9 Harlan validates markup if commission applies |
| Output | Insurance proposal draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to Kyle Kuklinski (kyle.kuklinski@gmail.com) |
| Output | Dossier insurance section updated — follow-up flag removed on selection |

---

## PHASE 1 — DISCOVERY

---

### TP 1.1 — Voyage Preview
**Status:** SENT  
**Send Date:** Apr 17, 2026  
**Owner:** A3 Dani  
**Supporting:** A6 Luna (copy), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
A vivid, emotionally-charged email paints the Panama Canal and Central America voyage. Each port — Panama City, Cartagena, Santa Marta, Puerto Limon — is evoked with a single powerful image or description. The canal transit is positioned as the centerpiece. The client reads this and gets excited to be going. No pricing, no logistics — pure experience and anticipation.

#### Layer 2 — Staff View
A6 Luna owns the creative writing on this touchpoint, drawing from ship intel data. Dani aggregates Luna's copy and formats it into the D2M email stationery. Hale checks WF-17 — logo, sig block, sign-off. Draft surfaces to Commander. Commander approves. Dani sends to all 6 guests.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Ship intel pull | `core/intel/thunderbird_ship_intel.py` → `run_ship_intelligence_sweep()` |
| Creative composition | Via `thunderbird_personas.py` → A6 Luna persona |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| Voice matching | `core/email/thunderbird_dani_voice.py` → `match_voice_profile()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft + send | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tools | `run_ship_intelligence_sweep`, `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | Viking Mars ship intel — amenities, ports, canal transit narrative |
| Data in | Kuklinski context cache — relationship tone calibration |
| Processing | A6 Luna writes port descriptions; Dani formats |
| Output | Sent from concierge@d2mluxury.quest to all 6 guests |
| Output | Dossier TP 1.1 marked SENT |
| Storage | Ship intel → `Thunderbird_Intel` Drive folder (ID: `1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj`) |

---

### TP 1.2 — Airfare Watch
**Status:** ACTIVE SEARCH (Apr 21 – Jun 10)  
**Send Date:** Jun 17, 2026  
**Owner:** A2 Dembe  
**Supporting:** A5 Viper (fare strategy), A9 Harlan (cost), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
On Jun 17, Kyle Kuklinski receives a detailed airfare recommendation email. Two routing pairs are presented: Richmond (RIC) to Panama City (PTY) for Kyle, Rosalie, Roger, and Nick — and Naples/Fort Myers (RSW) to Fort Lauderdale (FLL) for Josh and Erica. Each option shows airline, connection, total price, and a recommendation. A clear call to action asks Kyle to authorize booking before prices move.

**During search window:** Commander receives weekly Monday morning fare reports to johnloucks3@gmail.com as full sends, tracking price trends and optimal booking windows.

#### Layer 2 — Staff View
A2 Dembe runs parallel searches on both routing pairs every week from Apr 21 through Jun 10. A5 Viper advises on fare timing — whether to hold or book — based on price trend analysis. A9 Harlan costs each option with D2M markup applied. Dembe compiles weekly Commander reports (full send, not draft). At Jun 17 send date, Hale orchestrates the final client email. Dani formats. WF-17 gate. Commander approves. Send.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Flight search | `core/mcp/travel_mcp_server.py` → `search_flights()` |
| Price trend monitoring | `core/intel/thunderbird_price_monitor.py` → `monitor_fare_trends()` |
| Commission/markup | `core/booking/thunderbird_commission_recon.py` → `reconcile_commission()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `search_flights`, `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | Routing pairs from dossier: RIC→PTY (guests G1-G4), RSW→FLL (guests G5-G6) |
| Data in | Live fare data via Centrav B2B API (travel_mcp_server.py) |
| Data in | A5 Viper fare timing analysis |
| Processing | A9 Harlan applies D2M markup (25% standard); builds costed options table |
| Output (weekly) | Fare report — full send to johnloucks3@gmail.com, Mon AM, Apr 21 – Jun 10 |
| Output (final) | Airfare proposal email — draft in d2mconcierge Gmail |
| Output (final) | Sent from concierge@d2mluxury.quest to Kyle Kuklinski |
| Storage | Dossier airfare section updated with selected option on Commander approval |

---

### TP 1.3 — Hotel Options
**Status:** ACTIVE SEARCH (Apr 21 – Jun 10)  
**Send Date:** Jun 17, 2026 (combined with TP 1.2)  
**Owner:** A2 Dembe  
**Supporting:** A6 Luna (property descriptions), A9 Harlan (cost), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
Combined with the airfare email on Jun 17, Kyle receives hotel options for two stays: a pre-cruise hotel in Panama City (likely Dec 15-17, arriving a day early before the Dec 17 embarkation) and a post-cruise hotel in Fort Lauderdale (Dec 27-28, disembarkation day). Each property is presented with: name, link, images, guest reviews, and pricing for the room types. A6 Luna's copy makes each property feel like part of the journey, not just a place to sleep.

#### Layer 2 — Staff View
A2 Dembe researches hotel options in Panama City (near embarkation port) and Fort Lauderdale (near Port Everglades). A6 Luna writes property descriptions. A9 Harlan applies markup. Dani formats both options into a unified email with stationery. Hale runs WF-17. Quote PDFs generated and stored to Drive. Commander approves. Send.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Hotel search | `core/mcp/travel_mcp_server.py` → `search_hotels()` |
| Quote PDF render | `core/client/thunderbird_quote_render.py` → `render_hotel_quote_pdf()` |
| Markup application | `core/booking/thunderbird_commission_recon.py` → `reconcile_commission()` |
| World intel | `core/intel/thunderbird_world_intel.py` → `run_world_intelligence_sweep()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tools | `search_hotels`, `render_hotel_quote_pdf`, `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | Itinerary dates: embark Dec 17 Panama City, disembark Dec 27 Fort Lauderdale |
| Data in | Hotel rates via Hotelbeds/Bedsonline wholesale GDS |
| Data in | A6 property narrative copy |
| Processing | A9 Harlan: `client_price = net_usd * 1.25` (standard) or `1.22` (premium/SLH) |
| Output (weekly) | Hotel research report — full send to johnloucks3, Mon AM (combined with airfare) |
| Output (quote) | Hotel quote PDFs → `Thunderbird_Proposals` Drive folder (ID: `1g2AlDLEjd71cIL-T0HfIh2ytatPBCgVn`) |
| Output (final) | Hotel proposal email — draft in d2mconcierge Gmail |
| Output (final) | Sent from concierge@d2mluxury.quest to Kyle Kuklinski |
| Storage | Dossier hotel section updated on Commander approval |

---

## PHASE 2 — MOMENTUM

---

### TP 2.1 — Excursion Recommendations
**Status:** PENDING (search begins May 5)  
**Send Date:** Aug 1, 2026  
**Critical constraint:** Must reach client before Viking's excursion portal opens Aug 2  
**Owner:** A2 Dembe  
**Supporting:** A6 Luna (port copy), A9 Harlan (cost), A3 Dani (email), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
On Aug 1 — one day before Viking's excursion portal opens — Kyle receives a carefully curated excursion guide covering three ports: Cartagena, Santa Marta, and Puerto Limon. For each port, D2M presents both Viking-curated and independent options with comparative pricing, time requirements, and group suitability. A6 Luna's writing makes each excursion feel like a story waiting to happen. The email positions D2M as having done the homework so the group can choose with confidence, rather than defaulting to whatever Viking shows them first.

#### Layer 2 — Staff View
A2 Dembe runs parallel port research from May 5 through Jul 25 — GetYourGuide scraper for independent tours, Viking portal data for ship-offered excursions. Weekly Commander reports go out each Monday. A6 Luna writes port-specific narrative for each excursion type. A9 Harlan costs independent options with D2M markup; Viking options are priced at list with D2M commentary. Dembe and Hale compile the final package. Dani formats. WF-17 gate. Commander approves before Aug 1. Send.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Tour search | `core/mcp/travel_mcp_server.py` → `search_tours()` |
| World intel | `core/intel/thunderbird_world_intel.py` → `run_world_intelligence_sweep()` |
| Markup calculation | `core/booking/thunderbird_commission_recon.py` → `reconcile_commission()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tools | `search_tours`, `run_world_intelligence_sweep`, `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | Port schedule: Cartagena (Dec 19), Santa Marta (Dec 20), Puerto Limon (Dec 21) |
| Data in | GetYourGuide tour data via Playwright scraper |
| Data in | Viking Mars excursion catalog |
| Data in | A6 Luna experiential copy per port |
| Processing | A9 Harlan costs independent tours: `client_price = net_usd * 1.25` |
| Output (weekly) | Excursion research reports — full send to johnloucks3, Mon AM, May 5 – Jul 25 |
| Output (final) | Excursion guide email — draft in d2mconcierge Gmail |
| Output (final) | Sent from concierge@d2mluxury.quest to Kyle Kuklinski (primary) |
| Storage | Dossier excursions section updated |
| Storage | World intel outputs → `Thunderbird_Intel` Drive folder |

---

### TP 2.2 — Monthly Validation
**Status:** ACTIVE (ongoing — 15th of each month, Apr through Nov)  
**Send Dates:** Apr 15, May 15, Jun 15, Jul 15, Aug 15, Sep 15, Oct 15, Nov 15 (8 total)  
**Owner:** A3 Dani  
**Supporting:** Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
On the 15th of each month, Kyle receives a brief, reassuring status check from Dani. It confirms all bookings are active, notes any upcoming milestones or deadlines, reports on guest form completion (Morton and Dodge forms are flagged as missing until resolved), and previews what's coming next in the lifecycle. Clean, scannable, low-friction. The client knows D2M has eyes on the voyage without being overwhelmed.

#### Layer 2 — Staff View
Dani pulls current booking status from the dossier and TESS/Viking system. Validates against the master plan. Checks guest form completion. Drafts the monthly validation email using the standard template. Hale runs WF-17. Draft goes to d2mconcierge Gmail. A copy goes to Commander at 0600. Commander approves. Send on the 15th.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Booking validation | `core/client/thunderbird_validation.py` → `validate_booking_data()` |
| Guest form check | `core/booking/thunderbird_guest_forms.py` → `check_guest_form_status()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — current booking status |
| Data in | `THUNDERBIRD_MASTER_PLAN.md` — Part 5 active bookings registry |
| Data in | Viking / TESS booking system — payment and status confirmation |
| Data in | Guest form system — Morton (MISSING), Dodge (MISSING) |
| Processing | Dani compares current state against lifecycle milestone calendar |
| Output | Monthly validation email — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to Kyle Kuklinski |
| Storage | Dossier validation log entry added per send |

---

### TP 2.3 — Dining Research
**Status:** PENDING (search begins Jun 16)  
**Send Date:** Sep 18, 2026 (same day as TP 2.4)  
**Owner:** A2 Dembe  
**Supporting:** A6 Luna (dining copy), A9 Harlan (cost), A3 Dani (email), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
In mid-September, Kyle receives a dining guide covering two areas: onboard Viking Mars specialty restaurants with advance booking recommendations, and port dining options in Cartagena, Santa Marta, and Puerto Limon. The email also addresses holiday dining on the ship — Christmas Eve (Dec 24, sea day) and Christmas Day (Dec 25, sea day) — with details about what Viking traditionally offers. The tone is enthusiastic and specific, not generic. A6 Luna makes the food feel like an adventure.

#### Layer 2 — Staff View
A2 Dembe runs world intel sweeps on all three ports for restaurant intelligence. Dembe also researches Viking Mars specialty dining options and holiday meal programming. Weekly Commander reports go out Mondays Jun 16 – Sep 11. A6 Luna writes dining copy. Dani formats. Hale runs WF-17. Commander approves. Send Sep 18 (combined day with TP 2.4).

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| World intel | `core/intel/thunderbird_world_intel.py` → `run_world_intelligence_sweep()` |
| Ship intel | `core/intel/thunderbird_ship_intel.py` → `run_ship_intelligence_sweep()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tools | `run_world_intelligence_sweep`, `run_ship_intelligence_sweep`, `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | Viking Mars onboard dining menus and specialty restaurant details |
| Data in | Port restaurant data via world intel sweeps — Cartagena, Santa Marta, Puerto Limon |
| Data in | Holiday programming intel — Viking Dec 24-25 traditions |
| Data in | A6 Luna dining narrative copy |
| Processing | Dembe compiles and structures; A6 adds voice; Dani formats |
| Output (weekly) | Dining intel reports — full send to johnloucks3, Mon AM, Jun 16 – Sep 11 |
| Output (final) | Dining guide email — draft in d2mconcierge Gmail |
| Output (final) | Sent from concierge@d2mluxury.quest to Kyle Kuklinski |
| Storage | World intel outputs → `Thunderbird_Intel` Drive folder |
| Storage | Dossier dining section updated |

---

### TP 2.4 — Document Audit
**Status:** PENDING (audit begins Jul 1)  
**Send Date:** Sep 18, 2026 (same day as TP 2.3)  
**Owner:** A2 Dembe  
**Supporting:** A3 Dani (email), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
Kyle receives a document checklist email in September covering everything the group needs to have in order before departure. Passport validity rules for all three countries (Colombia, Costa Rica, Panama). Visa requirements (if any). Health documentation considerations. The email also specifically notes that D2M still needs guest profiles from Joshua Morton and Erica Dodge — with a polite but clear ask to complete the forms. The tone is helpful and organized, not panicked. Kyle feels like there's a clear checklist and time to execute.

#### Layer 2 — Staff View
A2 Dembe compiles entry requirements for Panama, Colombia, and Costa Rica. Dossier scanner flags Morton and Dodge guest forms as still MISSING. Dembe writes document audit summary. Dani formats with the guest form follow-up section included. Hale runs WF-17. Commander approves. Send Sep 18.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Dossier gap scan | `core/booking/thunderbird_dossier_scanner.py` → `scan_dossier_gaps()` |
| Guest form check | `core/booking/thunderbird_guest_forms.py` → `check_guest_form_status()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — guest DOBs, nationalities, current form status |
| Data in | Destination entry requirement research — Panama, Colombia, Costa Rica |
| Data in | Guest form system — Morton status: MISSING; Dodge status: MISSING |
| Processing | Scanner flags gaps; Dembe compiles checklist; Dani adds guest-form follow-up |
| Output | Document audit email — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to Kyle Kuklinski |
| Storage | Dossier document status section updated |
| Storage | Guest form follow-up flag remains active until forms received |

---

## PHASE 3 — PRE-DEPARTURE

---

### TP 3.1 — Pre-Voyage Brief
**Status:** PENDING (assembly begins Aug 25)  
**Send Date:** Nov 26, 2026  
**Owner:** A2 Dembe (research), A6 Luna (narrative)  
**Supporting:** EXEC Naia (voice review), A3 Dani (email), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
In late November, all six guests receive the most comprehensive email of the entire lifecycle. It's the pre-voyage playbook. Port-by-port destination guides. Embarkation logistics for Panama City. Disembarkation logistics for Fort Lauderdale. Canal transit what-to-expect. December weather and what to pack. Health advisories (tropical medicine, vaccination recommendations for Colombia and Costa Rica). Viking app download and online check-in instructions. Holiday at sea preview. The email is long but not bloated — every section earns its place. A6 Luna's writing makes even the logistics feel exciting.

#### Layer 2 — Staff View
A2 Dembe runs the most expansive research phase of the lifecycle over August 25 to November 19 — weekly intel sweeps on all five ports, weather data, health advisories, Viking system logistics, and canal transit detail. A6 Luna writes narrative for each port and experience segment. EXEC Naia voice-reviews the full draft — this is the highest-touch email in the pre-departure phase, and voice fidelity matters. Dani formats into D2M stationery. Hale runs WF-17. Commander approves. Sends to all 6 guests.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| World intel | `core/intel/thunderbird_world_intel.py` → `run_world_intelligence_sweep()` |
| Ship intel | `core/intel/thunderbird_ship_intel.py` → `run_ship_intelligence_sweep()` |
| Persona engine (Luna + Naia) | `core/ai_infra/thunderbird_personas.py` → `instantiate_persona()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| Voice matching | `core/email/thunderbird_dani_voice.py` → `match_voice_profile()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tools | `run_world_intelligence_sweep`, `run_ship_intelligence_sweep`, `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | World intel sweeps — Panama City, Cartagena, Santa Marta, Puerto Limon, Fort Lauderdale |
| Data in | Viking Mars ship intel — canal transit, onboard programming, logistics |
| Data in | Health advisory databases — tropical medicine, vaccination schedules |
| Data in | December weather forecast data for all ports |
| Data in | Full Kuklinski lifecycle context — preferences built over 7 months |
| Processing | A2 Dembe structures content; A6 Luna writes narrative; Naia voice-reviews |
| Output (weekly) | Pre-voyage assembly reports — full send to johnloucks3, Mon AM, Aug 25 – Nov 19 |
| Output (final) | Pre-voyage brief — draft in d2mconcierge Gmail |
| Output (final) | Sent from concierge@d2mluxury.quest to all 6 guests |
| Storage | Intel outputs → `Thunderbird_Intel` Drive folder |
| Storage | Dossier TP 3.1 marked SENT |

---

### TP 3.2 — Final Confirmation
**Status:** PENDING (compile Dec 1-8)  
**Send Date:** Dec 10, 2026  
**Owner:** HALE (direct ownership — sole TP Hale owns end-to-end)  
**Supporting:** EXEC Naia (voice review), A3 Dani (email formatting), Commander (send approval)

#### Layer 1 — Client View
Seven days before departure, all six guests receive the master confirmation document. Everything in one place: all three booking references with agency conf numbers, flight confirmations, hotel details, transfer logistics, shipboard credit summary ($800 for Kyle/Rosalie, $200 for each other cabin), embarkation details (Panama City, Pier X, Dec 17 at 3:00 PM), disembarkation details (Fort Lauderdale, Dec 27 at 5:00 AM), and Viking app check-in instructions. No surprises. No gaps. Pure confidence.

#### Layer 2 — Staff View
Hale personally compiles the confirmation package Dec 1-8 — pulling from every prior lifecycle touchpoint. All ancillaries (flights, hotels, transfers) should be booked by this point; if any remain outstanding, Hale flags them to Commander. EXEC Naia voice-reviews for tone and flow. Dani formats. Hale runs WF-17. Commander approves. Sends to all 6 guests.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Dossier compilation | `core/booking/thunderbird_dossier.py` → `compile_dossier_summary()` |
| Booking validation | `core/client/thunderbird_validation.py` → `validate_booking_data()` |
| Persona engine (Naia) | `core/ai_infra/thunderbird_personas.py` → `instantiate_persona()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — all sections, fully populated |
| Data in | Flight confirmation records (booked via TP 1.2) |
| Data in | Hotel confirmation records (booked via TP 1.3) |
| Data in | Transfer confirmation records |
| Data in | Viking booking system — all 3 booking refs, SBC balances |
| Processing | Hale compiles; validates all sections against expected checklist; flags any gaps |
| Output | Final confirmation email — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to all 6 guests |
| Storage | Dossier TP 3.2 marked SENT; lifecycle_status updated to PRE_DEPARTURE |

---

### TP 3.3 — Send-Off
**Status:** PENDING  
**Send Date:** Dec 14, 2026 (3 days before embarkation)  
**Owner:** A3 Dani  
**Supporting:** EXEC Naia (voice review), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
Three days before the group flies to Panama City, all six guests receive Dani's most personal email. It is not logistical. It is emotional — a bon voyage letter that acknowledges the journey they're about to take, honors the milestone of the Panama Canal transit, and leaves them excited and cared for. Short enough to feel personal, warm enough to feel genuine. The Dreams2Memories voice at full expression.

#### Layer 2 — Staff View
Dani owns this touchpoint creatively. She draws on the full relationship context — 8 months of touchpoints, guest preferences, the group's energy. EXEC Naia voice-reviews to ensure the tone hits the mark. Hale runs WF-17. Commander approves. Sends to all 6 guests.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| Voice matching | `core/email/thunderbird_dani_voice.py` → `match_voice_profile()` |
| Persona engine (Naia) | `core/ai_infra/thunderbird_personas.py` → `instantiate_persona()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — full lifecycle relationship context |
| Data in | Itinerary highlights — canal transit, ports, Christmas at sea |
| Data in | Voice harvest — tone calibration from prior sends |
| Processing | Dani composes; Naia voice reviews; Hale gates |
| Output | Send-off email — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to all 6 guests |
| Storage | Dossier TP 3.3 marked SENT |

---

## [VOYAGE — DEC 17-27, 2026]

*No lifecycle touchpoints during active voyage. Wing monitors in background.*

---

## PHASE 5 — POST-VOYAGE

---

### TP 5.1 — Welcome Home
**Status:** PENDING  
**Send Date:** Dec 28, 2026 (day after disembarkation)  
**Owner:** A3 Dani  
**Supporting:** EXEC Naia (voice review), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
The morning after the group disembarks in Fort Lauderdale, all six guests receive a warm welcome home email. It acknowledges the voyage they just completed, celebrates the Panama Canal transit and the holiday time at sea, and expresses genuine pride in having been part of the journey. No ask, no upsell — just warmth. Sets the tone for the post-voyage survey that will follow.

#### Layer 2 — Staff View
Dani drafts the welcome home email drawing on relationship context. EXEC Naia voice-reviews. Hale gates. Commander approves and sends day after disembarkation (Dec 28).

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| Voice matching | `core/email/thunderbird_dani_voice.py` → `match_voice_profile()` |
| Persona engine (Naia) | `core/ai_infra/thunderbird_personas.py` → `instantiate_persona()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — voyage summary, full lifecycle context |
| Data in | Voice harvest — relationship tone from all prior sends |
| Processing | Dani composes; Naia reviews; Hale gates |
| Output | Welcome home email — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to all 6 guests |
| Storage | Dossier TP 5.1 marked SENT; lifecycle_status updated to POST_VOYAGE |

---

### TP 5.2 — Post-Voyage Survey
**Status:** PENDING  
**Send Date:** Jan 3, 2027  
**Owner:** A7 Gauge  
**Supporting:** Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
Six days after returning home, all six guests receive a brief NPS + experience survey. It is formatted as a D2M email — not a generic survey link. The questions are specific to the Viking Mars voyage: overall satisfaction, D2M service quality, which touchpoints were most helpful, what could be improved, and an NPS score. Honest feedback is invited without pressure.

#### Layer 2 — Staff View
A7 Gauge owns survey design and deployment. Gauge selects and formats survey questions calibrated to the Kuklinski voyage. Hale runs WF-17 on the deployment email. Commander approves. Send Jan 3. Survey responses feed back into D2M lessons-learned and calibrate future lifecycle templates.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Survey generation | `core/client/thunderbird_survey.py` → `generate_nps_survey()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | Voyage itinerary and lifecycle touchpoints — for relevant question generation |
| Data in | Guest list and emails from dossier |
| Processing | Gauge generates survey questions; formats deployment email |
| Output | Survey deployment email — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to all 6 guests |
| Storage | Survey responses → dossier lessons-learned section |
| Storage | NPS scores → `THUNDERBIRD_MASTER_PLAN.md` client metrics |

---

### TP 5.3 — Thank You + Referral
**Status:** PENDING  
**Send Date:** Jan 10, 2027  
**Owner:** A3 Dani (co-owned with EXEC Naia)  
**Supporting:** Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
Ten days after returning home, all six guests receive what feels like a handwritten thank-you letter. Personal, warm, specific to their journey. It references the canal transit, the holiday voyage, the group dynamic. Then, naturally — not awkwardly — it asks if they have friends or family who love to travel and might benefit from D2M's service. The referral ask is brief, gracious, and never transactional. EXEC Naia's fingerprints are visible in the elevated voice.

#### Layer 2 — Staff View
Dani and Naia co-own this touchpoint. Dani drafts; Naia voice-reviews for the highest standard of voice quality in the lifecycle. Survey results from TP 5.2 (if received by Jan 10) inform the personal references in the letter. Hale runs WF-17. Commander approves and sends.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| Voice matching | `core/email/thunderbird_dani_voice.py` → `match_voice_profile()` |
| Persona engine (Naia) | `core/ai_infra/thunderbird_personas.py` → `instantiate_persona()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tool | `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | `dossiers/Kuklinski_Viking_Panama.md` — full lifecycle history |
| Data in | TP 5.2 survey responses (if received) — for personalization |
| Data in | Voice harvest — full relationship tone calibration |
| Processing | Dani drafts; Naia refines; Hale gates |
| Output | Thank you + referral email — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to all 6 guests |
| Storage | Dossier TP 5.3 marked SENT |

---

### TP 5.4 — Next Voyage Plant
**Status:** PENDING (search window Jan 11-25, 2027)  
**Send Date:** Jan 27, 2027  
**Owner:** A5 Viper  
**Supporting:** A2 Dembe (voyage research), A3 Dani (email), Hale (WF-17), Commander (send approval)

#### Layer 1 — Client View
Kyle Kuklinski receives a carefully curated next-voyage proposal. Not a generic catalog — a tailored suggestion based on everything D2M learned over nine months: the group's preference for group travel, their appetite for destination intensity, the age range across the group, the fact that Josh and Erica are coming from Florida, the Christmas voyage format. One or two voyage options are presented with enough detail to spark genuine interest. The lifecycle closes here — and a new one begins.

#### Layer 2 — Staff View
A5 Viper leads strategy — identifying voyage types, cruise lines, and price points that match Kuklinski preferences. A2 Dembe researches specific voyages and flights. A9 Harlan costs and validates commission. Dani formats the proposal. Hale runs WF-17. Commander approves. Send Jan 27.

#### Layer 3 — Code View
| Component | Detail |
|-----------|--------|
| Price monitoring | `core/intel/thunderbird_price_monitor.py` → `monitor_fare_trends()` |
| Ship intel | `core/intel/thunderbird_ship_intel.py` → `run_ship_intelligence_sweep()` |
| Flight search | `core/mcp/travel_mcp_server.py` → `search_flights()` |
| Hotel search | `core/mcp/travel_mcp_server.py` → `search_hotels()` |
| Email composition | `core/email/thunderbird_dani_email.py` → `compose_client_email()` |
| WF-17 quality gate | `core/email/thunderbird_presend_evaluator.py` → `run_wf17_gate()` |
| Draft creation | `core/email/thunderbird_gmail.py` → `create_gmail_draft()` |
| MCP tools | `search_flights`, `search_hotels`, `run_ship_intelligence_sweep`, `gmail_create_draft` |

#### Layer 4 — Data Flow
| Direction | Detail |
|-----------|--------|
| Data in | Full lifecycle preference data — all 9 months of Kuklinski context |
| Data in | TP 5.2 survey results — satisfaction scores, stated preferences |
| Data in | Viper strategic voyage analysis — cruise line, category, price range recommendation |
| Data in | Live cruise pricing and availability |
| Processing | A2 researches voyages; A9 costs; A5 validates strategy; Dani formats |
| Output | Next voyage proposal — draft in d2mconcierge Gmail |
| Output | Sent from concierge@d2mluxury.quest to Kyle Kuklinski |
| Storage | `dossiers/Kuklinski_Viking_Panama.md` — `lifecycle_closed: true` flag set |
| Storage | New dossier created if Commander approves next voyage |
| Storage | `THUNDERBIRD_MASTER_PLAN.md` — Kuklinski moved from active to completed bookings |

---

## APPENDIX A — WF-17 QUALITY GATE (APPLIED TO ALL CLIENT SENDS)

Every touchpoint that reaches a client passes through this gate before Commander sees it.

| Check | Standard | File |
|-------|----------|------|
| Logo renders | D2M navy banner renders in Gmail and all major clients | `thunderbird_presend_evaluator.py` |
| Sig block | concierge@d2mluxury.quest | `thunderbird_presend_evaluator.py` |
| Paper color | Cream #f7f3ea | `thunderbird_presend_evaluator.py` |
| Ink color | Bright blue #0000ff | `thunderbird_presend_evaluator.py` |
| Font | Georgia, serif | `thunderbird_presend_evaluator.py` |
| Sign-off | "Thanks" or "Thank you" — never "Best" | `thunderbird_presend_evaluator.py` |
| No AI disclaimer | Absent unless Commander adds as PS | `thunderbird_presend_evaluator.py` |
| No filler phrases | No "happy to help," no "certainly," no concierge announce | `thunderbird_presend_evaluator.py` |

---

## APPENDIX B — STAFF LOAD BY PHASE

| Phase | Window | Active Staff |
|-------|--------|-------------|
| Phase 0 (Onboarding) | Apr 17 – Apr 28 | Dani, Hale, Commander |
| Phase 1 (Discovery) | Apr 21 – Jun 17 | Dembe, Viper, Harlan, Dani, Hale, Commander |
| Phase 2 (Momentum) | May 5 – Sep 18 | Dembe, Luna, Harlan, Dani, Hale, Commander |
| Phase 3 (Pre-Departure) | Aug 25 – Dec 14 | Dembe, Luna, Naia, Dani, Hale, Commander |
| Phase 5 (Post-Voyage) | Dec 28 – Jan 27 | Gauge, Viper, Dembe, Naia, Dani, Hale, Commander |

---

## APPENDIX C — OPEN FLAGS

| Flag | Priority | Action Required |
|------|----------|-----------------|
| TP 0.6 Insurance OVERDUE | P0 | Dani to produce draft NOW — Commander approval needed urgently |
| Joshua Morton guest form MISSING | P1 | Follow up via TP 2.2 monthly validation; escalate if not received by Jul 1 |
| Erica Dodge guest form MISSING | P1 | Same as above |
| Flights NOT BOOKED (RIC-PTY, RSW-FLL) | P1 | Active search underway; send date Jun 17 |
| Hotels NOT BOOKED | P1 | Active search underway; send date Jun 17 |
| Transfers NOT BOOKED | P2 | Research window not yet open |
| Travel insurance NOT BOOKED | P0 | Blocked on TP 0.6 completion |

---

*Document: LIFECYCLE_PEEL_BACK — Kuklinski Viking Mars 2026 | Dreams2Memories Travel, LLC*  
*Owner: Col Victoria Hale, COS | Thunderbird Wing | Classification: INTERNAL*  
*Machine-readable companion: THUNDERBIRD_AI_MANIFEST.json*
