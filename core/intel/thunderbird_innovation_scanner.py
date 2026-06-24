"""
Thunderbird Innovation Scanner
================================

Scheduled intelligence system that scans Reddit, GitHub, HN, Discord,
and competitor ecosystems for AI/MCP/agent innovations relevant to D2M.

Standing Order (2026-03-20):
  "DO NOT assume that because some new idea is not immediately relevant
   to our setup, or is not travel related, that we cannot use it. Import
   ALL reasonable, and even some unreasonable innovations. No ONE person
   or agent decides what is and is not useful. The Domains will decide,
   I will decide."

Scan Domains (all 21 staff positions evaluate each finding):
  CEO, COS, CBO, CINO, SVP-CX, SVP-Intel, SVP-Tech, SVP-Ops,
  VP-Concierge, VP-Research, VP-Finance, VP-Brand, VP-Innovation,
  Advisory: Ethics, Advisory: Strategy, Advisory: Design,
  + A2, A3, A5, A6, A9

Cadence:
  - Daily 6:30 AM MT: Quick scan (Reddit hot, GitHub trending, HN front page)
  - Weekly Sunday 8 PM MT: Deep scan (all sources, full competitor analysis)
  - On-demand via MCP tool or Telegram C2 /scan command

Output:
  - intel/daily_innovation_digest.md (overwritten daily)
  - intel/weekly_innovation_report.md (weekly archive)
  - Telegram C2 notification with top 5 findings
  - Morning briefing injection

Dependencies: requests, feedparser, beautifulsoup4
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("thunderbird_innovation_scanner")

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
INTEL_DIR = THUNDERBIRD_DIR / "intel"
INTEL_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Thunderbird-Innovation-Scanner/1.0 (D2M Travel Intelligence)"


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class Innovation:
    """A single innovation finding."""
    title: str
    source: str           # e.g., "reddit/r/ClaudeAI", "github/trending", "hn"
    url: str
    description: str
    category: str          # mcp, agents, automation, voice, browser, security, etc.
    relevance: str         # Direct / Indirect / Exploratory
    difficulty: str        # Easy / Medium / Hard
    priority: str          # NOW / SOON / WATCH
    score: int = 0         # Engagement score (upvotes, stars, etc.)
    discovered: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ScanResult:
    """Result of a full innovation scan."""
    scan_type: str         # "daily" or "weekly"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    findings: list[Innovation] = field(default_factory=list)
    sources_scanned: int = 0
    sources_failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def top_findings(self) -> list[Innovation]:
        """Top 10 by score."""
        return sorted(self.findings, key=lambda f: f.score, reverse=True)[:10]


# ============================================================================
# Reddit Scanner
# ============================================================================

REDDIT_TARGETS = {
    "r/ClaudeAI": "https://www.reddit.com/r/ClaudeAI/hot.json?limit=25",
    "r/anthropic": "https://www.reddit.com/r/anthropic/hot.json?limit=25",
    "r/LocalLLaMA": "https://www.reddit.com/r/LocalLLaMA/hot.json?limit=25",
    "r/MCP": "https://www.reddit.com/r/mcp/hot.json?limit=25",
    "r/MachineLearning": "https://www.reddit.com/r/MachineLearning/hot.json?limit=15",
    "r/artificial": "https://www.reddit.com/r/artificial/hot.json?limit=15",
    "r/ChatGPT": "https://www.reddit.com/r/ChatGPT/hot.json?limit=15",
    "r/Cursor": "https://www.reddit.com/r/cursor/hot.json?limit=15",
    "r/singularity": "https://www.reddit.com/r/singularity/hot.json?limit=10",
    "r/TravelAgents": "https://www.reddit.com/r/TravelAgents/hot.json?limit=10",
    "r/n8n": "https://www.reddit.com/r/n8n/hot.json?limit=10",
    "r/selfhosted": "https://www.reddit.com/r/selfhosted/hot.json?limit=10",
}

# Keywords that signal innovation worth capturing
INNOVATION_KEYWORDS = [
    # MCP & Protocol
    "mcp", "model context protocol", "mcp server", "mcp tool",
    # Agents
    "agent", "multi-agent", "agentic", "autonomous", "crew",
    "autogen", "langgraph", "mastra", "swarm",
    # Claude specific
    "claude code", "claude agent", "anthropic", "claude sdk",
    "claude hook", "slash command", "claude team",
    # Automation
    "n8n", "make.com", "zapier", "automation", "workflow",
    "cron", "scheduler", "pipeline",
    # Voice & Realtime
    "voice agent", "realtime", "speech", "whisper", "tts",
    "voice ai", "phone agent", "call center",
    # Browser & Web
    "browser agent", "playwright", "puppeteer", "web scraping",
    "browser use", "operator", "mariner",
    # Knowledge & Memory
    "rag", "vector", "knowledge base", "memory", "embedding",
    "qdrant", "pinecone", "chroma",
    # Dev Tools
    "cursor", "windsurf", "copilot", "codex", "devin",
    # Business
    "crm", "booking", "travel", "concierge", "hotel",
    "email automation", "calendar ai", "gmail",
    # Infrastructure
    "self-hosted", "docker", "deploy", "production",
    "rate limit", "cost", "optimization", "caching",
    # Security
    "prompt injection", "guardrail", "safety", "auth",
    # New capabilities
    "breakthrough", "new feature", "just released", "announced",
    "game changer", "mind blown", "holy shit",
]


def _scan_reddit(subreddits: Optional[dict] = None) -> list[Innovation]:
    """Scan Reddit for innovation posts."""
    findings = []
    targets = subreddits or REDDIT_TARGETS

    for sub_name, url in targets.items():
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
            if resp.status_code == 429:
                logger.warning(f"Reddit rate limited on {sub_name}, skipping")
                time.sleep(2)
                continue
            resp.raise_for_status()
            data = resp.json()

            for post in data.get("data", {}).get("children", []):
                pd = post.get("data", {})
                title = pd.get("title", "")
                selftext = pd.get("selftext", "")[:500]
                score = pd.get("score", 0)
                url_link = f"https://reddit.com{pd.get('permalink', '')}"

                # Check if post matches innovation keywords
                full_text = f"{title} {selftext}".lower()
                matched = [kw for kw in INNOVATION_KEYWORDS if kw in full_text]

                if matched and score >= 5:
                    # Categorize
                    category = _categorize(matched)

                    findings.append(Innovation(
                        title=title[:200],
                        source=f"reddit/{sub_name}",
                        url=url_link,
                        description=selftext[:300] if selftext else title,
                        category=category,
                        relevance="Direct" if any(k in full_text for k in ["mcp", "claude", "travel", "agent"]) else "Indirect",
                        difficulty="Medium",
                        priority="WATCH",
                        score=score,
                    ))

            logger.info(f"Reddit {sub_name}: scanned, {len([f for f in findings if sub_name in f.source])} hits")
            time.sleep(1)  # Rate limit courtesy

        except Exception as e:
            logger.warning(f"Reddit {sub_name} failed: {e}")

    return findings


def _categorize(matched_keywords: list[str]) -> str:
    """Categorize an innovation by its matched keywords."""
    cats = {
        "mcp": ["mcp", "model context protocol", "mcp server", "mcp tool"],
        "agents": ["agent", "multi-agent", "agentic", "autonomous", "crew", "autogen", "langgraph", "swarm"],
        "claude": ["claude code", "claude agent", "anthropic", "claude sdk", "claude hook"],
        "automation": ["n8n", "make.com", "zapier", "automation", "workflow", "cron", "pipeline"],
        "voice": ["voice agent", "realtime", "speech", "whisper", "tts", "voice ai"],
        "browser": ["browser agent", "playwright", "puppeteer", "web scraping", "operator"],
        "knowledge": ["rag", "vector", "knowledge base", "memory", "embedding", "qdrant"],
        "devtools": ["cursor", "windsurf", "copilot", "codex", "devin"],
        "security": ["prompt injection", "guardrail", "safety", "auth"],
        "infrastructure": ["self-hosted", "docker", "deploy", "production", "caching"],
    }
    for cat, keywords in cats.items():
        if any(kw in matched_keywords for kw in keywords):
            return cat
    return "general"


# ============================================================================
# GitHub Trending Scanner
# ============================================================================

def _scan_github_trending() -> list[Innovation]:
    """Scan GitHub trending for AI/ML repositories."""
    findings = []
    searches = [
        "mcp server",
        "ai agent framework",
        "claude tool",
        "browser automation ai",
        "voice agent",
    ]

    for query in searches:
        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"{query} created:>{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10,
                },
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": USER_AGENT,
                },
                timeout=15,
            )
            resp.raise_for_status()
            repos = resp.json().get("items", [])

            for repo in repos:
                stars = repo.get("stargazers_count", 0)
                if stars < 10:
                    continue

                desc = repo.get("description", "") or ""
                findings.append(Innovation(
                    title=repo.get("full_name", ""),
                    source="github/trending",
                    url=repo.get("html_url", ""),
                    description=desc[:300],
                    category=_categorize([kw for kw in INNOVATION_KEYWORDS if kw in f"{repo.get('full_name', '')} {desc}".lower()]),
                    relevance="Direct" if any(k in desc.lower() for k in ["mcp", "travel", "agent"]) else "Indirect",
                    difficulty="Medium",
                    priority="WATCH",
                    score=stars,
                ))

            time.sleep(1)

        except Exception as e:
            logger.warning(f"GitHub search '{query}' failed: {e}")

    return findings


# ============================================================================
# Hacker News Scanner
# ============================================================================

def _scan_hacker_news() -> list[Innovation]:
    """Scan Hacker News top and best stories for AI innovations."""
    findings = []

    try:
        # Get top 100 story IDs
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10,
        )
        resp.raise_for_status()
        story_ids = resp.json()[:100]

        for sid in story_ids:
            try:
                item = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=5,
                ).json()

                if not item:
                    continue

                title = item.get("title", "")
                score = item.get("score", 0)
                url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")

                title_lower = title.lower()
                matched = [kw for kw in INNOVATION_KEYWORDS if kw in title_lower]

                if matched and score >= 20:
                    findings.append(Innovation(
                        title=title[:200],
                        source="hackernews",
                        url=url,
                        description=title,
                        category=_categorize(matched),
                        relevance="Direct" if any(k in title_lower for k in ["mcp", "claude", "anthropic"]) else "Indirect",
                        difficulty="Medium",
                        priority="WATCH",
                        score=score,
                    ))

            except Exception:
                continue

        logger.info(f"HN: scanned top 100, {len(findings)} hits")

    except Exception as e:
        logger.warning(f"HN scan failed: {e}")

    return findings


# ============================================================================
# RSS Feed Scanner (Tech Blogs)
# ============================================================================

BLOG_FEEDS = {
    "Anthropic Blog": "https://www.anthropic.com/rss.xml",
    "Claude Code Releases": "https://github.com/anthropics/claude-code/releases.atom",
    "MCP Servers": "https://github.com/modelcontextprotocol/servers/releases.atom",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "LangChain Blog": "https://blog.langchain.dev/rss/",
    "Hacker News Best": "https://hnrss.org/best?q=AI+agent+MCP+claude&count=20",
}


def _scan_blogs() -> list[Innovation]:
    """Scan RSS feeds from key tech blogs."""
    import feedparser

    findings = []
    cutoff = datetime.now() - timedelta(days=7)

    for name, url in BLOG_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:300]

                title_lower = f"{title} {summary}".lower()
                matched = [kw for kw in INNOVATION_KEYWORDS if kw in title_lower]

                if matched:
                    findings.append(Innovation(
                        title=title[:200],
                        source=f"blog/{name}",
                        url=link,
                        description=BeautifulSoup(summary, "html.parser").get_text()[:300],
                        category=_categorize(matched),
                        relevance="Direct",
                        difficulty="Medium",
                        priority="SOON",
                        score=50,  # Blogs don't have upvotes; default weight
                    ))

            logger.info(f"Blog {name}: {len([f for f in findings if name in f.source])} hits")

        except Exception as e:
            logger.warning(f"Blog {name} failed: {e}")

    return findings


# ============================================================================
# Main Scanner
# ============================================================================

def run_daily_scan() -> ScanResult:
    """Run the daily quick scan — Reddit hot + GitHub trending + HN top."""
    result = ScanResult(scan_type="daily")

    logger.info("Starting daily innovation scan...")

    # Reddit
    try:
        result.findings.extend(_scan_reddit())
        result.sources_scanned += len(REDDIT_TARGETS)
    except Exception as e:
        result.errors.append(f"Reddit: {e}")
        result.sources_failed += 1

    # GitHub
    try:
        result.findings.extend(_scan_github_trending())
        result.sources_scanned += 5
    except Exception as e:
        result.errors.append(f"GitHub: {e}")
        result.sources_failed += 1

    # Hacker News
    try:
        result.findings.extend(_scan_hacker_news())
        result.sources_scanned += 1
    except Exception as e:
        result.errors.append(f"HN: {e}")
        result.sources_failed += 1

    # Blogs
    try:
        result.findings.extend(_scan_blogs())
        result.sources_scanned += len(BLOG_FEEDS)
    except Exception as e:
        result.errors.append(f"Blogs: {e}")
        result.sources_failed += 1

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for f in result.findings:
        if f.url not in seen_urls:
            seen_urls.add(f.url)
            unique.append(f)
    result.findings = unique

    # Sort by score
    result.findings.sort(key=lambda f: f.score, reverse=True)

    logger.info(
        f"Daily scan complete: {len(result.findings)} findings from "
        f"{result.sources_scanned} sources ({result.sources_failed} failed)"
    )

    # Write digest
    _write_digest(result)

    return result


def run_weekly_scan() -> ScanResult:
    """Run the weekly deep scan — all sources, full analysis."""
    result = run_daily_scan()
    result.scan_type = "weekly"

    # Weekly gets archived
    week_file = INTEL_DIR / f"weekly_innovation_{datetime.now().strftime('%Y%m%d')}.md"
    _write_digest(result, output_path=week_file)

    return result


def _write_digest(result: ScanResult, output_path: Optional[Path] = None):
    """Write scan results as markdown digest."""
    path = output_path or INTEL_DIR / "daily_innovation_digest.md"

    lines = [
        f"# Innovation Scan — {result.scan_type.title()}",
        f"**Generated:** {result.timestamp}",
        f"**Sources:** {result.sources_scanned} scanned, {result.sources_failed} failed",
        f"**Findings:** {len(result.findings)} total",
        "",
        "---",
        "",
    ]

    if result.errors:
        lines.append("## Errors")
        for e in result.errors:
            lines.append(f"- {e}")
        lines.append("")

    # Group by category
    categories: dict[str, list[Innovation]] = {}
    for f in result.findings:
        categories.setdefault(f.category, []).append(f)

    # Top 10 overall
    lines.append("## Top 10 Findings (by engagement)")
    lines.append("")
    lines.append("| # | Score | Source | Title | Category |")
    lines.append("|---|-------|--------|-------|----------|")
    for i, f in enumerate(result.top_findings, 1):
        title_short = f.title[:60] + "..." if len(f.title) > 60 else f.title
        lines.append(f"| {i} | {f.score} | {f.source} | [{title_short}]({f.url}) | {f.category} |")
    lines.append("")

    # By category
    for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
        lines.append(f"## {cat.title()} ({len(items)} findings)")
        lines.append("")
        for f in items[:15]:
            lines.append(f"### [{f.title[:80]}]({f.url})")
            lines.append(f"- **Source:** {f.source} | **Score:** {f.score}")
            lines.append(f"- **Relevance:** {f.relevance} | **Difficulty:** {f.difficulty}")
            if f.description and f.description != f.title:
                lines.append(f"- {f.description[:200]}")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Digest written to {path}")

    # Email to Commander inbox — SO 27 MAR 2026: intel reports are full sends, not drafts
    if output_path is None:  # daily digest only, not weekly archive copies
        try:
            import sys as _sys
            _sys.path.insert(0, str(THUNDERBIRD_DIR))
            from core.email.thunderbird_gmail import gmail_send_from_wing
            ts_label = datetime.now().strftime("%Y-%m-%d")
            digest_text = "\n".join(lines)
            gmail_send_from_wing(
                to="johnloucks3@gmail.com",
                subject=f"Innovation Scan — {result.scan_type.title()} {ts_label} ({len(result.findings)} findings)",
                body=digest_text,
                persona_id="A12",
            )
            logger.info("Innovation digest sent to johnloucks3 inbox.")
        except Exception as _e:
            logger.warning(f"Innovation digest email failed: {_e}")


def get_digest_for_briefing(max_items: int = 5) -> str:
    """Get a compact digest for injection into the morning briefing."""
    digest_file = INTEL_DIR / "daily_innovation_digest.md"
    if not digest_file.exists():
        return ""

    # Parse the top findings
    content = digest_file.read_text(encoding="utf-8")
    lines = ["INNOVATION INTEL (automated daily scan):"]

    # Extract table rows
    in_table = False
    count = 0
    for line in content.split("\n"):
        if "| # |" in line:
            in_table = True
            continue
        if in_table and line.startswith("|"):
            if "---" in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 5 and count < max_items:
                lines.append(f"  {parts[0]}. [{parts[3]}] ({parts[2]}) — score {parts[1]}")
                count += 1
        elif in_table and not line.startswith("|"):
            break

    if count == 0:
        return ""

    return "\n".join(lines)


# ============================================================================
# MCP Tool Registration
# ============================================================================

def register_innovation_tools(mcp_server):
    """Register innovation scanner MCP tools."""

    @mcp_server.tool(
        name="run_innovation_scan",
        annotations={"title": "Run Innovation Scan", "readOnlyHint": False},
    )
    async def run_innovation_scan(scan_type: str = "daily") -> str:
        """Run an innovation scan across Reddit, GitHub, HN, and tech blogs.
        scan_type: 'daily' (quick) or 'weekly' (deep)."""
        if scan_type == "weekly":
            result = run_weekly_scan()
        else:
            result = run_daily_scan()
        return json.dumps({
            "status": "complete",
            "findings": len(result.findings),
            "sources_scanned": result.sources_scanned,
            "top_5": [asdict(f) for f in result.top_findings[:5]],
            "digest_path": str(INTEL_DIR / "daily_innovation_digest.md"),
        }, indent=2)

    @mcp_server.tool(
        name="get_innovation_digest",
        annotations={"title": "Get Innovation Digest", "readOnlyHint": True},
    )
    async def get_innovation_digest() -> str:
        """Get the latest innovation scan digest."""
        digest = INTEL_DIR / "daily_innovation_digest.md"
        if digest.exists():
            return digest.read_text(encoding="utf-8")[:5000]
        return "No digest available. Run innovation_scan first."


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    scan_type = sys.argv[1] if len(sys.argv) > 1 else "daily"
    print(f"Running {scan_type} innovation scan...")

    if scan_type == "weekly":
        result = run_weekly_scan()
    else:
        result = run_daily_scan()

    print(f"\nResults: {len(result.findings)} findings from {result.sources_scanned} sources")
    print(f"Top 5:")
    for i, f in enumerate(result.top_findings[:5], 1):
        print(f"  {i}. [{f.score}] {f.source}: {f.title[:70]}")
    print(f"\nDigest: {INTEL_DIR / 'daily_innovation_digest.md'}")
