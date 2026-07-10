"""
Instructor-based structured output validation for Thunderbird LLM calls.
Phase 4 roadmap item B (docs/PHASE_4_ROADMAP.md) — replaces the
json.loads(resp.content[0].text) / regex-scrape pattern with a client that
retries automatically until the model's output validates against a Pydantic
schema, or raises instead of silently returning malformed data.

Two backends are wired:
  - "anthropic" — instructor.from_anthropic(), Claude models
  - "groq"      — instructor.from_openai() pointed at Groq's OpenAI-compatible
                  endpoint (the roadmap's from_openai() example applies here,
                  since ANTHROPIC direct-API billing is a separate pool from
                  the Claude Max subscription and may be exhausted)

Usage:
    from core.ai.instructor_schema_validator import extract_structured, CruiseQuote

    quote = extract_structured(
        system_prompt="You are a data extraction assistant.",
        user_prompt=f"Extract the cruise quote fields from: {text}",
        response_model=CruiseQuote,
        backend="groq",
    )
    quote.total_cost  # guaranteed float, guaranteed present
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional, TypeVar

import instructor
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _anthropic_client() -> instructor.Instructor:
    import anthropic
    return instructor.from_anthropic(anthropic.Anthropic())


def _groq_client() -> instructor.Instructor:
    """Groq's API is OpenAI-compatible — instructor.from_openai() applies
    with Groq's base_url. JSON mode (not tool-calling) is required — Groq's
    OpenAI-compat layer doesn't support the tool-call schema instructor
    defaults to for from_openai()."""
    from openai import OpenAI
    return instructor.from_openai(
        OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1"),
        mode=instructor.Mode.JSON,
    )


_BACKENDS = {"anthropic": (_anthropic_client, DEFAULT_ANTHROPIC_MODEL),
             "groq": (_groq_client, DEFAULT_GROQ_MODEL)}


def get_client(backend: str = "anthropic") -> instructor.Instructor:
    if backend not in _BACKENDS:
        raise ValueError(f"Unknown backend {backend!r}. Choose from {list(_BACKENDS)}")
    factory, _ = _BACKENDS[backend]
    return factory()


def default_model(backend: str) -> str:
    return _BACKENDS[backend][1]


# ---------------------------------------------------------------------------
# Schemas — validated LLM output contracts
# ---------------------------------------------------------------------------

class CruiseQuote(BaseModel):
    ship_name: str
    supplier: str
    departure_date: str = Field(description="YYYY-MM-DD")
    return_date: str = Field(description="YYYY-MM-DD")
    total_cost: float = Field(ge=0)
    travelers: int = Field(ge=1)
    cabin_category: Optional[str] = None


class HotelGuide(BaseModel):
    hotel_name: str
    neighborhood: str
    nightly_rate: float = Field(ge=0)
    total_rate: float = Field(ge=0)
    stars: int = Field(ge=1, le=5)
    cancellation_policy: str
    highlights: List[str] = Field(default_factory=list)


class ClientProposal(BaseModel):
    client_name: str
    trip_name: str
    destination: str
    price_summary: str
    recommendation: str
    next_step: str


class MasterBookingData(BaseModel):
    """Replaces the json.loads(resp.content[0].text) call in
    core/ops/thunderbird_v3.py extract_master_data()."""
    Client_Name: str = "Pending"
    Trip_Name: str = "Pending"
    Start_Date: str = "Pending"
    End_Date: str = "Pending"
    Email: str = "Pending"
    Travelers: str = "Pending"
    Flight_Info: str = "Pending"
    Hotel_Info: str = "Pending"
    Transfer_Info: str = "Pending"


class ItineraryDay(BaseModel):
    Day: int
    Date: str
    Port: str
    Arrive: str
    Depart: str
    Romance: str
    Visual_Query: str


class DailyItinerarySchedule(BaseModel):
    """Replaces the json.loads(resp.content[0].text) call in
    core/ops/thunderbird_v3.py extract_daily_itinerary()."""
    schedule: List[ItineraryDay] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# extract_structured — one call, any schema, any backend
# ---------------------------------------------------------------------------

def extract_structured(
    *,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    backend: str = "anthropic",
    model: Optional[str] = None,
    max_tokens: int = 1000,
    max_retries: int = 2,
) -> T:
    client = get_client(backend)
    return client.chat.completions.create(
        model=model or default_model(backend),
        max_tokens=max_tokens,
        max_retries=max_retries,
        response_model=response_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )


# ---------------------------------------------------------------------------
# @validate — decorate a (system_prompt, user_prompt)-returning function so
# its call is routed through instructor and the result is a validated model
# instead of a raw string the caller has to json.loads()/regex out.
# ---------------------------------------------------------------------------

def validate(
    response_model: type[T],
    *,
    backend: str = "anthropic",
    model: Optional[str] = None,
    max_tokens: int = 1000,
    max_retries: int = 2,
) -> Callable[[Callable[..., tuple[str, str]]], Callable[..., T]]:
    def decorator(fn: Callable[..., tuple[str, str]]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            system_prompt, user_prompt = fn(*args, **kwargs)
            return extract_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                backend=backend,
                model=model,
                max_tokens=max_tokens,
                max_retries=max_retries,
            )
        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper
    return decorator
