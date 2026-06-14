#!/usr/bin/env python3
"""
apify_scraper.py — Apify cloud scraper for D2M research tasks.

STATUS: STUB — API token required.
  1. Create Apify account: https://apify.com/sign-up
  2. Go to console.apify.com → Settings → Integrations → copy API token
  3. Set APIFY_TOKEN in .env or creds/apify_credentials.json
  4. This wrapper is ready to activate.

Pricing: Free tier available. Starter $49/mo.
D2M use cases:
  - Regent/Silversea portal scraping without bot detection
  - TripAdvisor hotel/tour reviews at scale
  - Cruise critic forum sentiment harvest
  - Google Maps hotel data (pre/post cruise hotels)

Useful public actors in Apify Store:
  - apify/web-scraper: Universal JavaScript scraper
  - apify/playwright-scraper: Full browser, anti-bot
  - apify/tripadvisor-scraper: Hotel reviews
  - apify/google-maps-scraper: Maps data

Authority: SO-2026-05-04 §XII.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).parents[2]
CREDS_FILE = ROOT / "creds/apify_credentials.json"
API_BASE = "https://api.apify.com/v2"


def _get_token() -> str:
    token = os.environ.get("APIFY_TOKEN", "")
    if not token and CREDS_FILE.exists():
        data = json.loads(CREDS_FILE.read_text())
        token = data.get("APIFY_TOKEN", "")
    if not token:
        raise RuntimeError(
            "APIFY_TOKEN not set.\n"
            "1. Create account: https://apify.com/sign-up\n"
            "2. console.apify.com → Settings → Integrations\n"
            "3. Set in creds/apify_credentials.json or .env"
        )
    return token


def run_actor(
    actor_id: str,
    input_data: dict,
    wait_secs: int = 120,
    memory_mb: int = 256,
    build: str = "latest",
) -> list[dict]:
    """Run an Apify actor and return its dataset output.

    Args:
        actor_id: Actor in format "user/actor-name" (e.g. "apify/web-scraper")
        input_data: Actor-specific input configuration
        wait_secs: Max seconds to wait for run to finish (0 = fire and forget)
        memory_mb: Memory allocated for the run
        build: Actor version ("latest" or specific tag)

    Returns:
        List of items from the actor's default dataset
    """
    token = _get_token()

    # Start the actor run
    resp = requests.post(
        f"{API_BASE}/acts/{actor_id.replace('/', '~')}/runs",
        params={"token": token, "build": build},
        json={"memory": memory_mb, "timeout": wait_secs, "input": input_data},
        timeout=30,
    )
    resp.raise_for_status()
    run = resp.json().get("data", {})
    run_id = run.get("id")

    if not wait_secs:
        return [{"run_id": run_id, "status": "started"}]

    # Poll until finished or timeout
    deadline = time.time() + wait_secs
    while time.time() < deadline:
        status_resp = requests.get(
            f"{API_BASE}/actor-runs/{run_id}",
            params={"token": token},
            timeout=15,
        )
        status_resp.raise_for_status()
        run_data = status_resp.json().get("data", {})
        status = run_data.get("status")

        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        time.sleep(5)

    if status != "SUCCEEDED":
        return [{"error": f"Run {run_id} ended with status: {status}"}]

    # Fetch dataset
    dataset_id = run_data.get("defaultDatasetId")
    items_resp = requests.get(
        f"{API_BASE}/datasets/{dataset_id}/items",
        params={"token": token, "format": "json", "clean": True},
        timeout=30,
    )
    items_resp.raise_for_status()
    return items_resp.json()


def scrape_url(url: str, selectors: Optional[dict] = None, wait_secs: int = 60) -> list[dict]:
    """Scrape a single URL using the Apify web-scraper actor."""
    page_function = """
    async function pageFunction(context) {
        const { $, request } = context;
        return {
            url: request.url,
            title: $('title').text().trim(),
            text: $('body').text().trim().substring(0, 5000),
        };
    }
    """
    input_data = {
        "startUrls": [{"url": url}],
        "pageFunction": page_function,
        "maxConcurrency": 1,
    }
    return run_actor("apify/web-scraper", input_data, wait_secs=wait_secs)


def tripadvisor_hotel_reviews(hotel_url: str, max_reviews: int = 50) -> list[dict]:
    """Scrape TripAdvisor hotel reviews for a given hotel page URL."""
    input_data = {
        "startUrls": [{"url": hotel_url}],
        "maxReviews": max_reviews,
        "language": "en",
    }
    return run_actor("apify/tripadvisor-scraper", input_data, wait_secs=120)


def google_maps_hotels(location: str, max_places: int = 20, category: str = "hotel") -> list[dict]:
    """Scrape Google Maps for hotels at a location."""
    input_data = {
        "searchStringsArray": [f"{category} in {location}"],
        "maxCrawledPlaces": max_places,
        "language": "en",
        "exportPlaceUrls": True,
    }
    return run_actor("apify/google-maps-scraper", input_data, wait_secs=180)


if __name__ == "__main__":
    print("Apify stub — API token required.")
    print("Create account at: https://apify.com/sign-up")
    print("Browse actors at: https://apify.com/store")
