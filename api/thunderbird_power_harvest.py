"""
Thunderbird Power User Harvest
================================
Dreams2Memories Travel, LLC

Daily intelligence sweep for Claude Code / Anthropic ecosystem innovations.
Runs at 6:45 AM via systemd timer, feeds findings into the morning brief
as a "TECH SIGNAL" section.

Sources:
  - awesome-claude-code repo (README + recent commits)
  - Anthropic changelog / blog
  - Reddit r/ClaudeAI, r/LocalLLaMA  (via web search)
  - dev.to #claude tag

Model strategy:
  - Haiku  — classify each finding (relevant / not relevant)
  - Sonnet — synthesize D2M-relevant signals into brief section

Output:
  - ~/Thunderbird/logs/tech_harvest_YYYY-MM-DD.json
  - ~/Thunderbird/logs/tech_harvest_latest.json  (symlink / overwrite)
  - Appends "TECH SIGNAL" section to morning brief if run after brief is generated
  - Telegram push if any HIGH-priority signals found

Run:
  python3 thunderbird_power_harvest.py           # run harvest, save JSON
  python3 thunderbird_power_harvest.py --brief   # also inject into morning brief
  python3 thunderbird_power_harvest.py --test    # dry run, print to stdout only
"""

import json
import logging
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Browser-ish UA — bare curl UA gets 429'd by reddit and some CDNs
_UA = "Mozilla/5.0 (X11; Linux x86_64) D2M-TechHarvest/2.0"

logger = logging.getLogger("thunderbird_power_harvest")

THUNDERBIRD_DIR  = Path.home() / "Thunderbird"
LOG_DIR          = THUNDERBIRD_DIR / "logs"
HARVEST_LOG      = LOG_DIR / f"tech_harvest_{datetime.now().strftime('%Y-%m-%d')}.json"
HARVEST_LATEST   = LOG_DIR / "tech_harvest_latest.json"
POE_ENV_FILE     = THUNDERBIRD_DIR / "config" / "poe.env"
TELEGRAM_BOT_ENV = THUNDERBIRD_DIR / "config" / "d2mc2c_bot.env"

# Groq client — fast/light classification and synthesis via Groq API ($0 / fast)
try:
    from thunderbird_model_router import _call_groq, GROQ_API_KEY as _GROQ_KEY
    _groq_ok = bool(_GROQ_KEY)
    if not _groq_ok:
        logger.info("No GROQ_API_KEY — running in fetch-only mode (raw content saved, no LLM classification)")
except ImportError:
    _groq_ok = False
    logger.warning("thunderbird_model_router not found — fetch-only mode")

# ── Source definitions ────────────────────────────────────────────────────────

SOURCES = [
    {
        "id":    "awesome_cc",
        "name":  "awesome-claude-code",
        "type":  "url",
        "url":   "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md",
        "desc":  "Community-curated Claude Code tools, hooks, skills, MCP servers",
    },
    {
        "id":    "anthropic_changelog",
        "name":  "Anthropic Changelog",
        "type":  "url",
        "url":   "https://www.anthropic.com/changelog",
        "desc":  "Official Anthropic product updates and releases",
    },
    {
        "id":    "anthropic_news",
        "name":  "Anthropic News",
        "type":  "url",
        "url":   "https://www.anthropic.com/news",
        "desc":  "Anthropic blog posts and announcements",
    },
    {
        "id":    "reddit_claudeai",
        "name":  "Reddit r/ClaudeAI",
        "type":  "feed",
        "fmt":   "rss",
        "url":   "https://www.reddit.com/r/ClaudeAI/top/.rss?t=week&limit=25",
        "desc":  "Community discussions on Claude Code power user techniques",
    },
    {
        "id":    "hn_claude",
        "name":  "Hacker News — Claude Code",
        "type":  "feed",
        "fmt":   "hn",
        "url":   "https://hn.algolia.com/api/v1/search_by_date?query=claude%20code&tags=story&hitsPerPage=20",
        "desc":  "HN stories mentioning Claude Code (last posted)",
    },
    {
        "id":    "hn_mcp",
        "name":  "Hacker News — MCP / Anthropic",
        "type":  "feed",
        "fmt":   "hn",
        "url":   "https://hn.algolia.com/api/v1/search?query=MCP%20server%20anthropic&tags=story&hitsPerPage=15",
        "desc":  "HN stories on MCP servers and Anthropic tooling",
    },
    {
        "id":    "devto_claude",
        "name":  "dev.to Claude",
        "type":  "feed",
        "fmt":   "devto",
        "url":   "https://dev.to/api/articles?tag=claude&per_page=15&top=7",
        "desc":  "Developer articles tagged #claude (top of last week)",
    },
]

