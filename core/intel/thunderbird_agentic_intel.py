"""
Thunderbird Agentic Intelligence Scanner
==========================================

Nightly 01:00 MDT scan for worldwide developments that mirror or eclipse
the Thunderbird OS setup: Claude Code, Goose, multi-model orchestration,
agentic coding, inter-agent communication, AI staff systems.

Standing Order 2026-04-06:
  "Anything world-wide that mirrors our setup or eclipses it."
  Runs through Hale. Sent to johnloucks3@gmail.com.

Sources:
  - Reddit (15 subreddits)
  - Hacker News (top + new stories)
  - GitHub trending + search
  - Serper API (live web search)
  - RSS feeds (key AI blogs)

Output:
  - Email to johnloucks3@gmail.com (full send, Hale voice)
  - intel/nightly_agentic_intel.md (archive)
  - intel/nightly_agentic_intel.json (structured)

Dependencies: requests, feedparser, google-auth, google-api-python-client
"""

import base64
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import requests

try:
    import feedparser
except ImportError:
    feedparser = None

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger("thunderbird_agentic_intel")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ============================================================================
# Config
# ============================================================================

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
INTEL_DIR = THUNDERBIRD_DIR / "intel"
INTEL_DIR.mkdir(parents=True, exist_ok=True)

GMAIL_TOKEN = THUNDERBIRD_DIR / "creds" / "gmail_token.json"
if not GMAIL_TOKEN.exists():
    GMAIL_TOKEN = THUNDERBIRD_DIR / "gmail_token.json"

SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.send"]
OPS_EMAIL = "d2mconcierge@gmail.com"
COMMANDER_EMAIL = "johnloucks3@gmail.com"

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
DEDUP_FILE = INTEL_DIR / "agentic_intel_dedup.json"

USER_AGENT = "Thunderbird-Agentic-Intel/1.0 (D2M Travel Intelligence)"
MDT = timezone(timedelta(hours=-6))

# ============================================================================
# Keywords — what we're hunting
# ============================================================================

# Primary targets — these ARE our setup
PRIMARY_KEYWORDS = [
    "claude code", "claude cli", "claude agent sdk", "claude hooks",
    "goose ai", "goose cli", "goose codegen", "block/goose",
    "multi-model", "multi-agent orchestration", "agent-to-agent",
    "a2a protocol", "inter-agent", "model routing",
    "ai staff", "ai team", "ai personas", "ai org chart",
    "agentic coding", "agentic workflow", "agentic ide",
    "coding agent", "code agent", "autonomous coding",
    "osint", "open source intelligence", "ai osint", "agentic osint",
    # Crown Jewel — mobile/phone-native operation
    "claude mobile", "claude phone", "claude ios", "claude android",
    "mobile agent", "phone agent", "on-device agent",
    "mobile mcp", "phone mcp",
    "claude app agent", "voice controlled claude",
    # C2 — phone as command surface
    "phone c2", "mobile command and control",
    "phone approval ai", "remote approval agent",
    "push notification agent", "ntfy agent",
    "mobile agent dashboard", "agent pwa",
    "phone dispatch ai", "agent orchestration mobile",
]

# Secondary — competitors and adjacent tech
SECONDARY_KEYWORDS = [
    "cursor agent", "windsurf", "copilot agent", "devin", "codex cli",
    "cline", "aider", "continue.dev", "tabby", "qodo",
    "crewai", "autogen", "langgraph", "mastra", "openai agents",
    "anthropic mcp", "model context protocol",
    "n8n ai", "langchain agent", "llamaindex agent",
    "openrouter", "litellm", "ollama multi",
    "ai coding assistant", "ai pair programming",
    "headless ai", "ai dispatch", "ai c2",
    "swarm intelligence", "agent framework",
    "claude max", "claude opus", "claude sonnet",
    "goose desktop", "goose recipe", "goose extension",
    # Crown Jewel — secondary
    "mobile llm runtime", "on-device llm agent",
    "phone based agent", "smartphone automation",
    "wake word agent", "hands free coding",
    "mobile tool use", "phone browser automation",
    "ios agent app", "android agent app",
    "claude touch interface",
]

# Breakthrough signals — eclipses our setup
BREAKTHROUGH_SIGNALS = [
    "breakthrough", "game changer", "just released", "announced today",
    "open source", "self-hosted", "free tier", "unlimited",
    "replaces", "kills", "obsoletes", "better than",
    "production ready", "enterprise", "multi-tenant",
]

