# SO-2026-07-24: D2M Itinerary Image Composition Standard
**Document:** SO-ItineraryImages_v1
**Owner:** CMSgt Steve "Silver" Sterling (image QC) | **Drafted by:** Hale (COS)
**Approved:** Commander | **Effective:** 2026-07-24 | **Version:** 2.0
**Binding on:** All Wing staff and AI producing client cruise itinerary HTML documents

---

## 1. PURPOSE

Codify the mandatory image composition standard for D2M luxury itinerary documents.
Issued after 4 consecutive failures on Grandeur Scandinavia itineraries (Jul 2026).
Version 2.0 adds full autonomous sourcing authority — AI goes all the way without stopping to ask.

---

## 2. CORE DOCTRINE — TWO PHOTOS PER PORT, MINIMUM

Every port or destination in a client itinerary requires **at minimum 2 photos**:

| Slot | Type | Standard |
|------|------|----------|
| **Photo A** | Iconic landmark, scene, or location | Recognizable, specific to this port. No generic shots. No wrong-season images. No wrong-city images. |
| **Photo B** | Emotional / dreamy | Calming, evocative of the luxury cruise experience — sea light, cobblestones, café terraces, golden hour. Connects to the feeling of being there, not just the facts. |

**Zero tolerance:**
- No duplicate images across any slot in the same document
- No images from the wrong city or country
- No winter/snow images for summer voyages
- No protest crowds, construction sites, or negative contexts
- No portrait-orientation images (landscape only, 16:9 preferred)
- No images with competitor cruise line livery visible

---

## 3. OVERNIGHT PORTS — 4 PHOTOS REQUIRED

When a port is an overnight call (two consecutive days in port), it receives **4 different photos**:

- Day 1 morning card: Photo A (iconic) + Photo B (emotional)
- Day 1 evening / Day 2 card: Photo C (second iconic angle, different landmark, or excursion scene) + Photo D (second emotional — different mood than B)

All 4 must be distinct subjects. No reuse across the 4 slots.

---

## 4. STOCKHOLM PRE-CRUISE NIGHTS — SPECIAL TREATMENT

Stockholm is often a multi-night pre-cruise embarkation city. When clients have 2+ pre-cruise nights in Stockholm, the image set expands to include:

1. **City Hall / waterfront** — Stadshuset at golden hour or tall ships on Riddarfjärden
2. **Gamla Stan** — Stortorget square, colorful facades, or medieval alley (summer/golden light only)
3. **At Six Hotel or Östermalm** — hotel exterior, rooftop bar, or designer street scene. ONLY use an image that shows the actual At Six property or its immediate Östermalm neighborhood. NEVER use an image showing a different hotel's name/signage.
4. **Atmospheric/dreamy** — archipelago, evening light, waterfront café, or lifestyle shot

If no verified At Six image exists after exhausting all sources below, use a premium Östermalm/Kungsgatan street scene instead. Document the gap in the action items.

---

## 5. IMAGE SOURCING HIERARCHY — FULLY AUTONOMOUS, NO STOPS

AI executes this entire ladder before surfacing any gap to Commander. Work top-to-bottom; only escalate if all tiers fail.

### Tier 1 — Local library (fastest, free, pre-verified)
```
storage/output/[ship]_imgs/           # Ship-specific verified assets
grandeur_baltic_imgs/                 # Grandeur Scandinavia curated set
candidates/                           # Session-sourced candidates
storage/output/Grandeur_Scandinavia_Portal/assets/  # Portal ship interiors
cruises_web/assets/                   # Active itinerary assets
```
Command: `find /home/john/Thunderbird -name "*.jpg" -o -name "*.png" | xargs ls -la`
View every candidate with Read tool before accepting. Season, subject, quality — all must pass gate.

### Tier 2 — McLeod + Loucks gold-standard itineraries
- **McLeod itinerary** — most current gold standard; inspect image choices before sourcing
- **Loucks itinerary** — 19 verified images, correct port-per-slot architecture
- Extract their image URLs/IDs and reuse or use as search-term inspiration

