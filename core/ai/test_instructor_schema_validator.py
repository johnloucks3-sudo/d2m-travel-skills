#!/usr/bin/env python3
"""
Live validation of instructor_schema_validator.py.

Runs real LLM calls (Groq backend — ANTHROPIC_API_KEY has no credit balance
as of 2026-07-06, confirmed via a live 400 BadRequestError; see
core/ops/thunderbird_v3.py note) and asserts 100% of outputs validate
against their Pydantic schema. No mocking — instructor's entire value is
that malformed output either gets retried into shape or raises, so a mocked
"always-valid" response would test nothing.
"""
import sys

from instructor_schema_validator import (
    ClientProposal,
    CruiseQuote,
    HotelGuide,
    extract_structured,
)

BACKEND = "groq"

CRUISE_PROMPTS = [
    "The Silver Nova sails with Silversea, departing 2027-05-05 and returning 2027-05-19. Total cost $24,700 for 2 travelers, Veranda Suite.",
    "Regent Seven Seas Grandeur, confirmation for 4 guests, leaves 2026-08-29, back 2026-09-12, $18,831.00 total, Concierge Suite.",
    "Viking Ocean's Viking Mars departs Dec 17 2026 and returns Dec 31 2026, 6 guests, $42,300 total across 3 cabins, no category confirmed.",
    "Extract: Seven Seas Prestige (Regent), Dec 18 2027 to Jan 2 2028, 2 pax, $31,200, Penthouse Suite.",
    "Silversea Silver Muse, June 23 2026 - July 6 2026, 2 travelers, total $19,450, no cabin category given.",
]

HOTEL_PROMPTS = [
    "At Six Hotel, Stockholm Norrmalm, $450/night, $1,800 total for 4 nights, 5 stars, free cancellation until 30 days prior. Highlights: rooftop bar, spa, central location.",
    "Hotel Grande Bretagne, Athens Syntagma Square, $600/night, $2,400 total for 4 nights, 5 stars, non-refundable after deposit. Highlights: historic landmark, Acropolis views.",
    "Nobu Hotel, Athens, $380/night, $1,140 for 3 nights, 4 stars, free cancellation until 7 days prior. Highlights: rooftop pool, sushi restaurant.",
    "The Marker, Dublin Grand Canal Dock, $290/night, $870 for 3 nights, 4 stars, free cancellation until 48 hours prior. Highlights: harbor view, modern design.",
]

PROPOSAL_PROMPTS = [
    "Write a one-line proposal summary: client Erik McLeod and Melissa McGlasson, trip 'Lesser Antilles Voyage', destination Caribbean, price summary $11,943.15 balance due, recommendation to lock in the FPD by July 22, next step is a reply confirming the payment method.",
]


def run_batch(label, prompts, model_cls, system_prompt):
    passed = 0
    for i, prompt in enumerate(prompts, start=1):
        try:
            result = extract_structured(
                system_prompt=system_prompt,
                user_prompt=prompt,
                response_model=model_cls,
                backend=BACKEND,
            )
            assert isinstance(result, model_cls)
            print(f"✅ {label} {i}/{len(prompts)}: {result!r}")
            passed += 1
        except Exception as e:
            print(f"❌ {label} {i}/{len(prompts)} FAILED: {e}")
    return passed, len(prompts)


def main():
    total_passed = 0
    total_run = 0

    p, n = run_batch(
        "CruiseQuote", CRUISE_PROMPTS, CruiseQuote,
        "You are a data extraction assistant. Extract the cruise quote fields exactly as given.",
    )
    total_passed += p
    total_run += n

    p, n = run_batch(
        "HotelGuide", HOTEL_PROMPTS, HotelGuide,
        "You are a data extraction assistant. Extract the hotel guide fields exactly as given.",
    )
    total_passed += p
    total_run += n

    p, n = run_batch(
        "ClientProposal", PROPOSAL_PROMPTS, ClientProposal,
        "You are a travel concierge assistant. Extract the proposal summary fields exactly as given.",
    )
    total_passed += p
    total_run += n

    print(f"\n{total_passed}/{total_run} runs produced schema-valid output.")
    if total_passed != total_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
