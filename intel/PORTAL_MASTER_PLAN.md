# PORTAL MASTER PLAN — d2mluxury.quest
## Dreams2Memories Travel, LLC
## v1.0 — 2026-03-20 — ELON (A12, Innovation & Disruption)

---

## THE THESIS

Wait, why are we doing this at all?

Because TESS is someone else's platform. Every hour we spend fitting our workflow into their system is an hour we're building their moat, not ours. The portal isn't a "feature" — it's the product. D2M's differentiator isn't access to hotels and cruise lines. Every advisor has that. The differentiator is the *experience of being a D2M client*. That experience should live on OUR domain, under OUR control, with OUR brand wrapped around every pixel.

d2mluxury.quest is where the leather folio opens. Everything else is back-office plumbing.

---

## CURRENT STATE AUDIT

### What portal/server.py Does Today

**Framework:** FastAPI + single-page HTML (index.html) + CSS (style.css). 665 lines of Python, 620 lines of HTML/JS, 880 lines of CSS. No database. No build tools. No node_modules. This is beautiful.

**Auth:** Magic link via email (SMTP from d2mconcierge@gmail.com). Token store = JSON file on disk. Session = httponly cookie, 7-day TTL. Token = 24-hour TTL, single-use. No passwords anywhere. This is exactly right.

**Client Registry:** Auto-discovered from dossier markdown files at startup. Emails extracted via regex. Maps email to dossier stems. One email can appear in multiple dossiers (travel party support). Currently finds all emails from `~/Thunderbird/dossiers/*.md`, filters out internal addresses.

**Endpoints:**
| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Service status + known client count |
| `/api/auth/request` | POST | Request magic link (email in body) |
| `/api/auth/verify` | GET | Consume token, create session, redirect |
| `/api/auth/me` | GET | Return session email + dossier keys |
| `/api/auth/logout` | POST | Destroy session |
| `/api/trips` | GET | List trips (parsed from dossiers) |
| `/api/trips/{key}` | GET | Single trip detail |
| `/api/contact` | POST | Send message to COS (rate-limited: 5/hr) |
| `/` | GET | Serve index.html |
| `/{path}` | GET | SPA fallback to index.html |

**Pages (client-side routing via hash):**
- `#login` — Email input, magic link request
- `#dashboard` — Trip cards grid with countdown badges, payment status
- `#trip/{key}` — Trip detail: dates, timeline, payment, documents
- `#contact` — Message Dani form + Telegram/email alternatives

**Dossier Parser:** Extracts title, ship, embark/disembark dates, destinations (route), payment (total/paid/balance/due date/status), key dates from markdown tables, document references (booking confirmations, PNRs, e-tickets, insurance, itinerary PDFs).