### Tier 3 — Pexels API (free, high-res, licensed)
```bash
curl -H "Authorization: $PEXELS_API_KEY" \
  "https://api.pexels.com/v1/search?query=QUERY&per_page=15&orientation=landscape"
```
Download with: `curl -L -o filename.jpg "$photo.src.large2x"`
Rate limit: 200 req/hour. If 429 → wait 30s and retry once → if still failing, go to Tier 4.

**Search query templates by port:**
| Port | Photo A (iconic) | Photo B (dreamy) |
|------|-----------------|-----------------|
| Stockholm | `stockholm city hall sunset summer` | `stockholm gamla stan golden hour cobblestone` |
| Warnemünde | `warnemunde lighthouse beach chairs Baltic` | `warnemunde pier sunset Baltic Sea` |
| Berlin | `Brandenburg Gate twilight illuminated` | `berlin unter den linden summer trees` |
| Copenhagen | `nyhavn copenhagen colorful houses canal` | `copenhagen tivoli night lights magical` |
| Oslo | `oslo opera house summer golden` | `oslo fjord sailboats sunset` |
| Kristiansand | `kristiansand posebyen white houses Norway` | `kristiansand Norway coastal cliffs summer` |
| Helsinki | `helsinki cathedral senate square summer` | `helsinki market square waterfront summer` |
| Tallinn | `tallinn old town medieval towers summer` | `tallinn town hall square golden hour` |

### Tier 4 — Wikimedia Commons (verified open license, landmark photos)
Search: `https://commons.wikimedia.org/wiki/Special:Search?search=QUERY&ns6=1`
API: `https://en.wikipedia.org/w/api.php?action=query&prop=images&titles=CITY_NAME&format=json`
Download direct from Commons URL. License: CC BY-SA (no attribution required for internal/client docs in D2M context — for public web, add caption).
Best for: landmark architecture, historic city centers, official tourism photography.

### Tier 5 — Unsplash (free, editorial-quality, no key required for single downloads)
Search: `https://unsplash.com/s/photos/QUERY`
Direct download: Right-click "Download free" on any image. Resolution: 4000px+ standard.
API (if key available in `.env`): `https://api.unsplash.com/search/photos?query=QUERY&orientation=landscape`
Best for: golden-hour lifestyle, café culture, dreamy atmospheric shots.

### Tier 6 — OpenVerse (WordPress open image commons)
Search API: `https://api.openverse.org/v1/images/?q=QUERY&aspect_ratio=wide&license_type=commercial,modification`
No key required. Returns CC0 and CC-BY images only — safe for all use.
Best for: broader coverage when Pexels/Unsplash miss a specific port.

### Tier 7 — Flickr Creative Commons
Search: `https://www.flickr.com/search/?text=QUERY&license=4%2C5%2C6%2C9%2C10` (CC licenses)
Use bsk (browser-skill) to scrape if needed: `bsk navigate "https://www.flickr.com/search/..." --session ID`
Best for: niche ports, local photography, interior venue shots.

### Tier 8 — NASA Earth Observatory / NOAA (aerial/satellite, select ports)
`https://earthobservatory.nasa.gov/images` — all public domain
Use for: dramatic aerial approaches to coastal cities (Oslo fjord, Stockholm archipelago).

### Tier 9 — Google Maps Street View (approved 2026-07-26, Commander directive)
Access via `bsk` browser automation or Maps Static API.
Use for: street-level scenes of port neighborhoods, hotel exteriors (At Six Östermalm), local streets, market squares, harborfront walking views.
Technique: `bsk navigate "https://www.google.com/maps/@LAT,LNG,3a,75y,HEADING,90t/data=..." --session ID` → `bsk screenshot --session ID`
Best for: verifying the EXACT neighborhood/hotel/street clients will experience. No guessing.

### Tier 10 — Google Earth (aerial/satellite) (approved 2026-07-26, Commander directive)
Access via Google Earth web (`earth.google.com`) using `bsk` browser automation, or via Google Earth Engine public assets.
Use for: fjord approach views, archipelago bird's-eye, coastal geography, island clusters (Oslofjord, Stockholm archipelago).
Best for: "what they see sailing in" slot — the aerial approach perspective complements the ground-level sail-in shot.
Note: Screenshot must be cropped to landscape orientation. No Google watermark should dominate the frame — zoom/angle to minimize.

