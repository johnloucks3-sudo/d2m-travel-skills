# Duffel API Evaluation — D2M Flight Search
**Date:** 2026-07-02 | **Evaluator:** ELON (A12) | **Posture:** Adopt-first

---

## What It Is

Duffel is a developer-first, REST-based travel API that gives any travel seller direct access to flight search, booking, ticketing, ancillaries, and servicing from 300+ airlines through a single integration — pulling from NDC, GDS, and low-cost carriers simultaneously. No GDS relationship required. No IATA accreditation required. Duffel acts as the IATA-accredited intermediary (5 IATAs worldwide), so an independent advisor registers, gets a sandbox API key, and is booking-capable in the same day. They also offer hotels (2M+ properties) and car content but flights are the core product.

**Prior work:** Adapters already built. `scripts/duffel_flight_search.py` and `core/ai_infra/thunderbird_duffel.py` exist and are compiled. Blocked only on `DUFFEL_API_KEY` from Commander registering a sandbox account.

---

## Pricing Model

| Item | Cost |
|---|---|
| Starter plan | **Free** — up to 50 bookings/month, no monthly fee |
| Per confirmed order | **$3.00 + 1% of total purchase value** |
| Per paid ancillary | **$2.00** (seat, bag, meal) |
| Excess search fee | **$0.005/search** above 1,500:1 search-to-book ratio |
| FX conversion | **2%** if currency conversion required |
| Enterprise | Custom pricing — contact Duffel |

**Real math for D2M at current volume:** If we book 5 flights/month averaging $3,000/ticket:
- Per order: $3 + $30 = $33/booking
- 5 bookings: ~$165/month in Duffel fees
- Centrav alternative: no per-booking fee but wholesale-only, no NDC ancillaries

The excess search fee is a non-issue at D2M's volume — 1,500 searches per booking is an enormous allowance.

---

## Eligibility

| Question | Answer |
|---|---|
| IATA/ARC required? | **No.** Duffel provides their own accreditation (5 IATAs worldwide) via Managed Content |
| Can D2M use directly? | **Yes.** Self-serve signup at app.duffel.com, sandbox immediately, production after brief approval |
| Volume minimum? | **No.** Starter plan is free up to 50 bookings/month |
| Host agency tie-in? | **No.** D2M uses Duffel's accreditation, not a host agency |
| Own IATA option? | Yes — if D2M gets IATA-accredited later, Duffel supports BYOA (contact for pricing) |

D2M qualifies today with zero barriers. Five-minute signup.

---

## Network Coverage

300+ airlines across NDC, GDS, and LCC channels including:

**US Majors (all NDC):**
- American Airlines — NDC certified
- United Airlines — NDC certified
- Delta — NDC certified (joined April 2024, last of the Big 3)

**International key routes (cruise clients):**
- Air Canada, British Airways, Lufthansa, Turkish Airlines, Air France, KLM, Swiss, Iberia, Finnair, SAS
- Full NDC suite available on most major carriers (seat selection, baggage, branded fares)

**Coverage gap:** Some ultra-low-cost carriers (Spirit, Frontier) route through LCC channel with limited NDC ancillaries. Not relevant for D2M's luxury client base.

---

## vs Centrav (current)

| Feature | Centrav | Duffel |
|---|---|---|
| Access model | B2B wholesale portal (browser + API) | REST API only |
| Pricing | Wholesale net fares, no per-booking fee | $3 + 1% per booking |
| NDC content | Limited (GDS-dominant) | Full NDC from 300+ airlines |
| Ancillaries | Limited | Seat, bag, meal — all bookable via API |
| Automation | Semi-manual (we built a scraper) | Native API — no scraper needed |
| Airline direct offers | No | Yes — NDC unlocks fare families, bundles |
| Group booking | Yes (group desk workflow) | No dedicated group desk feature |
| No-search-fee | Yes | Yes (within 1500:1 ratio) |
| Requires Commander auth? | Yes (session cookie) | No (API key, persistent) |
| Current status | Cookie-dependent, expires regularly | Stateless API key |

**The real difference:** Centrav is better for group blocks (United Group Desk workflow). Duffel is better for individual/couple bookings with NDC ancillaries and zero browser-session maintenance. They are complementary, not redundant.

---

## ELON Recommendation

**ADOPT — INTEGRATE_NOW**

This is not a close call. The adapters are already built. The cost is $0 until Commander registers at duffel.com and drops the API key in `.env`. The marginal cost ($3 + 1% per booking) is recoverable from any D2M markup or service fee. The upside: NDC ancillaries, no cookie maintenance, 300+ airlines, full automation.

The only reason we are not live today is Commander has not completed the 5-minute signup. That is the entire blocker.

**This is not a "trial" candidate — it is INTEGRATE_NOW under SO_TECH_VANGUARD_ELEVATION_20260621 §2b.** No real money barrier (Starter is free), no client PII/send path involved (it is a search/pricing tool), Sterling has no concrete harm to show.

**First use case:** Spencer DEN-FCO 12-pax fare research, immediately replacing manual United Group Desk call for initial pricing intel. Then add to Dani's intake flow for all air inquiries.

---

## ZEN Counter-Voice

What could go wrong:

1. **$3 + 1% adds up at scale.** If D2M does 50 bookings/month at $5,000 avg, that is $2,650/month in Duffel fees. At current volume (5-10 bookings/month) this is trivial — but the fee structure scales against you, not for you. Long-term, if D2M grows, re-evaluate whether Centrav wholesale or ARC accreditation beats the per-transaction model.

2. **NDC content is not always cheaper.** NDC unlocks rich content but not necessarily lower fares. Some airlines use NDC to push branded upsells. Centrav wholesale may still beat Duffel net on pure price for many routes — always compare.

3. **Production approval gate.** Sandbox is immediate; production access requires Duffel review. For a new account, this is typically 1-3 business days — factor into any time-sensitive first use.

4. **No group block feature.** Duffel is transactional, individual bookings. For Spencer 12-pax group block pricing, United Group Desk is still the right channel. Duffel does not replace that workflow.

---

## Next Step if Adopting

1. Commander: go to [app.duffel.com/join](https://app.duffel.com/join) — sign up (5 min, email + business name)
2. Copy sandbox API key → add `DUFFEL_API_KEY=duffel_test_xxxx` to `/home/john/Thunderbird/.env`
3. Run: `python3 /home/john/Thunderbird/scripts/duffel_flight_search.py --test` (adapter already has test mode)
4. Apply for production access (1-3 business days)
5. First live query: Spencer DEN-FCO fare intel before United Group Desk call

**Commander action required: ~5 minutes at duffel.com.**

---

*Sources: [duffel.com/pricing](https://duffel.com/pricing) · [duffel.com/ndc/airlines-and-ndc](https://duffel.com/ndc/airlines-and-ndc) · [travelbookingpanel.com](https://travelbookingpanel.com/duffel-api-integration-how-travel-businesses-sell-flights-the-modern-way) · [duffel.com/blog](https://duffel.com/blog/benefits-of-using-duffel-content-services-duffels-accredited-agency-network)*