ALL_KEYWORDS = PRIMARY_KEYWORDS + SECONDARY_KEYWORDS + BREAKTHROUGH_SIGNALS


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class Finding:
    title: str
    source: str
    url: str
    summary: str
    keywords_matched: list[str]
    score: int = 0
    tier: str = "WATCH"  # CRITICAL / HIGH / WATCH
    discovered: str = field(default_factory=lambda: datetime.now(MDT).isoformat())

    @property
    def is_primary(self) -> bool:
        return any(k in self.keywords_matched for k in PRIMARY_KEYWORDS)


# ============================================================================
# Dedup
# ============================================================================

def _load_dedup() -> set:
    if DEDUP_FILE.exists():
        try:
            data = json.loads(DEDUP_FILE.read_text())
            cutoff = (datetime.now(MDT) - timedelta(days=7)).isoformat()
            return {u for u, ts in data.items() if ts > cutoff}
        except Exception:
            pass
    return set()


def _save_dedup(seen: set):
    now = datetime.now(MDT).isoformat()
    data = {u: now for u in seen}
    DEDUP_FILE.write_text(json.dumps(data, indent=2))


# ============================================================================
# Reddit Scanner
# ============================================================================

REDDIT_SUBS = {
    "r/ClaudeAI": 25,
    "r/anthropic": 25,
    "r/LocalLLaMA": 20,
    "r/MCP": 20,
    "r/Cursor": 20,
    "r/ChatGPT": 15,
    "r/MachineLearning": 15,
    "r/artificial": 15,
    "r/singularity": 15,
    "r/selfhosted": 10,
    "r/n8n": 10,
    "r/coding": 10,
    "r/devops": 10,
    "r/OpenAI": 15,
    "r/ArtificialIntelligence": 10,
}


def scan_reddit(seen: set) -> list[Finding]:
    findings = []
    for sub, limit in REDDIT_SUBS.items():
        url = f"https://www.reddit.com/{sub}/hot.json?limit={limit}"
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
            if resp.status_code == 429:
                time.sleep(3)
                continue
            resp.raise_for_status()

            for post in resp.json().get("data", {}).get("children", []):
                pd = post.get("data", {})
                title = pd.get("title", "")
                selftext = pd.get("selftext", "")[:500]
                score = pd.get("score", 0)
                link = f"https://reddit.com{pd.get('permalink', '')}"

                if link in seen or score < 3:
                    continue

                full_text = f"{title} {selftext}".lower()
                matched = [kw for kw in ALL_KEYWORDS if kw in full_text]

                if matched:
                    tier = "CRITICAL" if any(k in matched for k in PRIMARY_KEYWORDS) and score > 50 else \
                           "HIGH" if any(k in matched for k in PRIMARY_KEYWORDS) else "WATCH"
                    findings.append(Finding(
                        title=title[:200],
                        source=f"reddit/{sub}",
                        url=link,
                        summary=selftext[:300] if selftext else title,
                        keywords_matched=matched[:10],
                        score=score,
                        tier=tier,
                    ))
                    seen.add(link)

            time.sleep(1)
        except Exception as e:
            logger.warning(f"Reddit {sub}: {e}")

    logger.info(f"Reddit: {len(findings)} findings")
    return findings


# ============================================================================
# Hacker News Scanner
# ============================================================================

def scan_hackernews(seen: set) -> list[Finding]:
    findings = []
    for endpoint in ["topstories", "newstories", "beststories"]:
        try:
            ids = requests.get(
                f"https://hacker-news.firebaseio.com/v0/{endpoint}.json",
                timeout=10
            ).json()[:100]

            for item_id in ids:
                try:
                    item = requests.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                        timeout=5
                    ).json()
                    if not item:
                        continue

                    title = item.get("title", "")
                    url = item.get("url", f"https://news.ycombinator.com/item?id={item_id}")
                    score = item.get("score", 0)

                    if url in seen or score < 5:
                        continue

                    matched = [kw for kw in ALL_KEYWORDS if kw in title.lower()]
                    if matched:
                        tier = "CRITICAL" if any(k in matched for k in PRIMARY_KEYWORDS) and score > 100 else \
                               "HIGH" if any(k in matched for k in PRIMARY_KEYWORDS) else "WATCH"
                        findings.append(Finding(
                            title=title[:200],
                            source=f"hn/{endpoint}",
                            url=url,
                            summary=f"HN score: {score}, comments: {item.get('descendants', 0)}",
                            keywords_matched=matched[:10],
                            score=score,
                            tier=tier,
                        ))
                        seen.add(url)
                except Exception:
                    continue

            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"HN {endpoint}: {e}")

    logger.info(f"HN: {len(findings)} findings")
    return findings


