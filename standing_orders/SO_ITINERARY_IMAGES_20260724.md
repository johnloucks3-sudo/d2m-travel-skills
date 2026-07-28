# SO-ITINERARY-IMAGES — Cruise Itinerary Image Standards
**Effective:** 2026-07-24 | **Version:** 2.0 | **Owner:** Sterling | **Authority:** Commander directive 2026-07-24
**Canonical document:** `ops/SO-ItineraryImages_v1.md` — this file is a summary reference only.

---

## MANDATORY IMAGE STRUCTURE

### Per-Port Requirement (2-image minimum)
Every port section must have exactly **2 paired images**:
1. **Iconic** — a landmark, scene, or location. Instantly recognizable. Something the client can point to and say "I was there."
2. **Emotional/Dreamy** — evokes the feeling of cruising and touring. Calming, aspirational. Makes the client want to be there.

Both images must be **different subjects**. No two slots in the same port may show the same landmark or scene.

### Overnight Ports (2+ nights) — 4-image requirement
Ports where clients spend 2 or more nights require **4 UNIQUE images** (2 pairs):
- Pair 1: iconic landmark + emotional scene
- Pair 2: second iconic landmark or neighborhood + second emotional/dreamy shot

All 4 must be distinct subjects. No reuse.

### At-Sea / Travel Days — Ship imagery only
- Sea days and embarkation/disembarkation days use **Grandeur ship imagery only**
- Rotate between exterior shot and interior venue (dining, observation lounge, etc.)
- No port images on sea days

---

## IMAGE SOURCING — FULLY AUTONOMOUS (AI DOES NOT STOP TO ASK)

Work this ladder top-to-bottom. Commander never intervenes in image sourcing.

1. **Local library** — `grandeur_baltic_imgs/`, `candidates/`, `storage/output/[ship]_imgs/`, portal assets
2. **McLeod + Loucks gold-standard itineraries** — inspect their choices first
3. **Pexels API** (`PEXELS_API_KEY` in `.env`) — landscape orientation, summer, specific port terms
4. **Wikimedia Commons** — `commons.wikimedia.org/wiki/Special:Search` — landmark architecture, CC-licensed
5. **Unsplash** — `unsplash.com/s/photos/QUERY` — lifestyle, golden hour, dreamy atmospheric
6. **OpenVerse** — `api.openverse.org/v1/images/` — CC0/CC-BY, no key required
7. **Flickr CC** — search with `license=4,5,6,9,10` filter for commercial CC licenses
8. **NASA/NOAA** — aerial coastal approaches, all public domain
9. **Google Maps Street View** — `bsk navigate "https://www.google.com/maps/..."` → `bsk screenshot`. Use for hotel exteriors (At Six Östermalm), port neighborhoods, harborfront walking views. Pre-approved 2026-07-26.
10. **Google Earth** — aerial/satellite via `earth.google.com` + bsk. Use for fjord approaches, archipelago bird's-eye, coastal geography (Oslofjord, Stockholm archipelago). Pre-approved 2026-07-26.

If all 10 tiers fail: use best near-match + log `IMAGE GAP: [port] [slot]` in action items.

---

## SELF-ENFORCING QUALITY GATE (AI checks before embedding)

- [ ] Correct city/country for this port day?
- [ ] Summer season (warm light, full foliage, clear skies)?
- [ ] Unique — not used elsewhere in this document?
- [ ] Photo A clearly identifies the destination?
- [ ] Photo B evokes calm, luxury, or wanderlust?
- [ ] Landscape orientation (not portrait)?
- [ ] No defects (cranes, crowds, competitor logos, wrong hotel signage)?
- [ ] Overnight port: 4 distinct images confirmed?

---

## IMAGE QUALITY STANDARDS

- **Season match:** August voyages = summer images only. No bare trees, snow, gray skies.
- **No duplicates:** Every image across the entire itinerary must be unique.
- **No wrong cruise lines:** No ships with competitor livery visible.
- **No wrong hotels:** Hotel images must show the actual property or no branding at all.
- **Orientation:** Landscape only (16:9 preferred). Portrait = disqualified.
- **Resolution:** Minimum 1280px wide. Prefer 1920px+.
- **Tone:** Warm, inviting, aspirational. No heavy filters, no HDR gimmicks.

---

## STOCKHOLM SPECIAL RULE
Stockholm 3-night pre-cruise stay with At Six hotel (Östermalm). 4 images required:
1. City Hall / harbor waterfront (golden hour)
2. Gamla Stan (Stortorget square or medieval alley, summer light)
3. At Six exterior or Östermalm street scene (NO competing hotel signage)
4. Atmospheric/dreamy (archipelago, evening, lifestyle)

---

## SILVER STERLING REVIEW (IMAGE QC)
**Reviewer: CMSgt Steve "Silver" Sterling** — NOT Gauge Sterling (A7). Two different people.
- **Gauge Sterling (A7):** code, SO authorship, process compliance. Does NOT touch image decisions.
- **Silver Sterling:** image curator. Owns before/after QC on every itinerary image build.

**Before embedding:** Silver evaluates full proposed image roster against this SO.
**After embedding:** Silver spot-checks 3–5 rendered images in browser — confirms no artifacts, no wrong crops, no images that "read wrong" at display size.

AI proceeds autonomously through sourcing (Tiers 1–8) → self-gate → Silver before/after → WF-17. Commander does not intervene in sourcing.

---

## FAILURE LOG
- **2026-07-24 (×4):** Grandeur Scandinavia — wrong images, duplicates, single image per port, Paris Eiffel Tower in Berlin slot. Founding instance of this SO.

---

*Filed by: Hale-OC | v2.0 updated Commander directive 2026-07-24 | v2.1 Silver/Gauge lane separation corrected 2026-07-24 | Image QC owner: Silver Sterling | SO authorship owner: Gauge Sterling | Canonical: ops/SO-ItineraryImages_v1.md*