# D2M relevance keywords — anything touching these is high-priority
D2M_KEYWORDS = [
    "travel", "booking", "hotel", "flight", "cruise", "itinerary",
    "client", "proposal", "MCP", "hooks", "automation", "gmail", "calendar",
    "tool use", "agent", "Claude Code", "claude-sonnet", "claude-opus",
    "files api", "skills api", "streaming", "async", "telegram",
]

# ── Fetch ─────────────────────────────────────────────────────────────────────

def _curl(url: str, timeout: int = 20) -> str:
    """Raw curl with a browser UA. Returns body or '' on failure."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), "-A", _UA, url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception as e:
        logger.warning("curl(%s): %s", url, e)
        return ""


def _fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch raw page content (capped)."""
    return _curl(url, timeout)[:8000]


def _fetch_feed(src: dict, timeout: int = 20) -> str:
    """Fetch a structured feed (HN/dev.to JSON, reddit RSS) → newline list of 'Title — url'.

    Replaces the old _web_search stub, which always returned '' (every search
    source was guaranteed empty). Each format is parsed into title+url lines so
    the keyword classifier has real signal to score.
    """
    body = _curl(src["url"], timeout)
    if not body:
        return ""
    fmt = src.get("fmt", "")
    items: list[str] = []
    try:
        if fmt == "hn":
            for h in json.loads(body).get("hits", []):
                title = (h.get("title") or h.get("story_title") or "").strip()
                if not title:
                    continue
                link = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
                items.append(f"{title} — {link}")
        elif fmt == "devto":
            for a in json.loads(body):
                title = (a.get("title") or "").strip()
                if not title:
                    continue
                desc = (a.get("description") or "").strip()
                items.append(f"{title} — {a.get('url','')}" + (f" :: {desc}" if desc else ""))
        elif fmt == "rss":
            # Atom/RSS: pull <title> + <link href=...> (skip the feed's own header title)
            titles = re.findall(r"<title[^>]*>(.*?)</title>", body, re.S)
            links  = re.findall(r'<link[^>]*href="([^"]+)"', body)
            for t in titles[1:]:
                t = re.sub(r"<[^>]+>", "", t).strip()
                if t:
                    items.append(t)
        else:
            return body[:8000]
    except Exception as e:
        logger.warning("fetch_feed(%s): parse error %s", src.get("name"), e)
        return body[:4000]
    return "\n".join(items[:40])[:8000]

# ── Classify ──────────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """You are a relevance classifier for Dreams2Memories Travel, LLC.
We are a luxury travel agency using Claude Code and MCP tools to automate our operations.

Classify this content snippet as:
- HIGH: Directly useful for our travel agency operations (MCP tools, Claude Code hooks, automation, Gmail/Calendar/Drive integration, model routing, token optimization, client communication tools)
- MED:  Potentially useful, worth noting (AI/LLM advances, new models, API changes)
- LOW:  Not relevant (academic research, other domains, general AI ethics discussion)

Respond with JSON only: {"priority": "HIGH|MED|LOW", "reason": "one sentence"}

