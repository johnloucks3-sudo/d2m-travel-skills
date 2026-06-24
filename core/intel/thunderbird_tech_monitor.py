"""
Thunderbird OS Phase 4: Technology Enhancement Monitor
=======================================================

Daily monitoring of relevant technology developments for Dreams2Memories:
- AI/LLM advancements (Claude, GPT, Gemini, Groq, Llama)
- MCP/Agent frameworks (Goose, LangChain, AutoGPT)
- Web scraping tools (Playwright, Puppeteer, anti-detection)
- Travel technology APIs
- Document generation libraries
- Vector databases and RAG systems

Output: Daily email digest of relevant tech news
"""

import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re

import requests
from bs4 import BeautifulSoup
import feedparser
from pydantic import BaseModel, Field
import gspread
from google.oauth2 import service_account
from jinja2 import Template

# ============================================================================
# CONFIGURATION
# ============================================================================

class TechMonitorConfig:
    """Configuration for technology monitoring"""
    
    # Google Sheets
    SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    SERVICE_ACCOUNT_FILE = Path.home() / "Thunderbird" / "credentials.json"
    TECH_NEWS_TAB = "Tech News Monitor"
    
    # Email (for daily digest)
    RECIPIENT_EMAIL = "johnloucks3@gmail.com"
    
    # Technology Categories to Monitor
    TECH_CATEGORIES = {
        "AI_MODELS": {
            "keywords": [
                "Claude", "Anthropic", "Sonnet", "Opus", "Haiku",
                "GPT-4", "GPT-5", "OpenAI", "ChatGPT",
                "Gemini", "Google AI", "Bard",
                "Llama", "Meta AI",
                "Groq", "Mistral", "Qwen"
            ],
            "priority": "CRITICAL",
            "sources": [
                "https://www.anthropic.com/news",
                "https://openai.com/blog/rss",
                "https://blog.google/technology/ai/rss/"
            ]
        },

        "CLAUDE_CODE_INTEL": {
            "keywords": [
                "Claude Code", "claude code", "CLAUDE.md",
                "claude cli", "Claude CLI",
                "Cowork", "cowork scheduled tasks",
                "claude hooks", "claude skills",
                "slash commands", "claude agent",
                "claude mcp", "claude desktop",
                "CCManager", "awesome-claude-code",
                "claude code best practices",
                "agent teams", "subagent",
                "claude fast mode", "claude teleport",
                "anthropic sdk", "claude api"
            ],
            "priority": "CRITICAL",
            "sources": [
                "https://www.anthropic.com/news",
                "https://code.claude.com/docs/en/scheduled-tasks",
                "https://github.com/anthropics/claude-code/releases.atom",
                "https://github.com/wesammustafa/Claude-Code-Everything-You-Need-to-Know",
                "https://github.com/rohitg00/awesome-claude-code-toolkit",
                "https://github.com/kbwo/ccmanager",
                "https://github.com/hesreallyhim/awesome-claude-code",
                "https://github.com/jqueryscript/awesome-claude-code",
                "https://github.com/trailofbits/claude-code-config",
                "https://blog.sshh.io/p/how-i-use-every-claude-code-feature",
                "https://www.humanlayer.dev/blog/writing-a-good-claude-md",
                "https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-cowork",
                "https://support.claude.com/en/articles/13345190-get-started-with-cowork",
            ]
        },

        "MCP_AGENTS": {
            "keywords": [
                "MCP", "Model Context Protocol",
                "Goose", "Goose AI",
                "LangChain", "LangGraph", "LangSmith",
                "AutoGPT", "BabyAGI", "AgentGPT",
                "Crew AI", "AutoGen",
                "FastMCP", "MCP server",
                "Agentic AI Foundation",
                "MCP registry", "MCP OAuth"
            ],
            "priority": "HIGH",
            "sources": [
                "https://www.langchain.com/blog",
                "https://github.com/modelcontextprotocol/servers/releases.atom",
                "https://registry.modelcontextprotocol.io/"
            ]
        },

        "WEB_SCRAPING": {
            "keywords": [
                "Playwright", "Puppeteer", "Selenium",
                "playwright-stealth", "undetected-chromedriver",
                "Scrapy", "BeautifulSoup", "web scraping",
                "anti-bot", "cloudflare bypass",
                "browser automation", "headless browser"
            ],
            "priority": "HIGH",
            "sources": [
                "https://playwright.dev/blog.xml",
                "https://github.com/microsoft/playwright/releases.atom"
            ]
        },

        "TRAVEL_TECH": {
            "keywords": [
                "cruise API", "travel API", "booking.com API",
                "Amadeus API", "Sabre API", "Travelport",
                "cruise line technology", "GDS", "global distribution",
                "travel automation", "itinerary API",
                "Cruiseline.com", "CruiseDirect"
            ],
            "priority": "MEDIUM",
            "sources": [
                "https://developers.amadeus.com/blog",
                "https://www.phocuswire.com/rss"
            ]
        },

        "DOCUMENT_GEN": {
            "keywords": [
                "WeasyPrint", "python-docx", "reportlab",
                "PDF generation", "DOCX generation",
                "Jinja2", "templating engine",
                "HTML to PDF", "document automation",
                "python-pptx", "openpyxl"
            ],
            "priority": "LOW",
            "sources": [
                "https://github.com/Kozea/WeasyPrint/releases.atom",
                "https://palletsprojects.com/blog/feed.atom"
            ]
        },

        "VECTOR_DB_RAG": {
            "keywords": [
                "Pinecone", "Weaviate", "Qdrant", "Chroma",
                "vector database", "embeddings",
                "RAG", "retrieval augmented generation",
                "semantic search", "FAISS",
                "LlamaIndex", "Haystack"
            ],
            "priority": "MEDIUM",
            "sources": [
                "https://www.pinecone.io/blog/",
                "https://weaviate.io/blog/rss.xml"
            ]
        }
    }
    
    # News Aggregator Sources
    TECH_NEWS_FEEDS = {
        "Hacker News": "https://news.ycombinator.com/rss",
        "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
        "AI News": "https://www.artificialintelligence-news.com/feed/",
        "Anthropic Blog": "https://www.anthropic.com/rss.xml",
        "Claude Code Releases": "https://github.com/anthropics/claude-code/releases.atom",
        "MCP Servers Releases": "https://github.com/modelcontextprotocol/servers/releases.atom",
        "AI Disruption": "https://aidisruption.ai/feed",
        "Artificial Corner": "https://artificialcorner.com/feed",
    }

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class TechNewsArticle(BaseModel):
    """Model for technology news article"""
    
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    source: str = Field(..., description="News source")
    published_date: str = Field(..., description="Publication date")
    summary: str = Field(..., description="Article summary/excerpt")
    category: str = Field(..., description="Tech category (AI_MODELS, MCP_AGENTS, etc.)")
    relevance_score: int = Field(..., description="1-10 relevance score")
    keywords_matched: List[str] = Field(default_factory=list, description="Matched keywords")
    priority: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())

