#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Web Fetch & Scrape
======================================
Replaces `import trafilatura` (library-present != fetch-works). Performs one
real fetch+extract of a known-good, stable URL and REDs if extraction returns
little/no text — the actual failure mode (CloudFront/403/empty body) the
import check is blind to. Cheap (~3s), no client impact.
Exit 0 = healthy, 1 = degraded.
"""
import sys

PROBE_URL = "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md"
MIN_CHARS = 200


def fail(m): print(f"RED web-fetch: {m}"); sys.exit(1)


def main():
    try:
        import trafilatura
    except Exception as e:
        fail(f"trafilatura import failed: {e}")
    try:
        html = trafilatura.fetch_url(PROBE_URL)
    except Exception as e:
        fail(f"fetch raised: {e}")
    if not html:
        fail(f"fetch returned empty for probe URL (network/CDN block)")
    text = trafilatura.extract(html) or html
    n = len(text.strip())
    if n < MIN_CHARS:
        fail(f"extracted only {n} chars (<{MIN_CHARS}) — extractor degraded")
    print(f"RAZOR_SHARP web-fetch: fetched+extracted {n} chars from probe URL")
    sys.exit(0)


if __name__ == "__main__":
    main()
