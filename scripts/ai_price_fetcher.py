#!/usr/bin/env python3
"""
AI-assisted cruise price fetcher — Regent, Oceania, Silversea, Crystal, Atlas Ocean.

Pipeline per line:
  1. Perplexity sonar-pro  → web search for current fares (real-time data)
  2. Gemini Flash 1.5      → parse response → [{ship, departure, from_port, price_pp}]
  3. Groq Llama 3.3 70B    → fallback if Gemini fails (free tier)
  4. DB match + UPDATE     → price_ind, price_ts, price_src='ai_search'

Run: python3 scripts/ai_price_fetcher.py [--line "Regent Seven Seas Cruises"] [--dry-run]
Timer: cruise-ai-price.timer (weekly, Tue–Fri 18:00 MT, one line per night)
"""

import argparse, json, os, re, sqlite3, time, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT   = Path("/home/john/Thunderbird")
DB     = ROOT / "output/cruises.db"
ENVF   = ROOT / ".env"

# ── Load env ──────────────────────────────────────────────────────────────────
def load_env():
    env = {}
    if ENVF.exists():
        for line in ENVF.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
    env.update(os.environ)  # live env wins
    return env

ENV = load_env()

# ── Line configs ──────────────────────────────────────────────────────────────
LINE_CONFIGS = {
    "Regent Seven Seas Cruises": {
        "search_name": "Regent Seven Seas Cruises",
        "ships": ["Seven Seas Grandeur", "Seven Seas Splendor", "Seven Seas Explorer",
                  "Seven Seas Mariner", "Seven Seas Voyager", "Seven Seas Navigator"],
        "priority": 1,
    },
    "Oceania Cruises": {
        "search_name": "Oceania Cruises",
        "ships": ["Marina", "Riviera", "Vista", "Allura", "Nautica", "Regatta", "Insignia", "Sirena"],
        "priority": 2,
    },
    "Silversea Cruises": {
        "search_name": "Silversea Cruises",
        "ships": ["Silver Muse", "Silver Nova", "Silver Dawn", "Silver Wind",
                  "Silver Whisper", "Silver Origin", "Silver Shadow", "Silver Ray"],
        "priority": 3,
    },
    "Atlas Ocean Voyages": {
        "search_name": "Atlas Ocean Voyages",
        "ships": ["World Navigator", "World Traveller", "World Seeker",
                  "World Adventurer", "World Discoverer"],
        "priority": 4,
    },
    "Crystal Cruises": {
        "search_name": "Crystal Cruises",
        "ships": ["Crystal Serenity", "Crystal Symphony", "Crystal Grandeur"],
        "priority": 5,
    },
}

# ── Perplexity search ─────────────────────────────────────────────────────────
# Search strategy:
#   Primary  — Gemini Flash w/ Google Search grounding (free tier, 1500 req/day, real-time web)
#   Fallback — DeepSeek chat (training data, cheap; stale but better than nothing)
# Perplexity and XAI/Grok wired but gated — activate when credits are loaded.
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
XAI_URL        = "https://api.x.ai/v1/chat/completions"
GEMINI_SEARCH_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

SEARCH_PROMPT_TMPL = (
    "What are the current starting fares per person for {line_name} cruises "
    "departing {date_range}? "
    "List specific sailings with: ship name, exact departure date, departure port, "
    "and starting price per person in USD. "
    "Include as many upcoming sailings as possible. "
    "Format as a clear list. Only include confirmed published fares, not estimates."
)

def _build_search_prompt(line_name: str, months_ahead: int = 9) -> str:
    start = datetime.now() + timedelta(days=30)   # 30 days from today — clearly future
    end   = start + timedelta(days=months_ahead * 30)
    date_range = f"{start.strftime('%B %Y')} through {end.strftime('%B %Y')}"
    return SEARCH_PROMPT_TMPL.format(line_name=line_name, date_range=date_range)

def gemini_grounded_search(line_name: str, months_ahead: int = 6) -> str:
    """Gemini Flash with Google Search grounding — real-time web, free tier."""
    prompt = _build_search_prompt(line_name, months_ahead)
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000},
    }).encode()
    url = f"{GEMINI_SEARCH_URL}?key={ENV.get('GEMINI_API_KEY', '')}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  [gemini-search] Error: {e}")
        return ""

def deepseek_search(line_name: str, months_ahead: int = 6) -> str:
    """DeepSeek v3 — training data fallback (may be slightly stale)."""
    prompt = _build_search_prompt(line_name, months_ahead)
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2000,
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {ENV.get('DEEPSEEK_API_KEY', '')}",
            "Content-Type": "application/json",
        }
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [deepseek-search] Error: {e}")
        return ""