# ============================================================================
# GOOGLE SHEETS INTEGRATION
# ============================================================================

def get_sheets_client():
    """Initialize Google Sheets client"""
    creds = service_account.Credentials.from_service_account_file(
        str(TechMonitorConfig.SERVICE_ACCOUNT_FILE),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return gspread.authorize(creds)

def append_to_tech_news_sheet(article: TechNewsArticle) -> bool:
    """Append tech news article to Google Sheets"""
    try:
        gc = get_sheets_client()
        sheet = gc.open_by_key(TechMonitorConfig.SHEET_ID)
        
        # Create tab if doesn't exist
        try:
            worksheet = sheet.worksheet(TechMonitorConfig.TECH_NEWS_TAB)
        except:
            worksheet = sheet.add_worksheet(
                title=TechMonitorConfig.TECH_NEWS_TAB,
                rows=1000,
                cols=10
            )
            # Add headers
            worksheet.append_row([
                'Date', 'Title', 'Source', 'Category', 'Priority',
                'Relevance', 'Keywords', 'URL', 'Summary'
            ])
        
        # Append article
        row = [
            article.published_date,
            article.title,
            article.source,
            article.category,
            article.priority,
            article.relevance_score,
            ', '.join(article.keywords_matched),
            article.url,
            article.summary[:500]  # Truncate summary
        ]
        worksheet.append_row(row)
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to write to Sheets: {str(e)}")
        return False

# ============================================================================
# NEWS SCRAPING & ANALYSIS
# ============================================================================

def calculate_relevance_score(text: str, category: str) -> tuple[int, List[str]]:
    """
    Calculate relevance score based on keyword matches
    
    Returns:
        (score, matched_keywords)
    """
    text_lower = text.lower()
    category_config = TechMonitorConfig.TECH_CATEGORIES[category]
    keywords = category_config['keywords']
    
    matched = []
    score = 0
    
    for keyword in keywords:
        if keyword.lower() in text_lower:
            matched.append(keyword)
            # Weight by keyword specificity
            if len(keyword.split()) > 2:  # Multi-word = more specific
                score += 3
            elif len(keyword.split()) == 2:
                score += 2
            else:
                score += 1
    
    # Normalize to 1-10 scale
    score = min(10, max(1, score))
    
    return score, matched

def scrape_tech_news() -> List[TechNewsArticle]:
    """
    Scrape technology news from RSS feeds and analyze relevance
    
    Returns:
        List of TechNewsArticle objects with relevance scores
    """
    logger.info("📰 Scraping technology news feeds...")
    articles = []
    
    # Scrape general tech news feeds
    for source_name, feed_url in TechMonitorConfig.TECH_NEWS_FEEDS.items():
        try:
            logger.info(f"📡 Fetching {source_name}...")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:20]:  # Top 20 from each source
                title = entry.get('title', '')
                url = entry.get('link', '')
                published = entry.get('published', datetime.now().isoformat())
                summary = entry.get('summary', entry.get('description', ''))
                
                # Clean HTML from summary
                summary_text = BeautifulSoup(summary, 'html.parser').get_text()
                summary_text = summary_text[:500]
                
                # Check relevance against all categories
                best_category = None
                best_score = 0
                best_keywords = []
                
                full_text = f"{title} {summary_text}"
                
                for category in TechMonitorConfig.TECH_CATEGORIES.keys():
                    score, keywords = calculate_relevance_score(full_text, category)
                    if score > best_score and keywords:  # Must have keyword matches
                        best_score = score
                        best_category = category
                        best_keywords = keywords
                
                # Only include if relevant (score >= 3)
                if best_category and best_score >= 3:
                    priority = TechMonitorConfig.TECH_CATEGORIES[best_category]['priority']
                    
                    article = TechNewsArticle(
                        title=title,
                        url=url,
                        source=source_name,
                        published_date=published,
                        summary=summary_text,
                        category=best_category,
                        relevance_score=best_score,
                        keywords_matched=best_keywords,
                        priority=priority
                    )
                    articles.append(article)
                    
                    if best_score >= 7:
                        logger.info(f"🔥 HIGH RELEVANCE: {title[:60]}... (Score: {best_score})")
        
        except Exception as e:
            logger.error(f"❌ Failed to fetch {source_name}: {str(e)}")
            continue
    
    # Sort by relevance score (highest first)
    articles.sort(key=lambda x: x.relevance_score, reverse=True)
    
    logger.info(f"✅ Found {len(articles)} relevant tech articles")
    return articles