**Design:** Dark navy theme (#0a1628), gold accents (#c9a94e), cream (#f7f3ea). Playfair Display serif + Inter sans-serif. Cards, badges, responsive grid. Looks good — luxury feel is there. But it's an *app dashboard*, not a *leather folio*.

**What's Missing:**
- No public landing page (unauthenticated visitors see only the login card)
- No guest profile intake
- No document vault (references docs but doesn't serve files)
- No messaging thread (one-shot contact form, not a conversation)
- No itinerary view (day-by-day)
- No pre-departure toolkit
- No post-trip flow
- No between-trips retention
- No multi-advisor support
- No database (JSON files on disk)

**What's RIGHT:**
- Zero dependencies beyond FastAPI/Uvicorn/Pydantic
- Magic link auth is elegant and correct
- Dossier-driven data model (no separate CRM to sync)
- Cloudflare tunnel already routes portal.d2mluxury.quest to localhost:8780
- The CSS is genuinely premium
- No build step. No webpack. No npm. Ship it.

---

## FULL LIFECYCLE DESIGN

### Phase 0: Design Philosophy

The governing metaphor: **Opening a leather folio at a five-star hotel.**

Not a dashboard. Not an app. A folio. When a client opens d2mluxury.quest, they should feel the same thing they feel when a concierge hands them a cream-colored folder with their name embossed on it. Quiet confidence. Everything handled.

**Design Principles:**
- Cream paper (#f7f3ea) is the primary canvas, not dark navy. Navy is the binding, not the page. (Inversion from current design — current is dark-mode-first, which feels like a SaaS tool. Luxury is light.)
- Full-width destination photography on hero sections — Unsplash API or curated library
- Georgia serif for body text, Playfair Display for headlines only
- White space is the luxury. Remove, don't add.
- No visible UI chrome. No hamburger menus, no sidebars. One column, scrolling, like a printed itinerary.
- Gold (#c9a94e) used sparingly — dividers, the occasional accent. Not everywhere.
- Mobile-first. These clients are on their phones while traveling.

**The Two Modes:**
1. **Public mode** (unauthenticated) — Landing page, about, contact form, "Plan My Trip" wizard
2. **Client mode** (authenticated) — Trip folio, documents, messaging, pre-departure, post-trip

---

### 1. DISCOVERY — Prospect Lands on d2mluxury.quest

**Current:** Nothing. Login card. Dead end for prospects.

**Target:**

**Landing Page (/):**
- Full-viewport hero image (rotating curated destinations — Santorini, Fjords, Amalfi, Alaska)
- One line: "Luxury Travel, Personally Crafted"
- Subtle scroll indicator
- Second fold: "What Makes Us Different" — three cards:
  - "One Advisor, Not a Call Center" — photo of John in context
  - "Every Detail, Handled" — folio/itinerary imagery
  - "Relationships, Not Transactions" — testimonial or philosophy
- Third fold: Destination inspiration gallery (3-4 hero images linking to trip planning)
- Fourth fold: "Plan Your Next Journey" CTA

**Contact Form (/contact — public):**
- Name, email, phone (optional), trip interest (dropdown: cruise, resort, tour, not sure), message
- Submits to COS pipeline (same as current contact endpoint but without auth requirement)
- Creates an inquiry record in the system
- Fires notification to Commander via Telegram C2

**"Plan My Trip" Wizard (/plan):**
- Step 1: What kind of trip? (Cruise / Resort / Tour / Surprise Me)
- Step 2: When? (Month picker, flexible dates toggle)
- Step 3: Who's going? (Adults, children, names optional)
- Step 4: What matters most? (Relaxation / Adventure / Culture / Romance / Family)
- Step 5: Budget comfort zone? (Slider: $5k-$50k+ per person)
- Step 6: Anything else? (free text)
- Submit: Thank you screen + "Dani will reach out within 24 hours"
- Backend: Creates inquiry record, fires Telegram notification, optionally creates a skeleton dossier

**Implementation notes:**
- Landing page is a separate static HTML file or a distinct route in the SPA
- No auth required for any discovery page
- Contact form has its own rate limiting (IP-based, not session-based)
- Wizard data stored as JSON, fed into dossier creation pipeline

---

### 2. ONBOARDING — New Client Activated

**Current:** Magic link sends to trip dashboard. That's it.

**Target:**

**Magic Link Auth (existing — enhance):**
- Keep current magic link flow. It's perfect.
- Add: When a client's first session starts, show the Welcome Experience instead of jumping to dashboard

**Welcome Experience (first login only):**
- Full-screen cream background, Playfair Display headline: "Welcome to Dreams2Memories"
- John's privacy covenant: "Your information stays between us. No data sharing. No third-party marketing. Just your trip, done right."
- "What to expect" — 3-4 bullet points about the portal, Dani, how communication works
- "Complete Your Profile" CTA

**Guest Profile Form (embedded):**
- Currently using Google Forms with redirect. Replace with native form.
- Fields from existing Guest Profile Google Form (reference: reference_guest_profile_form.md):
  - Full legal name (as on passport)
  - Date of birth
  - Passport number + expiration (encrypted at rest)
  - Known Traveler Number / TSA PreCheck / Global Entry
  - Frequent flyer programs + numbers
  - Dietary restrictions
  - Mobility/accessibility needs
  - Emergency contact
  - Room preferences (bed config, deck preference, cabin type)
  - Celebration dates (anniversaries, birthdays during trip)
  - "Anything else Dani should know?"
- Save to dossier + Booking Master Sheet
- Progress indicator (don't show all fields at once — multi-step, like the wizard)
- Auto-save on blur (no "submit" anxiety)

**Implementation notes:**
- Welcome state tracked per client (a "welcomed" flag in the session/client store)
- Profile data writes to dossier markdown AND via MCP to Google Sheets
- Passport/sensitive fields: encrypt before storing anywhere. Consider whether to store at all vs. "we have it on file" confirmation.

---

### 3. TRIP PLANNING — Active Booking Lifecycle

**Current:** Trip cards with countdown, payment status, basic detail view.

**Target:**

**Trip Dashboard (enhanced):**
- Keep the card grid but upgrade the cards:
  - Each card gets a destination hero image (pulled from curated library or Unsplash by destination name)
  - Countdown in days, but also "in X weeks" for distant trips
  - Quick-action buttons on hover: View Itinerary, Documents, Message Dani
- Add a "Next Up" hero section at top for the nearest upcoming trip (full-width, large countdown)

**Itinerary View (/trip/{key}/itinerary):**
- Day-by-day timeline, left-aligned, vertical scroll
- Each day card:
  - Date, day-of-week, port/city name
  - Arrival/departure times (for cruises)
  - Planned excursions with booking confirmations
  - Restaurant reservations
  - Transfer details
  - Weather forecast snippet (pulled from NOAA/weather API)
  - Port/city intel from A2 (linked to destination guide)
- Toggle: Compact view (list) vs. Expanded view (cards with images)
- Print-friendly stylesheet
- PDF export (WeasyPrint, already in the stack)

**Document Vault (/trip/{key}/documents):**
- Currently: text list of document references. Not downloadable.
- Target: Actual file serving from Google Drive (D2M Trip Dossiers/)
  - Booking confirmations (PDF)
  - E-tickets / boarding passes
  - Travel insurance policy
  - Passport copies (client-uploaded, encrypted)
  - Hotel vouchers
  - Excursion confirmations
  - Custom itinerary PDF
- Upload capability: Client can upload their own docs (passport scan, insurance card)
- Files stored in Google Drive via MCP, served via signed URLs or proxied through the API
- Organize by category with icons

**Dani Messaging (/trip/{key}/messages or global /messages):**
- Currently: One-shot contact form. No history. No thread.
- Target: Threaded messaging interface
  - Messages stored in a simple JSON log or SQLite
  - Client sends message -> stored + COS notified via email/Telegram
  - Dani replies (via COS review gate) -> stored + client sees it in portal
  - Not real-time websocket chat (overkill for luxury concierge). Polling or SSE for new messages.
  - Email notifications when Dani replies ("You have a new message from Dani")
  - Message history persists across sessions
- Integration: Dani engine drafts reply -> COS approves -> posted to thread + email notification

**Audio Briefing Player:**
- Pre-departure audio briefings (TTS from trip dossier content, or John's recorded messages)
- Simple HTML5 audio player, cream/gold styled
- "Your Trip Briefing — 3 min" on the trip detail page
- Generated by Dani engine or ElevenLabs/Retell integration (see retell_ai_implementation_guide.md)

**Photo Gallery:**
- Destination photos from A2 research
- Curated per-trip gallery (stored in Drive, served via portal)
- Lightbox viewer
- Client can add their own photos post-trip (see Post-Trip phase)

---

### 4. PRE-DEPARTURE — Final Prep

**Target:**

**Packing Checklist (/trip/{key}/packing):**
- Template-generated based on destination, climate, trip type, duration
- Cruise-specific: formal nights, shore excursion gear, medication, plug adapters
- Resort-specific: swim/beach, SPF, activities gear
- Client can check items off (state stored locally + server)
- Print-friendly

**Flight Status (/trip/{key}/flights):**
- PNR and flight numbers from dossier
- Live status via FlightAware integration (already have `track_flight_flightaware` MCP tool)
- Show: departure/arrival times, gate, delays, terminal
- Link to airline check-in
- Auto-refresh

**Transfer Details (/trip/{key}/transfers):**
- Driver name, phone, vehicle description
- Pickup time and location (with map embed if address available)
- Confirmation number

**Emergency Info (/trip/{key}/emergency):**
- Travel insurance policy number + claims phone
- D2M emergency line (Dani's number or concierge@ email)
- Embassy/consulate contacts for destination country
- Local emergency numbers (police, ambulance, fire)
- Nearest hospitals

---

### 5. IN-TRIP — While Traveling

**Target:**

**Live Itinerary Updates:**
- Same itinerary view from Phase 3, but with real-time annotations
- Dani can push updates: "Your restaurant reservation moved to 8pm"
- Push notifications via service worker (PWA)

**Port/City Guides:**
- A2 destination intel rendered as beautiful mini-guides
- Per-port: overview, must-see, restaurants, safety notes, transport, currency, tipping customs
- Offline-capable (PWA service worker caches guides for the trip)
- Links to Google Maps for venues

**Restaurant Reservations:**
- List of confirmed reservations with confirmation numbers
- OpenTable integration for modifications (already have MCP tools)

**Emergency Contact:**
- One-tap call to Dani (tel: link)
- One-tap email to concierge@d2mluxury.quest
- Prominent, always accessible from any page

---

### 6. POST-TRIP — After Return

**Target:**

**Satisfaction Survey (/trip/{key}/survey):**
- thunderbird_survey.py already exists — embed its form directly in portal
- Rating: overall, concierge, accommodations, excursions
- Open text: "What was the highlight?" / "What would you change?"
- NPS question: "How likely to recommend D2M?"
- Submit triggers summary to Commander + dossier update

**Photo Upload / Memory Sharing:**
- Client uploads trip photos to their trip page
- Creates a "memory gallery" for the trip
- Photos stored in Drive (client's trip folder)
- Optionally: generate a "Trip Memories" PDF (WeasyPrint) with photos + itinerary highlights

**Referral Program (/refer):**
- "Know someone who deserves this experience?"
- Simple form: friend's name, email, relationship
- Generates a warm intro email from Dani (COS review)
- Tracking: which clients referred whom
- Incentive: TBD (credit toward next trip, complimentary excursion, etc.)

**"Next Trip" Inspiration:**
- Based on past travel (destinations, preferences from profile)
- A2 generates destination suggestions
- Cards with hero images, brief pitch, "I'm Interested" button -> creates inquiry

---

### 7. BETWEEN TRIPS — Retention

**Target:**

**Bulletin Inbox (/bulletins):**
- Monthly D2M newsletters, fare alerts, destination news
- Already have bulletin system (bulletin_generate, bulletin_send, etc.)
- Portal becomes another delivery channel alongside email
- Unread count badge in nav

**Fare Watch Alerts:**
- Already have fare_watch MCP tools (add, check, list, remove, history)
- Client can set up their own watches from the portal
- Alerts show in portal + email notification
- "Alert: The Mediterranean cruise you watched dropped $400/person"

**Personal Milestone Reminders:**
- Anniversary dates, birthdays from guest profile
- "Your anniversary is in 6 weeks — thinking about a trip?"
- Powered by dossier data + calendar integration

**Travel Year in Review (annual):**
- Generated summary: countries visited, miles traveled, days at sea
- Highlight reel from photo uploads
- "Your 2026 with Dreams2Memories" — PDF or in-portal experience
- Generated in December for the past year

---

## TECHNICAL ARCHITECTURE

### Framework Decision

**Keep FastAPI + Jinja2. Do NOT introduce React/Vue/Angular.**

Here's why, from first principles:

1. The current stack (FastAPI + vanilla JS) has zero build tools. `python server.py` and it runs. That's not a limitation — that's a competitive advantage. Every dependency you add is a future maintenance burden. React means node_modules, webpack/vite, build pipelines, CI/CD complexity. For what? A glorified document viewer with a contact form.

2. The client count is in the dozens, not thousands. We don't need virtual DOM diffing. We need fast server-side rendering of beautiful HTML.

3. The person maintaining this (John, Claude, future contractors) should be able to open any file and understand it. HTML + CSS + vanilla JS is universally readable. React components are not.

4. Jinja2 templates with server-side rendering means every page loads fast on any device. No JS bundle to download. No white screen while React hydrates. Google indexes it. Accessibility is native.

5. WeasyPrint (already in the stack) can render the same Jinja2 templates as PDFs. One template = web view + print + PDF. Try that with React.

**Upgrade path:**
- Move from single-file index.html to Jinja2 templates (one per page)
- Keep vanilla JS but organize into modules (ES module imports, no bundler)
- Add HTMX for dynamic updates without full page reloads (lightweight, server-driven, perfect fit)
- CSS stays as-is (it's good), add a light/cream theme variant

### Frontend Architecture

**Server-Rendered (Jinja2) + HTMX for interactivity.**

```
portal/
  server.py                 # FastAPI app
  templates/
    base.html               # Layout: header, footer, nav
    public/
      landing.html           # Public homepage
      about.html             # About D2M
      contact.html           # Public contact form
      plan.html              # Trip planning wizard
    auth/
      login.html             # Magic link login
      welcome.html           # First-login welcome
      profile.html           # Guest profile form
    client/
      dashboard.html         # Trip cards
      trip_detail.html       # Single trip overview
      itinerary.html         # Day-by-day itinerary
      documents.html         # Document vault
      messages.html          # Dani messaging thread
      packing.html           # Packing checklist
      flights.html           # Flight status
      survey.html            # Post-trip survey
      bulletins.html         # Bulletin inbox
    components/
      trip_card.html          # Reusable trip card partial
      message_bubble.html    # Chat message partial
      countdown.html         # Countdown display
  static/
    css/
      main.css               # Base styles (refactored from style.css)
      public.css             # Light/cream theme for public pages
      client.css             # Dark/navy theme for client pages
    js/
      app.js                 # Core: auth state, navigation, HTMX config
      itinerary.js           # Itinerary interactions
      messages.js            # Message polling/sending
      wizard.js              # Trip planning wizard steps
    images/
      hero/                  # Curated destination hero images
      icons/                 # SVG icons (no icon fonts, no emoji)
    fonts/                   # Self-hosted Playfair Display + Inter
```

### Mobile Strategy

**Responsive Web + PWA. No native app.**

- Why: A native app for dozens of clients is insane. The maintenance cost vs. usage ratio is infinite. PWA gives us 90% of native capability at 1% of the cost.
- PWA features used:
  - Add to Home Screen (looks like an app on iOS/Android)
  - Offline caching (service worker caches current trip itinerary + port guides)
  - Push notifications (Dani messages, flight delays, fare alerts)
- manifest.json with D2M branding (navy icon, gold splash screen)

### Authentication

**Keep magic links. Add optional passkeys.**

- Magic links are correct for this audience. Luxury clients don't want to remember passwords. An email link IS the password.
- Enhancement: Web Authentication API (passkeys) for repeat visits. After first magic link login, prompt "Save this device" which registers a FIDO2 credential. Next visit: face ID / fingerprint on their phone = instant access.
- Session TTL: 7 days (current) is right. Consider 30 days for trusted devices (passkey-authenticated).
- Rate limiting on magic link requests: 3 per email per hour (currently implicit via SMTP).

### Data Layer

**SQLite for structured data. Dossier markdown stays as source of truth.**

Current: JSON files on disk + dossier markdown parsing at request time. This works for 10 clients. It won't work for 100.

**Migration path:**
1. Phase 1: Keep JSON files. They work.
2. Phase 2: Add SQLite (single file, zero-config, already in Python stdlib).
   - Tables: clients, sessions, messages, documents, inquiries, surveys, fare_watches, bulletins
   - Dossier markdown remains the canonical trip record (parsed and cached on change)
   - SQLite handles everything dossiers don't: message threads, survey results, file metadata, audit logs
3. Phase 3 (platform play): PostgreSQL only if multi-tenant requires it. SQLite handles more than people think.

**No ORMs. Raw SQL with parameterized queries.** An ORM for a 10-table database is overhead for overhead's sake.

### Hosting

**YOGA (192.168.1.198) + Cloudflare Tunnel. No changes needed.**

- Current setup: uvicorn on localhost:8780, cloudflared tunnels to portal.d2mluxury.quest
- SSL: Cloudflare handles it. Free. Automatic.
- Static assets: Cloudflare caches them (add Cache-Control headers)
- File uploads: Store in Google Drive via MCP, serve proxied through the API
- Backups: SQLite file included in daily rclone sync to Drive

**Scale ceiling:** YOGA can handle hundreds of concurrent portal sessions. If we ever need more (platform play), Cloudflare Workers or a VPS. But that's a problem for when we have the problem.

### File Storage

**Google Drive (existing) via MCP tools.**

- Documents uploaded by clients -> Google Drive via `drive_upload_file` MCP tool
- Served to clients via `drive_download_file` + streaming response, or signed URLs
- Folder structure: `D2M Trip Dossiers/{Client Name}/{Trip}/documents/`
- Max upload size: 10MB per file (enforced server-side)
- Allowed types: PDF, JPG, PNG, HEIC (convert to JPG server-side)

---

## MULTI-TENANT PLATFORM PLAY

### The Vision

D2M becomes a travel advisor platform. Other advisors sign up, get their own branded portal, manage their own clients. D2M runs the infrastructure. Advisors pay monthly.

### How It Works

**Advisor Onboarding:**
- Advisor signs up at d2mluxury.quest/advisors (or a separate domain: platform.d2mluxury.quest)
- Creates account, uploads logo, sets brand colors, custom domain (CNAME)
- Gets their own portal URL: `{advisor-slug}.d2mluxury.quest` or custom domain
- Dashboard: their clients, their trips, their messages

**White-Label:**
- Each advisor gets brand customization:
  - Logo (header + login page + emails)
  - Primary/accent colors (replace gold/navy)
  - Custom subdomain or CNAME to their own domain
  - Email from address (their own SMTP or D2M shared)
  - Concierge name/avatar (their version of Dani)
- Templates render with advisor's brand context
- Client never sees "D2M" unless the advisor IS D2M

**Data Isolation:**
- Tenant ID on every table row. Non-negotiable.
- API middleware injects tenant context from session/domain.
- No advisor can query another advisor's clients. Ever.
- This is the hardest part and the most important. Get it right or don't build it.

**Architecture Change for Multi-Tenant:**
- Move from SQLite to PostgreSQL (row-level security for tenant isolation)
- Or: SQLite per tenant (separate database file per advisor — simpler isolation, harder to query across)
- Recommendation: PostgreSQL with tenant_id column + row-level security policies. It's the industry standard for multi-tenant SaaS because it works.
- Dossier markdown model doesn't translate to multi-tenant — advisors would use the portal's built-in trip management, not local markdown files
- Need a real trip/booking data model: trips, bookings, suppliers, payments, itinerary_days, excursions

**Pricing Model:**
- Free tier: 1 advisor, 10 active clients, D2M branding only
- Professional: $49/mo — unlimited clients, custom branding, custom domain
- Enterprise: $149/mo — API access, automation hooks, white-label emails, priority support
- Transaction fee: 0.5% of booking value (if we process payments through the platform)

**What D2M Gets:**
- Monthly recurring revenue from advisor subscriptions
- Aggregate data on travel trends (anonymized across tenants)
- Network effects: more advisors = better supplier relationships = better rates for everyone
- The platform becomes the business, not just travel advisory

### When to Build This

NOT NOW. This is Phase 4+. The priority is making d2mluxury.quest incredible for D2M's own clients. The platform play is a natural extension once the single-tenant product is proven.

Multi-tenant before product-market fit is how startups die. Build for yourself first. When other advisors start asking "how do you do that?" — that's when you build the platform.

---

## BUILD PHASES

### Phase 1 — The Folio Opens (1 week)
**Ship date: March 27, 2026**

Deliverables:
- [ ] Public landing page (hero image, value props, CTA)
- [ ] Public contact form (unauthenticated, rate-limited, COS notification)
- [ ] "Plan My Trip" wizard (multi-step form, creates inquiry)
- [ ] Migrate from single-file HTML to Jinja2 templates
- [ ] Light/cream theme for public pages
- [ ] Refactor CSS into modules (public.css, client.css, shared)
- [ ] PWA manifest + service worker (basic caching)
- [ ] Add to homescreen support

**What a client sees:** A beautiful landing page. A way to inquire. Magic link login to existing trip dashboard (unchanged from current). First impression = "this is real."

**What John demos:** Opens d2mluxury.quest on his phone, shows a prospect the landing page, says "just put your email in here and Dani will be in touch." Effortless.

### Phase 2 — The Trip Folio (2 weeks)
**Ship date: April 10, 2026**

Deliverables:
- [ ] Welcome experience for first-login clients
- [ ] Embedded guest profile form (replaces Google Forms)
- [ ] Enhanced trip dashboard (destination hero images, quick actions)
- [ ] Day-by-day itinerary view
- [ ] Document vault (upload + download via Google Drive MCP)
- [ ] Threaded Dani messaging (with COS review gate)
- [ ] SQLite database for messages, profiles, documents metadata
- [ ] Email notifications for new messages

**What a client sees:** Their entire trip in one place. Documents they can access anytime. A way to message Dani and see the conversation history. Profile on file so Dani remembers everything.

### Phase 3 — Full Lifecycle (2 weeks)
**Ship date: April 24, 2026**

Deliverables:
- [ ] Pre-departure toolkit (packing checklist, flight status, transfers, emergency contacts)
- [ ] Port/city guides (A2 intel rendered as mini-guides)
- [ ] Post-trip satisfaction survey (embedded thunderbird_survey.py)
- [ ] Photo upload + memory gallery
- [ ] Referral program (simple form + Dani intro email)
- [ ] Bulletin inbox (from existing bulletin system)
- [ ] Fare watch alerts (from existing fare_watch tools)
- [ ] Audio briefing player (TTS or recorded)
- [ ] Offline mode for trip itinerary + guides (PWA service worker)
- [ ] Passkey authentication (WebAuthn)

**What a client sees:** Everything. From the moment they book to the moment they're planning their next trip, d2mluxury.quest is their travel companion.

### Phase 4 — Platform Play (ongoing)
**Ship date: TBD (after Phases 1-3 proven)**

Deliverables:
- [ ] Multi-tenant data model (PostgreSQL migration)
- [ ] Advisor onboarding flow
- [ ] White-label branding engine
- [ ] Custom domain support (Cloudflare for SaaS)
- [ ] Advisor dashboard (their clients, their trips, their revenue)
- [ ] Billing integration (Stripe)
- [ ] API for third-party integrations
- [ ] Documentation / help center

---

## INTEGRATION MAP

These Thunderbird systems feed the portal:

| System | Portal Integration |
|---|---|
| Dossier Scanner | Trip data, payment status, key dates |
| Dani Engine | Message drafts, concierge replies |
| Voice Ledger | Tone/style for Dani's portal messages |
| Commander Inbox | Inquiry routing, contact form processing |
| MCP Google Drive | Document vault storage/retrieval |
| MCP Gmail | Magic link emails, notifications |
| FlightAware MCP | Live flight status |
| NOAA Weather MCP | Destination weather forecasts |
| A2 Intel Pipeline | Port/city guides, destination research |
| Bulletin System | Bulletin inbox content |
| Fare Watch | Alert delivery |
| Survey System | Post-trip survey form + results |
| Learning Compiler | Dani's evolving voice in portal messages |
| Template Engine | Itinerary PDFs, trip summary documents |

---

## RISK REGISTER

| Risk | Impact | Mitigation |
|---|---|---|
| Scope creep (build everything at once) | Delays everything, ships nothing | Phase 1 is ONE WEEK. Ship the landing page. |
| Sensitive data exposure (passports, payments) | Catastrophic | Encrypt at rest. Minimize storage. Don't store what you don't need. |
| SMTP failure (magic links don't arrive) | Clients locked out | Log token in dev mode. Monitor SMTP. Add passkey as backup auth. |
| Google Drive MCP latency | Slow document access | Cache frequently accessed docs. Serve thumbnails. |
| Cloudflare tunnel instability | Portal goes down | Systemd watchdog on cloudflared (already in place). Health check monitoring. |
| Over-engineering the platform play | Diverts from client experience | Platform play is Phase 4. Not one line of multi-tenant code before Phase 3 ships. |

---

## THE MATH

**Cost to build:**
- Developer time: $0 (Claude + John)
- Hosting: $0 (YOGA is already running)
- Domain: Already owned (d2mluxury.quest)
- SSL: $0 (Cloudflare)
- Photography: $0 (Unsplash API, free tier)
- Database: $0 (SQLite, then PostgreSQL free tier if needed)

**Value created:**
- Every client interaction that currently happens over email/Telegram/phone gets captured in the portal
- Document sharing goes from "email me the PDF" to "it's in your portal"
- Client experience goes from "I got an email from my travel agent" to "I have a luxury travel concierge with my own portal"
- Referral mechanism built into the product (currently: word of mouth with no tracking)
- Platform play potential: recurring revenue from advisor subscriptions

**The question isn't "can we afford to build this?"**
**The question is "can we afford not to have this?"**

Every high-end travel advisor's website is a brochure. A static page with "Contact Us." We're building the only one that's actually a product. That's the moat.

---

## DECISION REQUIRED

Commander, the plan is laid out. Three decisions needed:

1. **Phase 1 scope** — Landing page + contact form + wizard. One week. Green light?
2. **Theme direction** — Light (cream) for public pages, dark (current navy) for authenticated client pages? Or light everywhere?
3. **Profile data storage** — Store passport numbers encrypted, or "we have it on file" confirmation only (client submits via secure form, goes to Drive, not stored in database)?

Waiting on your call. I'll have Phase 1 scaffolded before you answer.

---

*Filed by ELON, A12 Innovation & Disruption*
*Dreams2Memories Travel, LLC*
*2026-03-20*
