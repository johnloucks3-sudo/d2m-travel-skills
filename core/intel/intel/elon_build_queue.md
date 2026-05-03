
### ELON-2026-04-29-001 — OpenTravelData Entity Registry Integration
- **Status:** 🟡 PENDING
- **Date:** 2026-04-29
- **What:** Ingest OpenTravelData structured travel entities (airports, cities, cruise ports, routes) as a reference source for destination research and itinerary validation.
- **Why:** Closes post-2010 travel data deconfliction gap — LIFE archives drown in old media noise; OPTD provides clean, authoritative transport/leisure entity data.
- **How:** Create core/intel/thunderbird_opentraveldata_connector.py (HTTP fetch OPTD CSV/JSON datasets, local cache). Integrate into thunderbird_world_intel.py:run_world_intelligence_sweep() — add OPTD entity lookup phase before OSINT scraping. Extend thunderbird_dossier.py:validate_itinerary_data() to cross-check port codes / airport IATA against OPTD registry. Use stdlib requests + csv/json, zero new dependencies.
- **Effort:** MED · **SSS:** NO
- **A5 Fit:** ACCELERATES — Solves itinerary validation typos for current clients + builds reusable entity registry pattern; medium effort, zero dependencies, high quality lift.
- **A9:** APPROVED — Free data source, reasonable effort, clear payoff. No budget blocker. Aligns with ELON's 'why duplicate what's already built' principle. Build it. — NO — OpenTravelData is free/open-source. Zero service subscription required. · ROI: Operational efficiency: kills LIFE noise (old media deconfliction), catches airport/port typos before they hit TESS/booking systems. Prevents rework + client friction. A2 research gets cleaner entity data. One-time 2.5 hr cost pays itself back in first month through fewer validation loops.
- **ELON:** _Worth it. Free structured data that kills LIFE noise. ~2.5 hr build. Payoff: itinerary validation that catches port/airport typos before they hit booking systems._

### ELON-2026-04-30-001 — LuxuryEstate Portuguese Scraper
- **Status:** 🟡 PENDING
- **Date:** 2026-04-30
- **What:** Add Portuguese-language LuxuryEstate scraper to auto-enrich pipeline for Portuguese-speaking UHNW clientele preference inference
- **Why:** Closes gap on lifestyle signals from Portuguese luxury property market (Portugal, Brazil) for travel vector compounding and archetype refinement
- **How:** Extend core/client/thunderbird_auto_enrich.py → add scrape_luxuryestate_pt() function using BeautifulSoup + requests, pattern-matched to existing EN scraper. Feed results into incubator_lifestyle_signals memory store.
- **Effort:** LOW · **SSS:** NO
- **A5 Fit:** ACCELERATES — Pattern-scaling auto-enrich pipeline at LOW effort with immediate archetype-detection value for Brazilian/Portuguese prospect signals.
- **A9:** APPROVED — NO · ROI: Improved Portuguese UHNW lifestyle signal inference for Portugal/Brazil segment. ROI depends on pipeline volume (currently unknown).
- **ELON:** _Copy the English scraper, swap language param, done. High ROI capturing Brazilian/Portuguese UHNW with minimal effort._


### ELON-2026-04-30-002 — LuxuryEstate Italian Scraper
- **Status:** 🟡 PENDING
- **Date:** 2026-04-30
- **What:** Add Italian-language LuxuryEstate scraper to auto-enrich pipeline for Mediterranean travel archetype inference
- **Why:** Closes gap on lifestyle signals from Italian property market for Viking/Oceania/Seabourn clientele Mediterranean-preference compounding
- **How:** Extend core/client/thunderbird_auto_enrich.py → add scrape_luxuryestate_it() function using same BeautifulSoup pattern as PT scraper. Feed into incubator_lifestyle_signals.
- **Effort:** LOW · **SSS:** NO
- **A5 Fit:** ACCELERATES — Mediterranean property signals directly improve cruise-preference detection for current roster (Furlow, McLeod, etc.) — clean platform pattern at LOW cost.
- **A9:** APPROVED — NO · ROI: Strong Mediterranean cruise signal (Viking/Oceania/Seabourn segment). Larger market than PT. High-value profile enrichment.
- **ELON:** _Italian property = strong Mediterranean cruise signal. Identical copy/paste pattern to PT. Easy win._