Content:
"""


def _classify_by_keyword(text: str) -> dict:
    """Deterministic, zero-cost fallback classifier.

    Scores by distinct D2M_KEYWORDS hits so the harvest still produces real
    HIGH/MED/LOW signal when no LLM provider is configured (the Groq router is
    frequently unavailable — see import guard above). HIGH >=4 distinct hits,
    MED 1-3, LOW 0.
    """
    if not text:
        return {"priority": "LOW", "reason": "empty content", "via": "keyword"}
    low = text.lower()
    hits = sorted({kw for kw in D2M_KEYWORDS if kw.lower() in low})
    if len(hits) >= 4:
        pri = "HIGH"
    elif hits:
        pri = "MED"
    else:
        pri = "LOW"
    reason = f"{len(hits)} D2M keyword(s): {', '.join(hits[:6])}" if hits else "no D2M keywords matched"
    return {"priority": pri, "reason": reason, "via": "keyword"}


def _classify(text: str) -> dict:
    """Classify content relevance. Groq llama if available, else keyword fallback."""
    if not text:
        return {"priority": "LOW", "reason": "empty content", "via": "none"}
    if not _groq_ok:
        return _classify_by_keyword(text)
    try:
        text_out = _call_groq(CLASSIFY_PROMPT, text[:1500], model="fast", max_tokens=100)
        start = text_out.find("{")
        end   = text_out.rfind("}") + 1
        if start >= 0 and end > start:
            out = json.loads(text_out[start:end])
            out.setdefault("via", "groq")
            return out
        return _classify_by_keyword(text)
    except Exception as e:
        logger.warning("classify (groq) fell back to keyword: %s", e)
        return _classify_by_keyword(text)

# ── Synthesize ────────────────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """You are VCSAF (Victory Hale, SES-6), Chief of Staff for Dreams2Memories Travel, LLC.

Synthesize the following raw intel harvest into a "TECH SIGNAL" section for the morning brief.

Format (strict):
## 🔧 TECH SIGNAL — {date}

### D2M RELEVANCE SUMMARY
(3-5 bullets: what matters to us specifically — tools we should adopt, API changes that affect us, automation wins)

### ANALYSIS
(What these signals mean for D2M operations — concrete next steps if warranted)

### RAW SIGNALS
(List all HIGH and MED priority findings with source and brief description)

If there are no HIGH priority signals today, say so clearly and list MED signals.
Commander should receive analysis first, raw data after. Never invert this.

