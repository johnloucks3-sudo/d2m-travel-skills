"""
Thunderbird Academic & Frontier Tech Scanner
=============================================
ELON's outward-facing research radar. Scans academic papers,
frontier AI research, and technical disruption signals daily.

Sources:
  - ArXiv (cs.AI, cs.LG, cs.IR, cs.CL, cs.MA — daily new papers)
  - Hugging Face Daily Papers
  - Papers With Code (trending)
  - Semantic Scholar (recent high-impact)
  - Conference proceedings alerts (NeurIPS, ICLR, ACL, EMNLP)

Output:
  - Morning briefing ELON section (HTML)
  - Telegram digest on demand
  - intel/academic_scan_YYYYMMDD.md for archiving
  - Wing memory storage for significant finds

ELON's filter: "Would this give D2M a 6-month head start on anyone else?"
If yes → surface it. If no → skip it.

Usage:
    python3 thunderbird_academic_scanner.py          # Run scan, print digest
    python3 thunderbird_academic_scanner.py --save   # Run + save to intel/
    from thunderbird_academic_scanner import get_academic_digest_for_briefing
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote_plus
from urllib.error import URLError
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(os.path.expanduser("~/Thunderbird"))
INTEL_DIR = THUNDERBIRD_DIR / "intel"
CACHE_FILE = THUNDERBIRD_DIR / "logs" / "academic_scan_cache.json"

# ---------------------------------------------------------------------------
# D2M Relevance Filter — topics that matter to us
# ---------------------------------------------------------------------------

# High relevance: direct application to Thunderbird or travel
HIGH_RELEVANCE_TERMS = [
    "agent memory", "long-term memory", "episodic memory", "retrieval augmented",
    "multi-agent", "tool use", "function calling", "model context protocol",
    "voice agent", "speech synthesis", "text to speech", "conversational ai",
    "personalization", "user modeling", "preference learning",
    "travel", "recommendation system", "knowledge graph",
    "agentic", "autonomous agent", "llm agent", "language agent",
    "planning", "task decomposition", "workflow automation",
    "semantic search", "vector database", "embedding",
    "fine-tuning", "instruction following", "alignment",
]

# Medium relevance: could apply with some translation
MEDIUM_RELEVANCE_TERMS = [
    "transformer", "attention mechanism", "context window",
    "compression", "summarization", "information extraction",
    "dialogue", "conversation", "chatbot",
    "document understanding", "pdf", "information retrieval",
    "reinforcement learning from human feedback", "rlhf",
    "constitutional ai", "safety", "hallucination",
    "efficiency", "latency", "inference",
    "multimodal", "vision language",
]

# Skip these — not relevant to D2M
SKIP_TERMS = [
    "medical imaging", "drug discovery", "protein folding",
    "climate model", "seismic", "astronomical",
    "robotics hardware", "autonomous driving",
    "code generation", "programming language",
    "game playing", "chess", "atari",
]


def _score_relevance(title: str, abstract: str) -> tuple[int, str]:
    """Score a paper's relevance to D2M. Returns (score, reason)."""
    text = (title + " " + abstract).lower()

    # Skip check first
    for term in SKIP_TERMS:
        if term in text:
            return 0, f"skip:{term}"

    score = 0
    reasons = []

    for term in HIGH_RELEVANCE_TERMS:
        if term in text:
            score += 3
            reasons.append(term)

    for term in MEDIUM_RELEVANCE_TERMS:
        if term in text:
            score += 1
            reasons.append(term)

    return score, ", ".join(reasons[:5])


# ---------------------------------------------------------------------------
# ArXiv Scanner
# ---------------------------------------------------------------------------

ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.IR", "cs.CL", "cs.MA"]
ARXIV_API = "http://export.arxiv.org/api/query"