### Fallback protocol
If all 8 tiers fail for a specific slot:
1. Use the best available near-match (same country, similar mood, same season)
2. Document as action item: `IMAGE GAP: [port] [slot] — best available substituted, original subject not found`
3. Do NOT leave a blank slot or embed a placeholder

---

## 6. SELF-ENFORCING QUALITY GATE

AI must answer YES to all before embedding any image. This is a hard stop — no exceptions.

- [ ] **Correct location?** This is unambiguously the right city/country for this port day.
- [ ] **Correct season?** Summer (June–September) for Aug/Sep voyages. Warm light, full foliage, clear skies.
- [ ] **Unique?** This Pexels ID / URL / filename does not appear anywhere else in this document.
- [ ] **Correct subject?** Photo A clearly identifies the destination. Photo B evokes calm, luxury, or wanderlust.
- [ ] **Correct orientation?** Landscape (wider than tall). Portrait images are disqualifying.
- [ ] **No defects?** No protest crowds, construction cranes, scaffolding, industrial equipment, competitor logos.
- [ ] **Overnight completeness?** If overnight port: confirmed 4 distinct images covering 2 pairs, all unique subjects.
- [ ] **Hotel images verified?** If a hotel is shown, its actual name/signage has been visually confirmed or the image has no hotel branding visible.

---

## 7. SILVER STERLING REVIEW — IMAGE QC GATE

**Reviewer: CMSgt Steve "Silver" Sterling** — Wing image curator. NOT CMSgt Thomas "Gauge" Sterling (A7/code auditor — separate role, invoked only for code, SO authorship, and process compliance). Do not confuse these two personnel.

### Before/After Review (mandatory for every itinerary image build):
- **BEFORE embedding:** Silver Sterling evaluates the full proposed image roster against this SO — correct port, correct season, unique, no defects, correct slot count (2 per single-day, 4 per overnight).
- **AFTER embedding:** Silver Sterling spot-checks 3–5 rendered images per file in the browser; confirms no compression artifacts, no wrong-aspect-ratio crops, no images that "read wrong" at display size even if they passed the static file check.

### What Silver Sterling does NOT block:
- Sourcing decisions mid-ladder (AI works Tiers 1–8 autonomously)
- Individual download decisions
- Commander review (WF-17) — that gate is independent

### What Gauge Sterling (A7) does NOT touch here:
- Image selection, quality, composition, or sourcing decisions — none of that is his lane
- Gauge is invoked only if the SO file itself needs amendment or a code/process violation is flagged

AI proceeds: source → self-gate (§6) → Silver Sterling before/after review → embed → WF-17. No Commander intervention in image sourcing.

---

## 8. FAILURE LOG

| Date | Failure | Root Cause |
|------|---------|------------|
| 2026-07-24 (×4) | Grandeur Scandinavia — wrong images, duplicates, single image per port | AI did not follow 2-per-port rule; duplicated instead of sourcing; no Sterling review invoked |
| 2026-07-24 | Brandenburg Gate slot contained Paris Eiffel Tower photo | Pexels ID mismatch — image not visually verified before embedding |
| 2026-07-24 | Romance narrative replaced entire itinerary content | AI rewrote instead of editing existing `cruises_web/` file |
| 2026-07-26 | Images still had duplicates, bland shots, incorrect counts after multiple passes | AI looped without using staff (Silver Sterling) or following 2-image/4-image per port rule; SO §2/§3 and staff gate not enforced |
| 2026-07-26 | Romance narrative identical across all 3 days of Stockholm port | Narrative must be distinct per day, tied to each day's excursion — "Venice of the North" repeated 3x is a failure; overnight ports require day-specific romance copy |

---

## 10. ROMANCE NARRATIVE STANDARD

### 10.1 Core Rule — Unique per day, tied to the excursion
Every port-day card requires its own narrative paragraph. **Never reuse narrative copy across multiple days at the same port.** An overnight port with 2 days gets 2 distinct paragraphs — one per day, each tied to what that couple actually does that day.

### 10.2 Narrative must tie to the booked excursion
If a client has a confirmed excursion on a port day, the narrative **references that excursion** — departure time, destination, key sights. Generic "explore the city" copy is a failure when a specific excursion is booked.

