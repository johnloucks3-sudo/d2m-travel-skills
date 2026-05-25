# D2M WEB PRESENCE ARCHITECTURE BRIEF
## Dreams2Memories Travel, LLC · Commander Directive — 2026-05-25
## Author: A13 Sienna Navarro | Reviewed by: A6 Luna Voss | Routing: Hale → Commander

---

## EXECUTIVE SUMMARY

D2M has a cruise intel pipeline with 205+ sailings across 13 lines, a deployed itinerary tunnel, a full AI concierge in Dani, and a social media director (A13) who will drive traffic the moment she has a destination to point at. The missing piece is a public web app that converts that traffic into inquiries.

This brief defines the two-track approach: a MAGtap stopgap activated immediately (2-3 hours), and `app.d2mluxury.quest` — the real D2M web application — built in parallel on Commander's existing YOGA infrastructure.

**Commander's three-layer architecture:**
1. Social (A13 Sienna) — drives qualified traffic
2. Web app (`app.d2mluxury.quest`) — captures and converts
3. Cruise intel pipeline — the search/discovery engine no competitor can replicate

---

## TRACK 1: MAGTAP STOPGAP (Activate Now — 2-3 Hours)

### What MAGtap My Site Is
MAGtap's hosted agent website — pre-configured template, pre-linked to TESS booking system, activatable within a working session.

### What It Does Well
- Gets D2M online immediately
- Provides a bookable link for Dani to share
- Satisfies the "do you have a website?" question from prospective clients
- Costs effectively nothing in build time

### What It Does Not Do
- No cruise intel search (no 205-sailing discovery layer)
- No Dani chatbot embed (no D2M conversational voice)
- No SEO blog section for A13's content
- No custom brand expression — looks like every other MAGtap agent site
- Cannot be the destination A13 drives traffic to at scale

### Decision
**Activate MAGtap My Site immediately.** It is the stopgap that buys time while the real app is built. Do not overinvest in it. Populate the profile, add a professional photo and bio, link it in Dani's email signature and A13's social bios.

**Subdomain:** `mags.d2mluxury.quest` or MAGtap's hosted URL — do not use `app.d2mluxury.quest` for this. That subdomain is reserved for the real app.

**Time to activate:** 2-3 hours. Owner: Hale. A7 Sterling reviews before go-live.

---

## TRACK 2: `app.d2mluxury.quest` — THE REAL D2M WEB APP

### Infrastructure Foundation
D2M already owns everything needed to build this:
- **YOGA server** (192.168.1.198) — backend host
- **Cloudflare tunnel** — already deployed (`api.d2mluxury.quest` live)
- **Itinerary tunnel** — already live at `itinerary.d2mluxury.quest`
- **Cruise intel pipeline** — 205+ sailings, 13 lines, scraped and structured
- **Dani** — conversational layer ready to embed

The app is not a greenfield build. It connects existing infrastructure to a public-facing surface.

---

## TECH STACK RECOMMENDATION

### Backend
**FastAPI (Python)** on YOGA 192.168.1.198

Rationale: D2M's entire codebase is Python. The cruise intel pipeline, dossier system, and Thunderbird core modules are all Python. A FastAPI backend is consistent with the existing stack, deployable by A7 Sterling without introducing a new language runtime, and fast enough for all D2M use cases.

```
/home/john/Thunderbird/app/
├── main.py              # FastAPI app entry point
├── routers/
│   ├── cruise.py        # Cruise intel search API
│   ├── intake.py        # "Request a Voyage" form handler
│   ├── blog.py          # Blog post API (feeds frontend)
│   └── dani.py          # Dani chatbot proxy endpoint
├── models/              # Pydantic data models
├── core/                # Shared utilities (pulls from existing core/)
└── static/              # Compiled frontend assets
```

**Systemd service:** `app-d2mluxury.service` — mirrors pattern of `thunderbird-mcp.service`

### Frontend
**Vanilla HTML/CSS/JS + minimal Alpine.js** for reactive components (search, chatbot, form)

Rationale: Avoids a full React build pipeline that requires Node.js, npm management, and A7 Sterling's time on frontend tooling. Alpine.js (7KB) handles the interactive pieces. The site is primarily content — cruise discovery, itinerary showcase, contact form. Server-side rendering via FastAPI Jinja2 templates covers 80% of it.

If Commander later decides to upgrade to React/Next.js for a richer SPA experience, the FastAPI backend stays unchanged. The frontend is the replaceable layer.

### Cloudflare Tunnel
`app.d2mluxury.quest` → YOGA:8080 (FastAPI)

Same pattern as `api.d2mluxury.quest`. A7 Sterling adds the route to the existing tunnel config. Zero new infrastructure cost.

### Database
**SQLite** for MVP (cruise intel data is already structured here via existing pipeline)

Upgrade path: PostgreSQL when concurrency demands it. Not needed for Phase 1.

---

## CORE MVP FEATURES

### Feature 1: Cruise Intel Search
**What it is:** A searchable, filterable interface over D2M's 205+ sailing database.

