# Hermai.ai — Analysis & Implementation Plan for Low-Volume Air Scans
**Source:** r/ClaudeCode post by u/Tradingoso, "My Claude Code now interacts with websites without a browser" · Analyzed 2026-07-19 by Hale

---

## Summary

Hermai is an open-source (AGPL-3.0) catalog of reverse-engineered website API
schemas — 1,971 community-maintained schemas across 15 categories (35 in
Travel), live at hermai.ai. Install a Claude Code skill
(`npx skills add hermai-ai/hermai-skills`) and the agent looks up a target
site in the registry, pulls its schema (exact request parameters, headers,
signing/session logic), and either self-executes the request directly or —
where enabled — calls Hermai's hosted `POST /v1/fetch`. Free tier: 1,000
credits/mo, no card required. Verified live: **kayak.com** (5 endpoints:
flight_search, hotel_search, car_rental, explore, price_forecast) and
**booking.com** (10 endpoints incl. autocomplete, hotel_detail, deals) both
have real, published schemas in the catalog today.

## The catch (verified, not assumed)

For both Kayak and Booking.com — the two travel sites most relevant here —
**hosted execution is explicitly marked "not yet enabled."** Every endpoint
says: *"Data package available. Hosted fetch not enabled yet. Pull the
package to run this endpoint yourself."* That means:
- Hermai does **not** proxy the request through its own infrastructure for
  these sites (good for PII — nothing transits a third party) — but also
  **doesn't solve anti-bot for you**. Thunderbird's own infrastructure would
  execute the documented request, and Kayak specifically runs aggressive
  bot detection (TLS fingerprinting, dynamic request signing).
- The real value on offer today is **saved reverse-engineering time** — the
  schema documents the exact request shape (their skill description
  mentions "session block rules for anti-bot sites" and "signer JS /
  bootstrap JS" for signed requests are part of the schema package) — not a
  guaranteed working bypass. Reliability against Kayak's live defenses is
  unverified until the package is actually pulled and tested.
- Per-call credit cost isn't published — only "1,000 credits/mo free."
  Unknown until an API key is registered.

This is a real, live, open-source project (not vaporware — the catalog,
playground, and specific Kayak/Booking.com schemas all checked out on direct
inspection) — but it's a documentation/shortcut layer, not a magic
anti-bot-bypass service, at least for travel sites as of today.

## Why it's still worth testing

Current flight stack: Kiwi RapidAPI (300/mo cap), Google Flights RapidAPI
(150/mo cap), Centrav B2B (headed-browser Playwright login), United
CloakBrowser (one-way only). All either quota-capped or require full browser
automation. If Hermai's documented Kayak request shape holds up under a
direct HTTP call (no browser), that's a genuinely lighter-weight path for
quick, low-stakes ad hoc fare checks — the "low volume air scans" the
Commander flagged — without burning RapidAPI quota or spinning up
CloakBrowser. Worst case if it doesn't work: zero cost, zero risk, learned
in an afternoon.

## Implementation plan

**P0 — Sandboxed evaluation (today, $0, no client data):**
1. Register a free Hermai API key (no card) under a Thunderbird-owned email,
   not personal.
2. Pull the `kayak.com` `flight_search` package and inspect the actual
   request spec before running anything.
3. Test one known route/date already priced via Kiwi/Google Flights
   RapidAPI, direct HTTP call, no browser — see if it actually returns valid
   data or gets blocked.

**P1 — Controlled trial (if P0 succeeds):**
4. Run 5-10 known routes in parallel against Kiwi/Google Flights RapidAPI —
   compare price accuracy, latency, and real credit cost per call.
5. Confirm the request survives repeated calls (anti-bot systems often allow
   a first hit then throttle/block — single-success isn't proof of
   reliability).

**P2 — Production rollout (only if P1 holds up over repeated use):**
6. Wire in as an additional low-cost source for quick ad hoc scans via the
   `flight-price` skill, alongside — not replacing — Kiwi/Google
   Flights/Centrav.
7. Keep the standing verify-via-second-source doctrine
   (`reference_flight_routing_research_methodology`) — never single-source a
   client-facing fare, Hermai included.
8. Document in `AGENTS.md` / the flight-price skill once validated.

**Not now:** contributing new schemas back to the registry (heavier
`hermai-cli` discovery toolkit — no current gap it fills), and Hermai's
hosted `/v1/fetch` path for any site where it does carry client-identifiable
data once hosted execution is enabled for travel — PII fence applies the
same as any third-party API.

## Bottom line

Legitimate open-source project, verified live for the two travel sites that
matter here — but the Reddit pitch overstates the "no browser required"
framing for Kayak/Booking.com specifically: hosted execution isn't on for
travel yet, so this saves reverse-engineering effort, it doesn't hand you a
guaranteed bypass. Worth the P0 test — costs nothing, could meaningfully cut
token/latency cost on low-volume ad hoc fare checks if the documented
request shape survives real-world anti-bot. Not ready to trust for
client-facing pricing until P1 validates it.