Raw intel:
"""


def _synthesize_deterministic(findings: list[dict], date_str: str) -> str:
    """Build a TECH SIGNAL brief section with no LLM — used whenever Groq is offline.

    Previously synthesis returned '' without Groq, so the brief section was blank
    even when HIGH signals existed. This guarantees the brief always populates.
    """
    hi  = [f for f in findings if f.get("priority") == "HIGH"]
    med = [f for f in findings if f.get("priority") == "MED"]
    lines = [f"## 🔧 TECH SIGNAL — {date_str}", ""]
    lines += ["### D2M RELEVANCE SUMMARY",
              f"- {len(hi)} HIGH / {len(med)} MED signal(s) across {len(findings)} sources "
              f"(keyword-classified; LLM synthesis offline).", ""]
    if hi:
        lines.append("### HIGH")
        for f in hi:
            preview = (f.get("content", "").splitlines() or [""])[0][:120]
            lines.append(f"- **{f['source']}** — {f['reason']}")
            if preview:
                lines.append(f"  {preview}")
    if med:
        lines.append("")
        lines.append("### MED")
        for f in med:
            lines.append(f"- {f['source']} — {f['reason']}")
    if not hi and not med:
        lines.append("No HIGH or MED signals today.")
    return "\n".join(lines)


def _synthesize(findings: list[dict], date_str: str) -> str:
    """Synthesize findings into a morning-brief section. Groq if available, else deterministic."""
    if not findings:
        return f"## 🔧 TECH SIGNAL — {date_str}\n\nNo sources returned content today."
    if not _groq_ok:
        return _synthesize_deterministic(findings, date_str)
    raw = "\n\n".join([
        f"[{f['source']}] {f['priority']} — {f.get('summary', f.get('content', '')[:300])}"
        for f in findings
        if f.get("priority") in ("HIGH", "MED")
    ])
    if not raw:
        return _synthesize_deterministic(findings, date_str)
    try:
        return _call_groq(
            SYNTHESIS_PROMPT.replace("{date}", date_str),
            raw,
            model="light",
            max_tokens=1500,
        )
    except Exception as e:
        logger.error("synthesize (groq) fell back to deterministic: %s", e)
        return _synthesize_deterministic(findings, date_str)

# ── Telegram push ─────────────────────────────────────────────────────────────

def _send_telegram(message: str) -> bool:
    """Push high-priority signal alert to Commander via Telegram."""
    import urllib.request
    token, chat_id = "", ""
    for env_file in [POE_ENV_FILE, TELEGRAM_BOT_ENV]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            if "TELEGRAM_BOT_TOKEN=" in line and not token:
                token = line.split("=", 1)[1].strip()
            if "TELEGRAM_COMMANDER_ID=" in line and not chat_id:
                chat_id = line.split("=", 1)[1].strip()
    if not token or not chat_id:
        return False
    try:
        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
        req     = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        logger.error("telegram: %s", e)
        return False

# ── Main harvest ──────────────────────────────────────────────────────────────

def run_harvest(dry_run: bool = False) -> dict:
    """Run the full harvest cycle. Returns summary dict."""
    date_str  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    findings  = []
    high_count = 0

    logger.info("Starting power harvest — %s", date_str)

    for src in SOURCES:
        logger.info("Processing source: %s", src["name"])

        # Fetch content
        if src["type"] == "url":
            content = _fetch_url(src["url"])
        else:
            content = _fetch_feed(src)

        if not content:
            logger.warning("No content from %s", src["name"])
            findings.append({
                "source":   src["name"],
                "priority": "LOW",
                "reason":   "fetch failed or empty",
                "content":  "",
            })
            continue

        # Classify
        classification = _classify(content)
        priority = classification.get("priority", "MED")
        if priority == "HIGH":
            high_count += 1

        findings.append({
            "source":   src["name"],
            "priority": priority,
            "reason":   classification.get("reason", ""),
            "via":      classification.get("via", ""),
            "content":  content[:2000],  # cap stored content
            "url":      src.get("url", ""),
        })

    # Synthesize
    brief_section = _synthesize(findings, date_str)

    result = {
        "date":          date_str,
        "sources_count": len(SOURCES),
        "high_count":    high_count,
        "findings":      findings,
        "brief_section": brief_section,
    }

    if not dry_run:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        HARVEST_LOG.write_text(json.dumps(result, indent=2), encoding="utf-8")
        HARVEST_LATEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
        logger.info("Harvest saved to %s", HARVEST_LOG)

        # Telegram push for HIGH signals
        if high_count > 0:
            alert = (
                f"🔧 <b>TECH SIGNAL — {high_count} HIGH-priority signal(s)</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                + "\n".join([
                    f"• [{f['source']}] {f['reason']}"
                    for f in findings if f.get("priority") == "HIGH"
                ])
                + f"\n\nFull analysis in morning brief."
            )
            _send_telegram(alert)

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    dry_run    = "--test" in sys.argv
    show_brief = "--brief" in sys.argv

    result = run_harvest(dry_run=dry_run)

    if dry_run or show_brief:
        print(result.get("brief_section", "No brief section generated."))
    else:
        high = result["high_count"]
        total = result["sources_count"]
        print(f"Harvest complete: {high} HIGH signals from {total} sources → {HARVEST_LATEST}")