**User experience:** Visitor enters destination, travel window, approximate budget. Results display sailings with ship, line, dates, and cabin categories. Each result has a "Request This Voyage" CTA that feeds directly into the D2M intake pipeline.

**Backend:** FastAPI endpoint queries the existing cruise intel SQLite database.

**Competitive advantage:** No other 1-person agency has a proprietary search engine built on their own scraped intelligence. MAGtap agents send clients to cruise line websites. D2M shows them 13 lines at once, filtered by the client's actual parameters.

**Staff dependency:** A2 Dembe's pipeline must continue feeding the database. A7 Sterling builds the search endpoint and connects it to the existing data structure.

### Feature 2: Dani Chatbot Embed
**What it is:** A booking inquiry chatbot on `app.d2mluxury.quest` powered by Dani's voice and backed by the Thunderbird intelligence layer.

**User experience:** Floating chat button on all pages. Opens a conversational interface. Dani collects trip parameters, answers cruise questions, and routes qualified inquiries to d2mconcierge@gmail.com for follow-up.

**Backend:** FastAPI `/dani` endpoint proxies to the Thunderbird Dani engine (existing `core/email/thunderbird_dani_engine.py` — adapt for HTTP rather than email trigger).

**Gate:** All inquiries that come through the chatbot are WF-17 flagged — they surface to Commander before any client commitment. Dani gathers; she does not commit.

**Note:** Public Dani (web chatbot) has different context than the email Dani. She does not have access to booking history for anonymous visitors. She operates in intake mode: qualify, gather, delight.

### Feature 3: Itinerary Showcase
**What it is:** A curated gallery of D2M-produced client itineraries — the work product that demonstrates the agency's quality.

**User experience:** "Our Work" section. Thumbnail cards linking to full itinerary HTML (served from `itinerary.d2mluxury.quest`). Each card shows ship, destination, and a one-line narrative from Luna.

**Backend:** Static links to existing itinerary tunnel. No database needed — curate manually, update quarterly.

**Content dependency:** Luna A6 curates which itineraries are showcase-ready. Commander approves before any client itinerary goes public (confirm client consent).

### Feature 4: "Request a Voyage" Form
**What it is:** The primary conversion point — a structured intake form that feeds D2M's booking pipeline.

**Fields:** Name, email, phone, destination or ship interest, travel window, approximate budget, party size, any comments.

**Backend:** FastAPI `/intake` endpoint writes form submission to a queue file → Hale picks up within 2 hours → routes to A1 Navarro for profile creation → Dani gets briefed before first contact.

**This is a Gate 3 trigger** — new client first contact. Commander is notified on every form submission before any response goes out.

**SEO value:** A well-structured intake form on a properly-indexed page is a keyword magnet for "luxury cruise travel agent" + destination combinations.

### Feature 5: SEO Blog Section
**What it is:** `/blog` — A13's content channel, published on the D2M domain for full SEO attribution.

**Structure:** Article cards on index page, full articles at `/blog/[slug]`. Optimized title tags, meta descriptions, structured data markup.

**Cadence:** One post per week from A13 Sienna. 1,200-1,500 words. Long-tail terms: "best time to cruise Norway," "Regent vs Silversea what's the difference," "seven seas grandeur review 2027."

**Backend:** FastAPI Jinja2 templates rendering from Markdown files (or a lightweight headless CMS if A7 deems it warranted). Keep it simple.

**Content flow:** Dembe research → Sienna draft → Naia brand pass → A7 publishes → Sienna promotes on LinkedIn and Pinterest.

---

## A13 SOCIAL → APP TRAFFIC FUNNEL

Sienna's seven platforms all converge on one destination: `app.d2mluxury.quest`.

```
Instagram Bio Link → app.d2mluxury.quest
LinkedIn CTA → blog posts at app.d2mluxury.quest/blog/[slug]
Pinterest pins → cruise intel search at app.d2mluxury.quest/search
YouTube descriptions → "Request a Voyage" form
TikTok bio → app.d2mluxury.quest
Facebook Group → pinned post with app link
"The D2M Dispatch" newsletter → monthly featured voyage link to search
```

**UTM parameters:** A13 uses UTM tracking on all social links so the weekly performance report shows which platform is driving actual form submissions, not just impressions. Format: `?utm_source=instagram&utm_medium=bio&utm_campaign=organic`.

**Paid funnel:** Meta Ads and LinkedIn Ads link directly to either a specific search result or the "Request a Voyage" form, depending on campaign objective.

**The feedback loop:** Social drives traffic → app converts → Dani books → client story goes to Dani → A13 gets approved social proof → social gets stronger. The engine compounds.

---

## BUILD TIMELINE

