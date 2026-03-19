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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("thunderbird_power_harvest")

THUNDERBIRD_DIR  = Path.home() / "Thunderbird"
LOG_DIR          = THUNDERBIRD_DIR / "logs"
HARVEST_LOG      = LOG_DIR / f"tech_harvest_{datetime.now().strftime('%Y-%m-%d')}.json"
HARVEST_LATEST   = LOG_DIR / "tech_harvest_latest.json"
POE_ENV_FILE     = THUNDERBIRD_DIR / "config" / "poe.env"
TELEGRAM_BOT_ENV = THUNDERBIRD_DIR / "config" / "d2mc2c_bot.env"

# Anthropic client — NOTE: Python SDK requires API key (pay-as-you-go).
# Max plan works via Claude CLI OAuth only. If no API key, classification/synthesis
# gracefully degrades — URL fetching still works and raw content is saved.
try:
    import anthropic
    import os as _os
    _client = anthropic.Anthropic() if _os.environ.get("ANTHROPIC_API_KEY") else None
    if not _client:
        logger.info("No ANTHROPIC_API_KEY — running in fetch-only mode (raw content saved, no LLM classification)")
except ImportError:
    _client = None

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
        "type":  "search",
        "query": "site:reddit.com/r/ClaudeAI Claude Code tips hooks MCP new features 2026",
        "desc":  "Community discussions on Claude Code power user techniques",
    },
    {
        "id":    "reddit_mcp",
        "name":  "Reddit MCP/LLM",
        "type":  "search",
        "query": "site:reddit.com Claude Code MCP server new 2026 tool automation",
        "desc":  "MCP server innovations and automation techniques",
    },
    {
        "id":    "devto_claude",
        "name":  "dev.to Claude",
        "type":  "search",
        "query": "site:dev.to claude code hooks skills automation 2026",
        "desc":  "Developer articles on Claude Code techniques",
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

def _fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch URL content via curl."""
    try:
        result = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        return result.stdout[:8000] if result.returncode == 0 else ""
    except Exception as e:
        logger.warning("fetch_url(%s): %s", url, e)
        return ""


def _web_search(query: str) -> str:
    """Use Anthropic Claude to web search (via tool use)."""
    if not _client:
        return ""
    try:
        from thunderbird_poe_config import route_model
        response = _client.messages.create(
            model=route_model("classify"),
            max_tokens=1000,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
            }],
            messages=[{"role": "user", "content": f"Search: {query}. Return the top 5 results as a brief summary."}],
        )
        # Extract text from response
        for block in response.content:
            if hasattr(block, "text"):
                return block.text[:3000]
        return ""
    except Exception as e:
        logger.warning("web_search(%s): %s", query, e)
        return ""

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


def _classify(text: str) -> dict:
    """Classify content relevance using Haiku (cheap)."""
    if not _client or not text:
        return {"priority": "MED", "reason": "classification unavailable"}
    try:
        from thunderbird_poe_config import route_model
        response = _client.messages.create(
            model=route_model("intel_classify"),
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": CLASSIFY_PROMPT + text[:1500],
            }],
        )
        text_out = response.content[0].text if response.content else ""
        # Extract JSON
        start = text_out.find("{")
        end   = text_out.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text_out[start:end])
        return {"priority": "MED", "reason": text_out[:100]}
    except Exception as e:
        logger.warning("classify: %s", e)
        return {"priority": "MED", "reason": str(e)[:80]}

# ── Synthesize ────────────────────────────────────────────────────────────────

SYNTHESIS_PROMPT = """You are COS (Victoria Hale), Chief of Staff for Dreams2Memories Travel, LLC.

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


def _synthesize(findings: list[dict], date_str: str) -> str:
    """Use Sonnet to synthesize findings into morning brief section."""
    if not _client or not findings:
        return ""
    raw = "\n\n".join([
        f"[{f['source']}] {f['priority']} — {f.get('summary', f.get('content', '')[:300])}"
        for f in findings
        if f.get("priority") in ("HIGH", "MED")
    ])
    if not raw:
        return f"## TECH SIGNAL — {date_str}\n\nNo HIGH or MED signals today."
    try:
        from thunderbird_poe_config import route_model
        response = _client.messages.create(
            model=route_model("intel_analysis"),
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.replace("{date}", date_str) + raw,
            }],
        )
        return response.content[0].text if response.content else ""
    except Exception as e:
        logger.error("synthesize: %s", e)
        return f"## TECH SIGNAL — {date_str}\n\nSynthesis failed: {e}"

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
            content = _web_search(src["query"])

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