def perplexity_search(line_name: str, months_ahead: int = 6) -> str:
    """Perplexity sonar — activate when quota is reloaded."""
    prompt = _build_search_prompt(line_name, months_ahead)
    body = json.dumps({
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        PERPLEXITY_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {ENV.get('PERPLEXITY_API_KEY', '')}",
            "Content-Type": "application/json",
        }
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [perplexity] Error (quota?): {e}")
        return ""

def xai_search(line_name: str, months_ahead: int = 6) -> str:
    """XAI Grok w/ web search — activate when credits are purchased."""
    prompt = _build_search_prompt(line_name, months_ahead)
    body = json.dumps({
        "model": "grok-3",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        XAI_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {ENV.get('XAI_API_KEY', '')}",
            "Content-Type": "application/json",
        }
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  [xai/grok] Error (credits?): {e}")
        return ""

def multi_search(line_name: str, months_ahead: int = 6) -> str:
    """Multi-source search: Gemini grounded + Perplexity sonar + XAI Grok + DeepSeek fallback."""
    parts = []

    gem = gemini_grounded_search(line_name, months_ahead)
    print(f"  [1a] Gemini+Search: {len(gem)} chars")
    if gem: parts.append(f"--- GEMINI GOOGLE SEARCH ---\n{gem}")

    ppx = perplexity_search(line_name, months_ahead)
    print(f"  [1b] Perplexity:    {len(ppx)} chars")
    if ppx: parts.append(f"--- PERPLEXITY SONAR ---\n{ppx}")

    grok = xai_search(line_name, months_ahead)
    print(f"  [1c] XAI Grok-3:    {len(grok)} chars")
    if grok: parts.append(f"--- XAI GROK-3 ---\n{grok}")

    ds = deepseek_search(line_name, months_ahead)
    print(f"  [1d] DeepSeek:      {len(ds)} chars")
    if ds: parts.append(f"--- DEEPSEEK ---\n{ds}")

    return "\n\n".join(parts)

# ── Gemini Flash parser ───────────────────────────────────────────────────────
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

EXTRACT_PROMPT = """Extract all cruise sailing prices from the text below.
Return ONLY a JSON array with objects having these exact keys:
  ship (string), departure (YYYY-MM-DD or best estimate), from_port (string), price_pp (number, USD, per person)

Rules:
- price_pp must be a number (no $ signs, no commas)
- departure must be a date string (estimate year if only month given, use {year})
- Skip any sailing without a specific price
- If a price range is given, use the lower (starting) price
- Return [] if nothing found

Text to parse:
{text}

Return only the JSON array, no explanation."""

def gemini_parse(text: str, year: int) -> list:
    """Use Gemini 2.5 Flash to extract structured pricing from search response."""
    prompt = EXTRACT_PROMPT.format(text=text, year=year)
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 4096, "responseMimeType": "application/json"},
    }).encode()

    url = f"{GEMINI_URL}?key={ENV.get('GEMINI_API_KEY', '')}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        parts = data["candidates"][0].get("content", {}).get("parts", [])
        raw = parts[0].get("text", "").strip() if parts else ""
        raw = re.sub(r'^```(?:json)?\s*', '', raw).strip()
        raw = re.sub(r'\s*```$', '', raw).strip()
        if not raw:
            return []
        return json.loads(raw)
    except Exception as e:
        print(f"  [gemini] Parse error: {e}")
        return []

# ── Groq Llama fallback parser ────────────────────────────────────────────────
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def groq_parse(text: str, year: int) -> list:
    """Groq Llama 3.3 70B fallback — free tier."""
    prompt = EXTRACT_PROMPT.format(text=text, year=year)
    body = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(
        GROQ_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {ENV.get('GROQ_API_KEY', '')}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        }
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        raw = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(raw)
        # Groq json_object wraps in a key sometimes
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list): return v
            return []
        return parsed
    except Exception as e:
        print(f"  [groq] Parse error: {e}")
        return []

# ── DeepSeek fallback ─────────────────────────────────────────────────────────
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