### ELON-2026-04-30-003 — LuxuryEstate French Scraper
- **Status:** 🟡 PENDING
- **Date:** 2026-04-30
- **What:** Add French-language LuxuryEstate scraper to auto-enrich pipeline for French/Swiss/Monaco UHNW clientele preference inference
- **Why:** Closes gap on lifestyle signals from French luxury property market for European travel archetype compounding
- **How:** Extend core/client/thunderbird_auto_enrich.py → add scrape_luxuryestate_fr() function using same BeautifulSoup pattern. Feed into incubator_lifestyle_signals. RECOMMENDATION: consolidate all 4 languages into single scrape_luxuryestate_multilingual(languages=['en','pt','it','fr']) function instead of four separate functions.
- **Effort:** LOW · **SSS:** NO
- **A5 Fit:** ACCELERATES — European market signals feed Scandinavia/Ponant archetype inference; identical low-effort pattern-match with immediate client-targeting ROI.
- **A9:** APPROVED — NO · ROI: French/Swiss/Monaco UHNW targeting. Strong fit for Ponant & luxury European cruises (core D2M product line).
- **ELON:** _Third identical pattern. Stop copy/pasting. Consolidate into one multilingual function with language list param before hitting merge._


### ELON-2026-04-30-004 — LuxuryEstate Signal Quality Layer - Dedup & Filter
- **Status:** 🟡 PENDING
- **Date:** 2026-04-30
- **What:** Build entity deduplication and pop-culture signal filtering layer to handle 79.9k French market listing corpus without noise bleed
- **Why:** Closes gap on infrastructure to ingest high-volume French property listings while filtering duplicates and celebrity/landmark contamination that pollutes travel preference signals
- **How:** Create core/client/incubator_signal_quality_layer.py → (1) deduplicate_listings(listings) using Levenshtein distance on (address, price, sqm) to identify duplicates with configurable threshold, (2) filter_pop_culture_bleed(listings) using keyword blacklist (celebrity home, château historique, musée, landmark, famous residence). Integrate post-scrape in thunderbird_auto_enrich.py call chain. Store quality thresholds and filter rules in config.
- **Effort:** MED · **SSS:** YES
- **A5 Fit:** ? — 
- **A9:** ? —  · ROI: 
- **ELON:** _79k listings = real scale. Raw dump = garbage signal. Dedup + filter is non-negotiable. Requires SSS approval on: (1) storage cost for listing corpus, (2) entity resolution compute (Levenshtein is O(n²) without indexing), (3) quality threshold validation to ensure dedup+filter doesn't over-reduce signal corpus below utility._

### ELON-2026-05-02-001 — Android Private Space Signal — HNWI Privacy Compartmentalization Detection
- **Status:** 🟡 PENDING
- **Date:** 2026-05-02
- **What:** Detect and flag when HNWI clients use Android Private Space (encrypted app/data hiding) as privacy preference signal for profile enrichment.
- **Why:** Closes gap in HNWI profile inference — compartmentalization desire signals security-conscious, high-net-worth profile; enables Dani to tailor privacy-forward copy + compliance messaging.
- **How:** Add 'android_private_space' boolean field to thunderbird_recipient_profiles.py::RecipientProfile dataclass. Integrate into guest_intake_form (checkbox: 'I use Android Private Space for sensitive apps'). Hook into life_event_trigger_crm.py::enrich_profile_from_signals() to boost privacy_preference_score. Store in dossier JSON under client.privacy_signals.
- **Effort:** LOW · **SSS:** YES
- **A5 Fit:** ACCELERATES — Serves current HNWI clients + builds reusable signal-inference pattern; gate on privacy policy amendment before form deploy.
- **A9:** FLAG_FOR_COMMANDER — NO - $0/mo · ROI: HNWI profile inference closure → better privacy-conscious client targeting → improved retention + compliance messaging fit
- **ELON:** _Ask don't infer — we have zero device telemetry. One checkbox in intake form, zero API complexity. But flag: privacy signal collection itself needs privacy policy amendment + Commander sign-off before we touch client-facing forms._