# ============================================================================
# GitHub Scanner
# ============================================================================

GITHUB_QUERIES = [
    "claude+code+agent",
    "goose+ai+coding",
    "multi-model+orchestration",
    "agentic+coding",
    "agent-to-agent+protocol",
    "mcp+server",
    "ai+staff+persona",
    "coding+agent+cli",
    "autonomous+coding+assistant",
    "inter-agent+communication",
    # Crown Jewel
    "claude+mobile",
    "mobile+mcp+client",
    "phone+agent+runtime",
    "on-device+llm+agent",
    # C2
    "phone+c2+ai",
    "claude+code+phone+approval",
    "ntfy+ai+agent",
]


def scan_github(seen: set) -> list[Finding]:
    findings = []
    for query in GITHUB_QUERIES:
        try:
            resp = requests.get(
                f"https://api.github.com/search/repositories?q={query}&sort=updated&per_page=10",
                headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"},
                timeout=15,
            )
            if resp.status_code == 403:
                time.sleep(10)
                continue
            resp.raise_for_status()

            for repo in resp.json().get("items", []):
                url = repo.get("html_url", "")
                if url in seen:
                    continue

                name = repo.get("full_name", "")
                desc = repo.get("description", "") or ""
                stars = repo.get("stargazers_count", 0)
                updated = repo.get("updated_at", "")

                full_text = f"{name} {desc}".lower()
                matched = [kw for kw in ALL_KEYWORDS if kw in full_text]

                if matched and stars >= 5:
                    # Check if recently updated (within 7 days)
                    try:
                        updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        if datetime.now(timezone.utc) - updated_dt > timedelta(days=7):
                            continue
                    except Exception:
                        pass

                    tier = "CRITICAL" if stars > 500 and any(k in matched for k in PRIMARY_KEYWORDS) else \
                           "HIGH" if any(k in matched for k in PRIMARY_KEYWORDS) else "WATCH"
                    findings.append(Finding(
                        title=f"{name} ({stars} stars)",
                        source="github",
                        url=url,
                        summary=desc[:300],
                        keywords_matched=matched[:10],
                        score=stars,
                        tier=tier,
                    ))
                    seen.add(url)

            time.sleep(2)
        except Exception as e:
            logger.warning(f"GitHub {query}: {e}")

    logger.info(f"GitHub: {len(findings)} findings")
    return findings


# ============================================================================
# Serper Web Search (if API key available)
# ============================================================================

SERPER_QUERIES = [
    "claude code new features 2026",
    "goose AI coding assistant update",
    "multi-model agent orchestration",
    "agentic coding tools comparison",
    "AI agent-to-agent communication protocol",
    "autonomous coding agent production",
    "claude code vs cursor vs windsurf",
    "goose alternatives AI coding",
    "MCP model context protocol news",
    "AI staff system multi-persona",
    # Crown Jewel
    "claude mobile app agent 2026",
    "on-device AI agent smartphone",
    "mobile MCP client phone",
    "phone based coding agent",
    "voice controlled AI agent phone",
    # C2
    "phone as command center AI agent",
    "approve AI tools from phone",
    "ntfy agent approval workflow",
    "remote AI agent C2 phone",
]


