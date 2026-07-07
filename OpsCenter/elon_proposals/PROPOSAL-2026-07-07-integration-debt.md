# PROPOSAL: Close Integration Debt Before New Cadence Opens
**Author:** staff_proposal_cadence.py (gate, not ELON manual write)
**Date:** 2026-07-07
**Decision:** QUEUE_FOR_COMMANDER
**CLOSURE_TARGET_DATE:** 2026-07-14

## Why this fired instead of new proposals
Integration rate is 14% (threshold: 50%).
Cadence is throttled — the backlog does not get to grow while this much of it sits
committed-but-unwired.

## Committed but NOT integrated (16 modules)
- wcag_auditor
- crew_roster
- itinerary_optimizer
- memory_book_builder
- medical_screening
- upgrade_detector
- upsell_recommender
- insurance_integrator
- booking_notifications
- client_ivr
- lounge_coordinator
- pricing_negotiation
- translation_engine
- cancellation_scorer
- loyalty_tracker
- claude_narrative_generator

## Ask
Pick one of:
1. Assign an owner to wire N of these into a live path (import + call site, or a
   systemd timer) this week, OR
2. Explicitly mark any of these as WON'T-INTEGRATE (kill it, stop counting it as debt), OR
3. Override the throttle for this week (state reason; logged to hale_decisions.md).