def deepseek_parse(text: str, year: int) -> list:
    """DeepSeek v3 fallback — very cheap."""
    prompt = EXTRACT_PROMPT.format(text=text, year=year)
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 2000,
    }).encode()

    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {ENV.get('DEEPSEEK_API_KEY', '')}",
            "Content-Type": "application/json",
        }
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        raw = data["choices"][0]["message"]["content"].strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw).strip()
        raw = re.sub(r'\s*```$', '', raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  [deepseek] Parse error: {e}")
        return []

# ── DB match + write ──────────────────────────────────────────────────────────
def match_and_write(line: str, sailings: list, dry_run: bool = False) -> int:
    """Match extracted sailings to DB rows and update price_ind."""
    if not sailings or not DB.exists():
        return 0

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    ts   = datetime.now(timezone.utc).isoformat()
    updated = 0

    for s in sailings:
        try:
            price = float(s.get("price_pp") or 0)
            if price <= 0:
                continue
            ship     = (s.get("ship") or "").strip()
            dep      = (s.get("departure") or "").strip()
            if not ship or not dep:
                continue

            # Match by line + ship (fuzzy) + departure date (±3 days)
            ship_word = ship.split()[-1]  # last word, e.g. "Grandeur"
            row = conn.execute("""
                SELECT id, ship, departure FROM cruises
                WHERE line = ?
                  AND ship LIKE ?
                  AND ABS(julianday(departure) - julianday(?)) <= 3
                ORDER BY ABS(julianday(departure) - julianday(?)) ASC
                LIMIT 1
            """, (line, f"%{ship_word}%", dep, dep)).fetchone()

            if row:
                print(f"  MATCH: {row['ship']} {row['departure']} → ${price:,.0f} pp (id={row['id']})")
                if not dry_run:
                    conn.execute(
                        "UPDATE cruises SET price_ind=?, price_ts=?, price_src=? WHERE id=?",
                        (price, ts, "ai_search/perplexity", row["id"])
                    )
                updated += 1
            else:
                print(f"  NO MATCH: {ship} {dep} ${price:,.0f}")
        except Exception as e:
            print(f"  [match] Error on {s}: {e}")

    if not dry_run:
        conn.commit()
    conn.close()
    return updated


# ── Per-line runner ───────────────────────────────────────────────────────────
def fetch_line(line: str, dry_run: bool = False) -> dict:
    cfg = LINE_CONFIGS.get(line)
    if not cfg:
        print(f"[{line}] No config — skipping")
        return {"line": line, "status": "no_config", "updated": 0}

    print(f"\n{'='*60}")
    print(f"[{line}] Starting AI price fetch")
    year = datetime.now().year

    # Step 1: Multi-source search (Perplexity + XAI Grok)
    print(f"  [1] Multi-source search (Perplexity + XAI Grok)...")
    raw_text = multi_search(cfg["search_name"])
    if not raw_text:
        return {"line": line, "status": "search_failed", "updated": 0}
    print(f"  [1] Combined: {len(raw_text)} chars")

    # Step 2: Gemini Flash parse
    print(f"  [2] Gemini Flash parsing...")
    sailings = gemini_parse(raw_text, year)
    if not sailings:
        print(f"  [2] Gemini failed — trying Groq Llama...")
        sailings = groq_parse(raw_text, year)
    if not sailings:
        print(f"  [2] Groq failed — trying DeepSeek...")
        sailings = deepseek_parse(raw_text, year)

    print(f"  [2] Extracted {len(sailings)} sailings")

    # Step 3: DB match + write
    print(f"  [3] Matching to DB and writing prices...")
    updated = match_and_write(line, sailings, dry_run=dry_run)
    print(f"  [3] Updated {updated} DB records")

    return {"line": line, "status": "ok", "extracted": len(sailings), "updated": updated}


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", default=None, help="Specific line to fetch (default: all)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true", dest="all_lines")
    args = ap.parse_args()

    lines_to_run = (
        [args.line] if args.line
        else sorted(LINE_CONFIGS, key=lambda x: LINE_CONFIGS[x]["priority"])
    )

    print(f"AI Price Fetcher — {datetime.now().strftime('%Y-%m-%d %H:%M MT')}")
    print(f"Lines: {', '.join(lines_to_run)}")
    print(f"Dry run: {args.dry_run}")

    results = []
    for line in lines_to_run:
        result = fetch_line(line, dry_run=args.dry_run)
        results.append(result)
        time.sleep(2)  # polite delay between lines

    print(f"\n{'='*60}")
    print("SUMMARY:")
    for r in results:
        status = r.get("status", "?")
        extracted = r.get("extracted", 0)
        updated = r.get("updated", 0)
        print(f"  {r['line']}: {status} | {extracted} extracted | {updated} DB updated")


if __name__ == "__main__":
    main()