def scan_serper(seen: set) -> list[Finding]:
    if not SERPER_API_KEY:
        logger.info("Serper: no API key, skipping")
        return []

    findings = []
    for query in SERPER_QUERIES:
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 10, "tbs": "qdr:d"},  # last 24 hours
                timeout=15,
            )
            resp.raise_for_status()

            for result in resp.json().get("organic", []):
                url = result.get("link", "")
                if url in seen:
                    continue

                title = result.get("title", "")
                snippet = result.get("snippet", "")

                full_text = f"{title} {snippet}".lower()
                matched = [kw for kw in ALL_KEYWORDS if kw in full_text]

                if matched or any(q_word in full_text for q_word in query.lower().split()):
                    findings.append(Finding(
                        title=title[:200],
                        source=f"serper/{query[:30]}",
                        url=url,
                        summary=snippet[:300],
                        keywords_matched=matched[:10] if matched else [query],
                        score=10 - resp.json().get("organic", []).index(result),
                        tier="HIGH" if any(k in (matched or []) for k in PRIMARY_KEYWORDS) else "WATCH",
                    ))
                    seen.add(url)

            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Serper '{query[:30]}': {e}")

    logger.info(f"Serper: {len(findings)} findings")
    return findings


# ============================================================================
# RSS Blog Scanner
# ============================================================================

RSS_FEEDS = [
    ("Anthropic Blog", "https://www.anthropic.com/blog/rss"),
    ("Simon Willison", "https://simonwillison.net/atom/everything/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("AI News (Ars)", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
    ("Hacker News RSS", "https://hnrss.org/newest?q=claude+OR+goose+OR+agentic+OR+multi-model&points=20"),
]


def scan_rss(seen: set) -> list[Finding]:
    if not feedparser:
        logger.info("RSS: feedparser not installed, skipping")
        return []

    findings = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=36)

    for feed_name, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                url = entry.get("link", "")
                if url in seen:
                    continue

                title = entry.get("title", "")
                summary = entry.get("summary", "")[:500]

                full_text = f"{title} {summary}".lower()
                matched = [kw for kw in ALL_KEYWORDS if kw in full_text]

                if matched:
                    findings.append(Finding(
                        title=title[:200],
                        source=f"rss/{feed_name}",
                        url=url,
                        summary=summary[:300],
                        keywords_matched=matched[:10],
                        score=len(matched) * 5,
                        tier="HIGH" if any(k in matched for k in PRIMARY_KEYWORDS) else "WATCH",
                    ))
                    seen.add(url)
        except Exception as e:
            logger.warning(f"RSS {feed_name}: {e}")

    logger.info(f"RSS: {len(findings)} findings")
    return findings


# ============================================================================
# Email — Hale voice, D2M stationery
# ============================================================================

def _get_gmail_service():
    creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN), SCOPES_GMAIL)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GMAIL_TOKEN.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _render_html(findings: list[Finding], scan_time: str) -> str:
    critical = [f for f in findings if f.tier == "CRITICAL"]
    high = [f for f in findings if f.tier == "HIGH"]
    watch = [f for f in findings if f.tier == "WATCH"]

    def _rows(items):
        rows = ""
        for f in sorted(items, key=lambda x: x.score, reverse=True)[:25]:
            kw_tags = ", ".join(f.keywords_matched[:5])
            rows += f"""<tr>
                <td style="padding:6px 8px;"><a href="{f.url}" style="color:#0000ff;">{f.title[:80]}</a></td>
                <td style="padding:6px 8px;">{f.source}</td>
                <td style="padding:6px 8px; text-align:center;">{f.score}</td>
                <td style="padding:6px 8px; font-size:12px;">{kw_tags}</td>
            </tr>"""
        return rows

    html = f"""<html><body style="font-family:Georgia,serif; background:#f7f3ea; color:#333; padding:20px; max-width:900px; margin:0 auto;">
    <div style="background:#1a237e; color:white; padding:16px 24px; border-radius:4px 4px 0 0;">
        <h1 style="margin:0; font-size:20px;">NIGHTLY AGENTIC INTEL SWEEP</h1>
        <p style="margin:4px 0 0 0; font-size:13px; opacity:0.9;">{scan_time} MDT | Hale, COS | Sources: Reddit, HN, GitHub, Serper, RSS</p>
    </div>
    <div style="background:white; padding:24px; border:1px solid #ddd; border-top:none;">
        <p style="margin-top:0;"><strong>Commander,</strong></p>
        <p>Nightly sweep complete. <strong>{len(findings)} findings</strong> across {len(set(f.source.split('/')[0] for f in findings))} source types.
        {len(critical)} critical, {len(high)} high priority, {len(watch)} watch items.</p>
    """

    if critical:
        html += f"""<h2 style="color:#cc0000; border-bottom:2px solid #cc0000; padding-bottom:4px;">CRITICAL — Mirrors or Eclipses Our Setup ({len(critical)})</h2>
        <table style="width:100%; border-collapse:collapse; margin:12px 0;">
        <tr style="background:#1a237e; color:white;"><th style="padding:8px; text-align:left;">Finding</th><th style="padding:8px;">Source</th><th style="padding:8px;">Score</th><th style="padding:8px;">Keywords</th></tr>
        {_rows(critical)}</table>"""

    if high:
        html += f"""<h2 style="color:#0000ff; border-bottom:2px solid #0000ff; padding-bottom:4px;">HIGH PRIORITY ({len(high)})</h2>
        <table style="width:100%; border-collapse:collapse; margin:12px 0;">
        <tr style="background:#1a237e; color:white;"><th style="padding:8px; text-align:left;">Finding</th><th style="padding:8px;">Source</th><th style="padding:8px;">Score</th><th style="padding:8px;">Keywords</th></tr>
        {_rows(high)}</table>"""

    if watch:
        html += f"""<h2 style="color:#666; border-bottom:1px solid #ccc; padding-bottom:4px;">WATCH ({len(watch)})</h2>
        <table style="width:100%; border-collapse:collapse; margin:12px 0;">
        <tr style="background:#eee;"><th style="padding:8px; text-align:left;">Finding</th><th style="padding:8px;">Source</th><th style="padding:8px;">Score</th><th style="padding:8px;">Keywords</th></tr>
        {_rows(watch)}</table>"""

    html += """<p style="margin-top:24px; color:#666; font-size:13px;">Thanks<br><br>
        — Hale, COS | Thunderbird Wing | Nightly Agentic Intel Sweep</p>
    </div></body></html>"""

    return html