# ============================================================================
# DAILY DIGEST EMAIL GENERATION
# ============================================================================

EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #1f4788 0%, #355c9d 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 28pt;
        }
        .header .tagline {
            font-size: 14pt;
            opacity: 0.9;
            margin-top: 10px;
        }
        
        .category-section {
            margin-bottom: 40px;
        }
        
        .category-header {
            background: #f4f7f6;
            padding: 15px;
            border-left: 4px solid #1f4788;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        
        .category-header h2 {
            margin: 0;
            color: #1f4788;
            font-size: 18pt;
        }
        
        .category-header .count {
            color: #666;
            font-size: 11pt;
            margin-top: 5px;
        }
        
        .article {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 15px;
            transition: box-shadow 0.2s;
        }
        
        .article:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .article-title {
            font-size: 16pt;
            font-weight: bold;
            color: #1f4788;
            margin-bottom: 10px;
        }
        
        .article-title a {
            color: #1f4788;
            text-decoration: none;
        }
        
        .article-title a:hover {
            text-decoration: underline;
        }
        
        .article-meta {
            font-size: 10pt;
            color: #666;
            margin-bottom: 10px;
        }
        
        .article-summary {
            font-size: 11pt;
            color: #444;
            line-height: 1.5;
        }
        
        .article-footer {
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #f0f0f0;
            font-size: 10pt;
            color: #888;
        }
        
        .priority-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 9pt;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .priority-CRITICAL {
            background: #dc3545;
            color: white;
        }
        
        .priority-HIGH {
            background: #ffc107;
            color: #333;
        }
        
        .priority-MEDIUM {
            background: #17a2b8;
            color: white;
        }
        
        .priority-LOW {
            background: #6c757d;
            color: white;
        }
        
        .relevance-score {
            display: inline-block;
            font-weight: bold;
            color: #1f4788;
        }
        
        .keywords {
            display: inline-block;
            background: #e3f2fd;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 9pt;
            margin-right: 5px;
            color: #1976d2;
        }
        
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            text-align: center;
            font-size: 10pt;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Thunderbird Tech Monitor</h1>
        <div class="tagline">Daily Technology Enhancement Digest</div>
        <div class="tagline">{{ report_date }}</div>
    </div>
    
    <p style="font-size: 12pt; color: #555;">
        Today's digest contains <strong>{{ total_articles }}</strong> relevant technology articles 
        across <strong>{{ category_count }}</strong> categories.
    </p>
    
    {% for category, category_articles in articles_by_category.items() %}
    <div class="category-section">
        <div class="category-header">
            <h2>{{ category_names[category] }}</h2>
            <div class="count">{{ category_articles|length }} articles</div>
        </div>
        
        {% for article in category_articles %}
        <div class="article">
            <div class="article-title">
                <a href="{{ article.url }}" target="_blank">{{ article.title }}</a>
            </div>
            
            <div class="article-meta">
                <span class="priority-badge priority-{{ article.priority }}">{{ article.priority }}</span>
                <span class="relevance-score">Relevance: {{ article.relevance_score }}/10</span>
                | {{ article.source }} | {{ article.published_date }}
            </div>
            
            <div class="article-summary">
                {{ article.summary }}
            </div>
            
            <div class="article-footer">
                <strong>Keywords:</strong>
                {% for keyword in article.keywords_matched[:5] %}
                <span class="keywords">{{ keyword }}</span>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% endfor %}
    
    <div class="footer">
        <strong>Thunderbird OS Phase 4: Technology Enhancement Monitor</strong><br>
        Dreams2Memories Travel | {{ company_email }}<br>
        <p style="margin-top: 15px; font-size: 9pt;">
            This digest is generated daily to track technology developments relevant to 
            your luxury travel intelligence platform. Articles are automatically scored 
            by relevance and categorized by technology type.
        </p>
    </div>