### Phase 1 — Now (Week 1-2)

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Activate MAGtap My Site | Hale | 2-3 | Stopgap live, linked in Dani signature |
| Register `app.d2mluxury.quest` in Cloudflare tunnel | A7 Sterling | 1 | Subdomain route to YOGA:8080 |
| Scaffold FastAPI app with Jinja2 templates | A7 Sterling | 4-6 | Bare app serving at `app.d2mluxury.quest` |
| Placeholder homepage with "Request a Voyage" form | A7 Sterling | 3 | First conversion point live |
| Intake form backend → queue file → Hale notification | A7 Sterling | 2 | Gate 3 compliant intake |
| A13 social bios updated with app URL | A13 Sienna | 1 | Traffic begins routing |

**Phase 1 exit condition:** `app.d2mluxury.quest` is live, serving a real homepage, and the intake form works end-to-end. A13 can start routing social traffic to it.

### Phase 2 — 30 Days

| Task | Owner | Hours | Deliverable |
|------|-------|-------|-------------|
| Cruise intel search UI (connected to existing data) | A7 Sterling | 8-10 | Search working with real sailing data |
| Dani chatbot embed (intake mode) | A7 Sterling | 6-8 | Chatbot live on all pages |
| Itinerary showcase section | A7 Sterling | 4 | Commander-approved itineraries on display |
| Blog section + first 4 posts published | A13 Sienna | ongoing | `/blog` live with SEO-structured content |
| UTM tracking on all A13 social links | A13 Sienna | 2 | Attribution data begins flowing |
| "The D2M Dispatch" first edition deployed | A13 Sienna | 4 | Newsletter live to TESS import list |
| Google Business Profile fully populated | A13 Sienna | 2 | 5-star review campaign launched |

**Phase 2 exit condition:** The three competitive differentiators are live — cruise intel search, Dani chatbot, and SEO blog. The app is genuinely useful and distinct from MAGtap.

### Phase 3 — 90 Days

| Task | Owner | Deliverable |
|------|-------|-------------|
| Cruise intel search: auto-updates from Dembe pipeline | A7 Sterling + A12 ELON | Database refresh without manual intervention |
| Dani chatbot: context-aware (remembers session, recognizes returning visitors) | A7 Sterling | Richer chatbot experience |
| Client portal integration (existing portal at `portal.d2mluxury.quest`) | A7 Sterling | Single login: request a voyage → track your booking |
| Social proof module: client milestone posts feed from A13 content | A12 ELON | Automation: approved post → app testimonial feed |
| SEO: 16+ blog posts indexed, organic traffic measurable | A13 Sienna | First organic ranking for target terms |
| A/B test: chatbot vs form as primary conversion point | A13 Sienna + Harlan | Data-driven decision on primary CTA |
| MAGtap My Site: evaluate sunset or maintain | Commander | Decision on whether stopgap has any residual value |

**Phase 3 exit condition:** `app.d2mluxury.quest` generates at least one warm inquiry per week through organic or social channels, independent of Commander's direct referral network.

---

## STAFF RESPONSIBILITIES

| Staff | Role in This Initiative |
|-------|-------------------------|
| **A7 Sterling** | Backend and frontend build, Cloudflare tunnel configuration, code review of all app modules, security review before public launch |
| **A12 ELON** | Automation layer: intake form → Hale notification pipeline, database refresh automation, social proof feed from A13 content |
| **A13 Sienna** | SEO strategy and blog content, UTM tracking setup, social traffic funneling, newsletter activation, Google Business Profile |
| **A6 Luna** | Itinerary showcase content curation, blog editorial pass for long-form posts, homepage narrative copy |
| **Naia EXEC** | Brand pass on homepage copy, newsletter content, all blog posts before publish |
| **Hale** | MAGtap activation, intake form triage, Dani chatbot routing oversight, weekly traffic review |
| **Commander** | Phase gate approvals, itinerary showcase consent decisions, strategy direction (Phase 2 scope, Phase 3 priorities) |

---

## SECURITY AND COMPLIANCE NOTES

- No client PII stored on the public app. Intake form submissions route to an internal queue file, not a public database.
- Dani chatbot: no session persistence across anonymous visits. Inquiry data logged to d2mconcierge, not the web server.
- A7 Sterling security review required before Phase 2 launch (chatbot + search live). Gate is Sterling's sign-off.
- SSL/TLS: Cloudflare handles termination. Zero additional configuration needed.
- GDPR/privacy: "Request a Voyage" form includes consent checkbox before submission. A12 ELON implements.

---

## DECISION REQUIRED FROM COMMANDER

1. **MAGtap activation:** Approve Track 1 now? (2-3 hours, Hale executes)
2. **`app.d2mluxury.quest` Phase 1 start:** Direct A7 Sterling to begin scaffold this week?
3. **Itinerary showcase:** Which completed client itineraries are cleared for public display? (Luna curates, Commander approves list)
4. **Blog voice:** Should "The D2M Intelligence Brief" blog byline be Commander John Loucks, or D2M editorial? (affects LinkedIn repurposing and authority positioning)

---

*Document prepared by: A13 Sienna Navarro + A6 Luna Voss*
*Routing: Hale review → Commander decision*
*Date: 2026-05-25*
*Next review: 2026-06-01 (Phase 1 exit condition check)*