def _fetch_arxiv_papers(max_results: int = 50) -> List[Dict]:
    """Fetch recent papers from ArXiv across D2M-relevant categories."""
    papers = []

    # Search recent papers across categories
    query_parts = [f"cat:{cat}" for cat in ARXIV_CATEGORIES]
    query = " OR ".join(query_parts)

    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }

    url = f"{ARXIV_API}?{urlencode(params)}"

    try:
        req = Request(url, headers={"User-Agent": "Thunderbird/2.0 D2M Academic Scanner"})
        with urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8")

        root = ET.fromstring(content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el = entry.find("atom:id", ns)
            published_el = entry.find("atom:published", ns)

            if title_el is None or summary_el is None:
                continue

            title = title_el.text.strip().replace("\n", " ")
            abstract = summary_el.text.strip().replace("\n", " ")[:500]
            arxiv_id = id_el.text.strip() if id_el is not None else ""
            published = published_el.text.strip()[:10] if published_el is not None else ""

            # Authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name_el = author.find("atom:name", ns)
                if name_el is not None:
                    authors.append(name_el.text.strip())

            score, reason = _score_relevance(title, abstract)
            if score < 3:
                continue

            papers.append({
                "source": "arxiv",
                "title": title,
                "abstract": abstract,
                "url": arxiv_id,
                "authors": authors[:3],
                "published": published,
                "score": score,
                "relevance_reason": reason,
            })

    except Exception as e:
        logger.warning(f"ArXiv fetch failed: {e}")

    return sorted(papers, key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Hugging Face Daily Papers
# ---------------------------------------------------------------------------

HF_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def _fetch_hf_papers(days_back: int = 1) -> List[Dict]:
    """Fetch Hugging Face daily papers."""
    papers = []

    try:
        req = Request(HF_PAPERS_URL, headers={"User-Agent": "Thunderbird/2.0"})
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data[:30]:
            paper = item.get("paper", {})
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()[:500]
            arxiv_id = paper.get("id", "")
            url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
            published = paper.get("publishedAt", "")[:10]

            if not title:
                continue

            score, reason = _score_relevance(title, abstract)
            if score < 3:
                continue

            papers.append({
                "source": "huggingface",
                "title": title,
                "abstract": abstract,
                "url": url,
                "authors": [],
                "published": published,
                "score": score,
                "relevance_reason": reason,
            })

    except Exception as e:
        logger.warning(f"HuggingFace papers fetch failed: {e}")

    return sorted(papers, key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Papers With Code — Trending
# ---------------------------------------------------------------------------

PWC_TRENDING_URL = "https://paperswithcode.com/api/v1/papers/?ordering=-arxiv_id&items_per_page=30"


def _fetch_pwc_papers() -> List[Dict]:
    """Fetch trending papers from Papers With Code."""
    papers = []

    try:
        # NOTE: PWC API now redirects to HuggingFace HTML (merged platforms).
        # Returning empty — HuggingFace Daily Papers covers this source.
        return []
        req = Request(PWC_TRENDING_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; Thunderbird/2.0)"})
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data.get("results", []):
            title = item.get("title", "").strip()
            abstract = item.get("abstract", "").strip()[:500]
            url = item.get("url_abs", "") or item.get("url_pdf", "")
            published = item.get("published", "")[:10]
            stars = item.get("github_link_stars", 0) or 0

            if not title:
                continue

            score, reason = _score_relevance(title, abstract)
            # Boost score for papers with GitHub implementations (production-ready signal)
            if stars > 100:
                score += 2
                reason = f"github_stars:{stars}, " + reason
            if score < 3:
                continue

            papers.append({
                "source": "paperswithcode",
                "title": title,
                "abstract": abstract,
                "url": url,
                "authors": [],
                "published": published,
                "score": score,
                "relevance_reason": reason,
                "github_stars": stars,
            })

    except Exception as e:
        logger.warning(f"Papers With Code fetch failed: {e}")

    return sorted(papers, key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _dedup_papers(paper_lists: List[List[Dict]]) -> List[Dict]:
    """Merge paper lists, deduplicating by title similarity."""
    seen_titles = set()
    merged = []

    for papers in paper_lists:
        for paper in papers:
            # Normalize title for comparison
            norm = re.sub(r"[^a-z0-9]", "", paper["title"].lower())[:60]
            if norm not in seen_titles:
                seen_titles.add(norm)
                merged.append(paper)

    return sorted(merged, key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# Cache — avoid re-surfacing papers seen in last 7 days
# ---------------------------------------------------------------------------

def _load_cache() -> set:
    """Load set of already-seen paper titles."""
    if not CACHE_FILE.exists():
        return set()
    try:
        data = json.loads(CACHE_FILE.read_text())
        # Prune entries older than 7 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        fresh = {k: v for k, v in data.items() if v > cutoff}
        return set(fresh.keys())
    except Exception:
        return set()


def _save_cache(titles: List[str]):
    """Save seen titles to cache."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = {}
        if CACHE_FILE.exists():
            existing = json.loads(CACHE_FILE.read_text())
        now = datetime.now(timezone.utc).isoformat()
        for title in titles:
            norm = re.sub(r"[^a-z0-9]", "", title.lower())[:60]
            existing[norm] = now
        # Prune old
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        existing = {k: v for k, v in existing.items() if v > cutoff}
        CACHE_FILE.write_text(json.dumps(existing))
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


# ---------------------------------------------------------------------------
# ELON Commentary Generator
# ---------------------------------------------------------------------------

def _elon_take(paper: Dict) -> str:
    """Generate ELON-voice one-liner for a paper."""
    title = paper["title"].lower()
    reason = paper["relevance_reason"]
    stars = paper.get("github_stars", 0)

    if "memory" in reason and stars > 100:
        return f"Code exists. {stars} stars. We could run this on YOGA this weekend."
    elif "memory" in reason:
        return "Memory architecture. Read the abstract. If it beats Mem0, we wire it in."
    elif "agent" in reason or "agentic" in reason:
        return "Multi-agent pattern. Question is whether Wing can use this directly."
    elif "voice" in reason or "speech" in reason:
        return "Voice stack candidate. Stack against Retell and ElevenLabs."
    elif "retrieval" in reason or "rag" in title:
        return "Retrieval improvement. Could sharpen Dani's fact accuracy."
    elif "personalization" in reason:
        return "Personalization research. This is literally what the voice ledger does — but proven."
    elif "compression" in reason:
        return "Token efficiency play. If it works, reduces our API costs."
    elif stars > 500:
        return f"{stars} GitHub stars in days. The community voted. Worth 30 minutes."
    else:
        return "Flag for Commander review. Relevance score warrants a look."


# ---------------------------------------------------------------------------
# Main Scan
# ---------------------------------------------------------------------------

def run_academic_scan(max_papers: int = 5, skip_cache: bool = False) -> List[Dict]:
    """Run full academic scan across all sources.

    Returns top N papers by relevance score, filtered for novelty.
    """
    logger.info("Academic scanner: fetching from ArXiv, HuggingFace, Papers With Code...")

    arxiv = _fetch_arxiv_papers(max_results=50)
    hf = _fetch_hf_papers()
    pwc = _fetch_pwc_papers()

    all_papers = _dedup_papers([hf, arxiv, pwc])  # HF first (most curated)

    if not skip_cache:
        seen = _load_cache()
        fresh = []
        for p in all_papers:
            norm = re.sub(r"[^a-z0-9]", "", p["title"].lower())[:60]
            if norm not in seen:
                fresh.append(p)
        all_papers = fresh

    top = all_papers[:max_papers]

    # Save to cache
    _save_cache([p["title"] for p in top])

    logger.info(f"Academic scan complete: {len(top)} fresh relevant papers surfaced")
    return top


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_digest_text(papers: List[Dict], date_str: str = "") -> str:
    """Format scan results as plain text digest."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    if not papers:
        return f"ELON ACADEMIC SCAN — {date_str}\nNo new relevant papers today. Either quiet day or cache is current."

    lines = [f"ELON ACADEMIC SCAN — {date_str}", f"{len(papers)} finds worth your attention:", ""]

    for i, p in enumerate(papers, 1):
        source_badge = {"arxiv": "[ArXiv]", "huggingface": "[HF]", "paperswithcode": "[PWC]"}.get(p["source"], "[?]")
        lines.append(f"{i}. {source_badge} {p['title']}")
        lines.append(f"   {p['abstract'][:200]}...")
        lines.append(f"   Relevance: {p['relevance_reason']}")
        lines.append(f"   ELON: {_elon_take(p)}")
        if p.get("url"):
            lines.append(f"   {p['url']}")
        lines.append("")

    return "\n".join(lines)


def format_digest_html(papers: List[Dict]) -> str:
    """Format scan results as HTML for morning briefing injection."""
    if not papers:
        return ""

    today = datetime.now().strftime("%Y-%m-%d")
    html = f"""
  <div class="section">
    <div class="section-header">
      <div class="section-icon" style="background:rgba(255,200,100,0.15);">&#128301;</div>
      <div class="section-title">ELON: Frontier Research Radar — {today}</div>
    </div>
    <div style="padding:12px 16px;font-size:13px;line-height:1.7;color:#e0e6ed;">
      <div style="color:#c9a84c;font-weight:600;margin-bottom:8px;">
        {len(papers)} paper(s) worth D2M's attention today
      </div>
"""

    for p in papers:
        score_color = "#ff6666" if p["score"] >= 9 else "#e8c97a" if p["score"] >= 6 else "#7eb8ff"
        source_label = {"arxiv": "ArXiv", "huggingface": "HF Daily", "paperswithcode": "PWC"}.get(p["source"], "Research")
        stars_note = f' · {p["github_stars"]}★' if p.get("github_stars", 0) > 0 else ""

        html += f"""
      <div style="margin-bottom:16px;padding:10px 12px;background:rgba(255,255,255,0.03);border-left:3px solid {score_color};border-radius:4px;">
        <div style="font-weight:600;color:#e0e6ed;margin-bottom:4px;">
          <a href="{p.get('url','#')}" style="color:#7eb8ff;text-decoration:none;">{p['title'][:100]}</a>
          <span style="color:#5a6a85;font-size:11px;margin-left:8px;">{source_label}{stars_note} · score:{p['score']}</span>
        </div>
        <div style="color:#8a9ab5;font-size:12px;margin-bottom:6px;">{p['abstract'][:200]}...</div>
        <div style="color:#c9a84c;font-size:12px;font-style:italic;">ELON: {_elon_take(p)}</div>
        <div style="color:#5a6a85;font-size:11px;margin-top:4px;">Match: {p['relevance_reason']}</div>
      </div>
"""

    html += "    </div>\n  </div>\n"
    return html


def get_academic_digest_for_briefing(max_papers: int = 5) -> str:
    """Called by morning briefing to get HTML digest. Returns empty string on failure."""
    try:
        papers = run_academic_scan(max_papers=max_papers)
        return format_digest_html(papers)
    except Exception as e:
        logger.warning(f"Academic scanner failed for briefing: {e}")
        return ""


# ---------------------------------------------------------------------------
# Archive to intel/
# ---------------------------------------------------------------------------

def save_scan_to_intel(papers: List[Dict]) -> Optional[Path]:
    """Save scan results to intel/academic_scan_YYYYMMDD.md"""
    if not papers:
        return None

    date_str = datetime.now().strftime("%Y%m%d")
    out_path = INTEL_DIR / f"academic_scan_{date_str}.md"

    INTEL_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# ELON Academic Scan — {date_str}",
        f"## Thunderbird OS · D2M Frontier Research Radar",
        f"### {len(papers)} relevant finds",
        "",
        "---",
        "",
    ]

    for i, p in enumerate(papers, 1):
        source = p["source"].upper()
        lines += [
            f"## {i}. [{source}] {p['title']}",
            f"**Published:** {p.get('published', 'unknown')}",
            f"**URL:** {p.get('url', 'N/A')}",
            f"**Relevance Score:** {p['score']} | **Matched:** {p['relevance_reason']}",
            "",
            f"### Abstract",
            p['abstract'],
            "",
            f"### ELON Take",
            f"*{_elon_take(p)}*",
            "",
            "---",
            "",
        ]

    out_path.write_text("\n".join(lines))
    logger.info(f"Academic scan saved to {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Wing Memory — store significant finds
# ---------------------------------------------------------------------------

def store_significant_finds(papers: List[Dict], threshold: int = 9):
    """Store high-scoring papers in Wing memory for cross-session recall."""
    high_value = [p for p in papers if p["score"] >= threshold]
    if not high_value:
        return

    try:
        from travel_mcp_server import mcp
        from thunderbird_academic_scanner import _elon_take
    except ImportError:
        pass

    try:
        # Direct wing memory add
        sys_path = str(Path(os.path.expanduser("~/Thunderbird")))
        import sys
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)

        from thunderbird_shared_memory import shared_memory
        for p in high_value:
            observation = (
                f"ELON ACADEMIC FIND ({p['source']}): {p['title']} | "
                f"Score:{p['score']} | {_elon_take(p)} | URL: {p.get('url', '')}"
            )
            shared_memory.store(observation, user_id="elon_scout")
            logger.info(f"Stored in wing memory: {p['title'][:60]}")
    except Exception as e:
        logger.debug(f"Wing memory store skipped: {e}")


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_academic_scanner_tools(mcp):
    """Register academic scanner MCP tools."""

    @mcp.tool()
    async def academic_scan(
        max_papers: int = 5,
        save_to_intel: bool = False,
        skip_cache: bool = False,
    ) -> str:
        """Run ELON's frontier research radar scan.

        Scans ArXiv, HuggingFace Daily Papers, and Papers With Code for
        research relevant to D2M / Thunderbird. Returns top finds with
        ELON commentary.

        Args:
            max_papers: Maximum papers to return (default 5)
            save_to_intel: Save results to intel/academic_scan_YYYYMMDD.md
            skip_cache: Include papers seen in last 7 days
        """
        papers = run_academic_scan(max_papers=max_papers, skip_cache=skip_cache)
        if save_to_intel:
            save_scan_to_intel(papers)
        return format_digest_text(papers)

    @mcp.tool()
    async def academic_scan_save() -> str:
        """Run academic scan and save full results to intel/ directory."""
        papers = run_academic_scan(max_papers=10, skip_cache=False)
        path = save_scan_to_intel(papers)
        store_significant_finds(papers)
        digest = format_digest_text(papers)
        saved = f"\nSaved to: {path}" if path else ""
        return digest + saved

    logger.info("Academic scanner tools registered: academic_scan, academic_scan_save")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    save = "--save" in sys.argv
    skip_cache = "--fresh" in sys.argv
    max_p = 8 if save else 5

    papers = run_academic_scan(max_papers=max_p, skip_cache=skip_cache)
    print(format_digest_text(papers))

    if save:
        path = save_scan_to_intel(papers)
        store_significant_finds(papers)
        print(f"\nSaved: {path}")