</body>
</html>
"""

def generate_daily_digest_html(articles: List[TechNewsArticle]) -> str:
    """Generate HTML email digest from tech news articles"""
    
    # Group articles by category
    articles_by_category = {}
    for article in articles:
        if article.category not in articles_by_category:
            articles_by_category[article.category] = []
        articles_by_category[article.category].append(article)
    
    # Sort each category by relevance
    for category in articles_by_category:
        articles_by_category[category].sort(key=lambda x: x.relevance_score, reverse=True)
    
    # Category display names
    category_names = {
        "AI_MODELS": "🤖 AI Models & LLMs",
        "CLAUDE_CODE_INTEL": "⚡ Claude Code & Tooling Intel",
        "MCP_AGENTS": "🔗 MCP & Agent Frameworks",
        "WEB_SCRAPING": "🕷️ Web Scraping & Automation",
        "TRAVEL_TECH": "✈️ Travel Technology & APIs",
        "DOCUMENT_GEN": "📄 Document Generation",
        "VECTOR_DB_RAG": "🧠 Vector Databases & RAG"
    }
    
    # Render template
    template = Template(EMAIL_TEMPLATE)
    html = template.render(
        report_date=datetime.now().strftime("%B %d, %Y"),
        total_articles=len(articles),
        category_count=len(articles_by_category),
        articles_by_category=articles_by_category,
        category_names=category_names,
        company_email="d2mconcierge@gmail.com"
    )
    
    return html

def save_digest_to_file(html: str, output_dir: Path) -> Path:
    """Save HTML digest to file"""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"Tech_Digest_{datetime.now().strftime('%Y%m%d')}.html"
    output_path = output_dir / filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"✅ Digest saved: {output_path}")
    return output_path

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def run_daily_tech_monitor() -> Dict[str, Any]:
    """
    Run daily technology monitoring sweep
    
    Returns:
        Summary of articles found and processed
    """
    logger.info("="*70)
    logger.info("🚀 THUNDERBIRD TECH MONITOR - DAILY SWEEP")
    logger.info("="*70 + "\n")
    
    # Scrape tech news
    articles = scrape_tech_news()
    
    # Filter for today (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    recent_articles = [
        a for a in articles
        if a.scraped_at >= yesterday.isoformat()
    ]
    
    # Write to Google Sheets
    for article in recent_articles[:50]:  # Top 50 articles
        append_to_tech_news_sheet(article)
    
    # Generate HTML digest
    html_digest = generate_daily_digest_html(recent_articles[:30])  # Top 30 for email
    
    # Save to file
    output_dir = Path.home() / "Documents" / "Luxury_Itineraries" / "Tech_Digests"
    digest_path = save_digest_to_file(html_digest, output_dir)
    
    # Generate summary
    summary = {
        "status": "complete",
        "timestamp": datetime.now().isoformat(),
        "total_articles_found": len(articles),
        "recent_articles": len(recent_articles),
        "top_categories": {},
        "digest_file": str(digest_path),
        "next_run": "Tomorrow at same time"
    }
    
    # Count articles by category
    for article in recent_articles:
        cat = article.category
        if cat not in summary["top_categories"]:
            summary["top_categories"][cat] = 0
        summary["top_categories"][cat] += 1
    
    logger.info("\n" + "="*70)
    logger.info(f"✅ SWEEP COMPLETE: {len(recent_articles)} relevant articles")
    logger.info(f"📧 Digest generated: {digest_path}")
    logger.info("="*70)

    # Send to Commander inbox — SO 27 MAR 2026: intel reports are full sends, not drafts
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from core.email.thunderbird_gmail import gmail_send_from_wing
        ts_label = datetime.now().strftime("%Y-%m-%d")
        cat_summary = ", ".join(f"{k}: {v}" for k, v in list(summary["top_categories"].items())[:5])
        gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=f"Tech Monitor Digest — {ts_label} ({len(recent_articles)} articles)",
            body=html_digest,
            persona_id="A12",
        )
        summary["email_status"] = "sent"
        logger.info("Tech monitor digest sent to johnloucks3 inbox.")
    except Exception as _e:
        summary["email_status"] = f"failed: {_e}"
        logger.warning(f"Tech monitor email failed: {_e}")

    return summary

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Thunderbird Tech Monitor - Daily Technology News"
    )
    
    parser.add_argument(
        '--run',
        action='store_true',
        help='Run daily tech monitoring sweep'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=str(Path.home() / "Documents" / "Luxury_Itineraries" / "Tech_Digests"),
        help='Output directory for HTML digests'
    )
    
    args = parser.parse_args()
    
    if args.run or len(sys.argv) == 1:
        result = asyncio.run(run_daily_tech_monitor())
        print("\n📊 SUMMARY:")
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()

# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_tech_monitor_tools(mcp):
    """Register tech monitor tools with the MCP server."""
    from pydantic import Field as PydField

    @mcp.tool(
        name="run_tech_monitor",
        annotations={"title": "Run Daily Tech Monitor Sweep", "readOnlyHint": False},
    )
    async def run_tech_monitor() -> str:
        """Run a full technology monitoring sweep across RSS feeds. Scrapes AI/LLM, MCP, web scraping, travel tech, and document generation news. Writes results to Google Sheets and generates an HTML digest."""
        try:
            result = await run_daily_tech_monitor()
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "tech_monitor_error"})

    @mcp.tool(
        name="get_tech_news",
        annotations={"title": "Get Tech News by Category", "readOnlyHint": True},
    )
    async def get_tech_news(
        category: str = PydField("all", description="Category: 'AI_MODELS', 'CLAUDE_CODE_INTEL', 'MCP_AGENTS', 'WEB_SCRAPING', 'TRAVEL_TECH', 'DOCUMENT_GEN', 'VECTOR_DB_RAG', or 'all'"),
        min_relevance: int = PydField(3, description="Minimum relevance score (1-10)"),
    ) -> str:
        """Scrape tech news feeds and return articles filtered by category and relevance."""
        try:
            articles = scrape_tech_news()
            if category != "all":
                articles = [a for a in articles if a.category == category]
            articles = [a for a in articles if a.relevance_score >= min_relevance]
            return json.dumps(
                {"status": "success", "count": len(articles), "articles": [a.model_dump() for a in articles[:20]]},
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": str(e), "type": "tech_news_error"})

    logger.info("Tech Monitor tools registered successfully")


if __name__ == "__main__":
    import sys
    main()