| Excursion status | Narrative approach |
|---|---|
| **Confirmed excursion** | Name the excursion, state the departure time, name 1–2 specific sights they will see |
| **No excursion** | Describe 2–3 specific things they can do or see independently; still port-specific, not generic |

### 10.3 Multi-night port differentiation (Stockholm rule)
Stockholm (and any multi-night pre-cruise city) requires distinct narratives for each night/day:

| Slot | Content focus |
|---|---|
| **Arrival night (At Six)** | Hotel neighborhood (Östermalm), Capital District feel, first evening |
| **Free day (pre-cruise)** | What they do exploring independently — boat tour, Djurgården, Gamla Stan |
| **Embarkation day** | Boarding the ship, suite arrival, evening at sea |
| **Day 1 aboard at port** | First excursion or first day activity; Pacific Rim dinner if applicable |

Repeating "the beautiful capital" or "cobbled streets" across all 4 Stockholm slots is a violation of this SO.

### 10.4 Forbidden narrative patterns
- Clichéd opener: "Venice of the North," "gem of the Baltic," "stunning," "breathtaking," "magical" (use sparingly and only if precise)
- Repeating the same sentence, phrase, or structure across days
- Generic "explore the city at your leisure" without naming specific places
- Future-tense hype ("you'll discover...") — prefer present-tense active ("the guided walk traces...")
- Overlong paragraphs — **max 3–4 sentences, 1 paragraph per slot**

### 10.5 Image–narrative sync
The port image(s) must show what the narrative describes. If the narrative mentions Kronborg Castle, at least one image should show a castle. If the narrative describes a sail-in arrival, at least one image should show the approach view (islands, lighthouse, waterfront).

**Sail-in images:** For ports with scenic approaches (Oslofjord, Stockholm archipelago, Kristiansand inlet), at least one image per port should show the approach view — islands, lighthouse silhouettes, coastal villages, forested shores — not just the city center. This is what they actually see from the ship.

### 10.6 Staff chain for romance narratives
Research (Dembe A2) → Narrative draft (Luna A6) → D2M voice pass (Dani A3) → WF-17

Invoke via `/ask` with the full excursion map per couple. Dembe provides confirmed excursion times and port facts. Luna writes the paragraph. Dani applies brand voice. AI does not self-loop without staff review on romance narrative copy.

### 10.7 Per-couple differentiation
When clients share a port day but have different booked excursions, each couple receives their own narrative for that day. The HTML files for each client are separate documents and should reflect that client's actual itinerary.

---

## 9. AMENDMENT HISTORY

| Date | Change | Authority |
|------|--------|-----------|
| 2026-07-24 | v1.0 — Initial SO created after 4th image failure | Commander directive |
| 2026-07-24 | v2.0 — Full autonomous sourcing hierarchy added; Sterling gate moved to WF-17 only; commons solutions added; self-enforcing quality gate codified | Commander directive — "revise SO so I do not have to intervene" |
| 2026-07-24 | v2.1 — Corrected reviewer attribution: CMSgt Steve "Silver" Sterling (image QC) owns §7, NOT Gauge Sterling (A7). Before/after review protocol added. Silver/Gauge lane separation enforced. | Commander directive — "Make sure CMSgt Steve Silver Sterling is involved in the before/after — not A7 Thomas Gauge Sterling" |
| 2026-07-26 | v2.2 — Added Tier 9 (Google Maps Street View) and Tier 10 (Google Earth/satellite) as approved autonomous sourcing sources. All Wikimedia Commons, Google Maps, and Google Earth images pre-approved. 5th failure logged: port romance narratives repeated verbatim across multi-day port stays — SO §2/§3 updated to mandate distinct excursion-tied narrative per day for overnight ports. | Commander directive — "ALL Commons images, Google Maps Images, Google Earth, add to the SO are approved" |
| 2026-07-26 | v2.3 — Added §10 Romance Narrative Standard: unique per-day, tied to booked excursion, forbidden patterns codified (clichés, repeats, vague generic copy), image–narrative sync requirement, sail-in image doctrine, staff chain (Dembe→Luna→Dani), per-couple differentiation rule. Failure logged: identical narrative across all 3 Stockholm overnight days = SO violation. | Commander directive — "more creative with the romance, tie it to excursions… you MUST use appropriate staff, don't just make this stuff up in your own little loop. This all needs to go into the SO." |