def send_intel_email(findings: list[Finding], scan_time: str):
    html = _render_html(findings, scan_time)

    service = _get_gmail_service()
    msg = MIMEMultipart("alternative")
    msg["To"] = COMMANDER_EMAIL
    msg["From"] = OPS_EMAIL
    msg["Subject"] = f"Agentic Intel Sweep — {scan_time} | {len(findings)} findings"

    plain = f"Nightly agentic intel sweep: {len(findings)} findings. View in HTML email client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"Email sent to {COMMANDER_EMAIL}: {len(findings)} findings")


# ============================================================================
# Main
# ============================================================================

def run_sweep() -> list[Finding]:
    """Run the full nightly agentic intel sweep."""
    scan_time = datetime.now(MDT).strftime("%Y-%m-%d %H:%M")
    logger.info(f"=== Agentic Intel Sweep starting at {scan_time} ===")

    seen = _load_dedup()
    all_findings = []

    # Scan all sources
    all_findings.extend(scan_reddit(seen))
    all_findings.extend(scan_hackernews(seen))
    all_findings.extend(scan_github(seen))
    all_findings.extend(scan_serper(seen))
    all_findings.extend(scan_rss(seen))

    # Sort: CRITICAL first, then by score
    tier_order = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2}
    all_findings.sort(key=lambda f: (tier_order.get(f.tier, 3), -f.score))

    # Save dedup
    _save_dedup(seen)

    # Save markdown
    md_path = INTEL_DIR / "nightly_agentic_intel.md"
    md = f"# Agentic Intel Sweep — {scan_time}\n\n"
    md += f"**{len(all_findings)} findings** | Sources: Reddit, HN, GitHub, Serper, RSS\n\n"
    for f in all_findings:
        md += f"## [{f.tier}] {f.title}\n"
        md += f"- Source: {f.source} | Score: {f.score}\n"
        md += f"- URL: {f.url}\n"
        md += f"- Keywords: {', '.join(f.keywords_matched[:5])}\n"
        md += f"- {f.summary}\n\n"
    md_path.write_text(md)
    logger.info(f"Markdown saved to {md_path}")

    # Save JSON
    json_path = INTEL_DIR / "nightly_agentic_intel.json"
    json_path.write_text(json.dumps([asdict(f) for f in all_findings], indent=2))

    # Email to Commander
    if all_findings:
        try:
            send_intel_email(all_findings, scan_time)
        except Exception as e:
            logger.error(f"Email failed: {e}")
    else:
        logger.info("No findings — skipping email")

    logger.info(f"=== Sweep complete: {len(all_findings)} findings ===")
    return all_findings


if __name__ == "__main__":
    run_sweep()
