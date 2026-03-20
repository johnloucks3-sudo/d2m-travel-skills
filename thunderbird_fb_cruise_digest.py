#!/usr/bin/env python3
"""
Thunderbird Facebook Cruise Community Digest
Dreams2Memories Travel, LLC

Scrapes Facebook cruise groups, summarizes via Claude Opus, emails to Commander.
Runs daily at 0900 MT via cron.

Usage:
  python3 thunderbird_fb_cruise_digest.py              # Send digest email
  python3 thunderbird_fb_cruise_digest.py --preview     # Save HTML locally
"""

import json
import asyncio
import logging
import os
import subprocess
import sys
import base64
import argparse
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path(__file__).parent
GROUP_LIST = THUNDERBIRD_DIR / "fb_cruise_groups.txt"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
LOGO_FILE = THUNDERBIRD_DIR / "Agency_Logo_email.png"

CLAUDE_CLI = os.path.expanduser("~/.local/bin/claude")

GMAIL_TOKEN = THUNDERBIRD_DIR / "gmail_token.json"
GMAIL_OAUTH = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
# D2M ops account — authenticated sender (gmail_token.json)
OPS_EMAIL = "d2mconcierge@gmail.com"
# Commander's personal inbox — digest delivered here
COMMANDER_EMAIL = "johnloucks3@gmail.com"
SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.modify"]

FB_PROFILE = "facebook"
PROFILES_DIR = THUNDERBIRD_DIR / "browser_profiles"

logger = logging.getLogger("fb_cruise_digest")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CRUISE] %(message)s",
    stream=sys.stderr,
)


# ---------------------------------------------------------------------------
# GMAIL SERVICE
# ---------------------------------------------------------------------------

def _get_gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN), SCOPES_GMAIL)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GMAIL_TOKEN.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# FACEBOOK GROUP SCRAPER
# ---------------------------------------------------------------------------

def load_group_list():
    groups = []
    current_comment = ""
    with open(GROUP_LIST, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# ") and not line.startswith("# ==="):
                current_comment = line[2:]
            elif line.startswith("groups/"):
                groups.append({
                    "path": line,
                    "name": current_comment,
                    "url": f"https://www.facebook.com/{line}",
                })
    return groups


async def scrape_fb_group(context, group, max_posts=3):
    """Scrape recent posts from a Facebook group."""
    url = group["url"]
    name = group["name"]
    page = await context.new_page()

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

        title = await page.title()

        # Check for login wall
        page_text = await page.evaluate("document.body.innerText.substring(0, 300)")
        if "Log in" in page_text[:100] and "Facebook" in title and "Groups" not in title:
            return {
                "name": name,
                "url": url,
                "status": "error",
                "error": "Session expired — need FB re-login",
                "posts": [],
            }

        # Check for "Join Group" wall (private group, not a member)
        if "Join group" in page_text[:300] or "Join Group" in page_text[:300]:
            return {
                "name": name,
                "url": url,
                "status": "error",
                "error": "Private group — not a member yet",
                "posts": [],
            }

        # Extract posts — Facebook uses role="article" for feed posts
        posts = await page.evaluate("""
            (maxPosts) => {
                var feedPosts = document.querySelectorAll('[role="article"]');
                var results = [];
                for (var i = 0; i < Math.min(feedPosts.length, maxPosts); i++) {
                    var post = feedPosts[i];
                    var text = post.innerText || '';
                    // Clean up — get first 1500 chars
                    text = text.substring(0, 1500);

                    // Try to find links
                    var links = [];
                    var anchors = post.querySelectorAll('a[href]');
                    for (var j = 0; j < anchors.length; j++) {
                        var href = anchors[j].href;
                        var linkText = anchors[j].innerText.trim().substring(0, 120);
                        if (href.startsWith('http') &&
                            !href.includes('/groups/feed') &&
                            !href.includes('/avatar/') &&
                            linkText.length > 2 && linkText.length < 100) {
                            links.push({text: linkText, url: href});
                        }
                    }

                    if (text.length > 20) {
                        results.push({
                            text: text,
                            links: links.slice(0, 5)
                        });
                    }
                }
                return results;
            }
        """, max_posts)

        return {
            "name": name,
            "url": url,
            "status": "ok",
            "posts": posts,
        }

    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status": "error",
            "error": str(e),
            "posts": [],
        }
    finally:
        await page.close()


async def scrape_all_fb_groups():
    """Scrape all Facebook cruise groups."""
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth

    groups = load_group_list()
    logger.info(f"Scraping {len(groups)} Facebook groups...")

    results = []
    async with Stealth().use_async(async_playwright()) as p:
        profile_dir = PROFILES_DIR / FB_PROFILE
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        for group in groups:
            logger.info(f"  Scraping: {group['name']}...")
            result = await scrape_fb_group(context, group)
            results.append(result)
            await asyncio.sleep(3)  # Polite delay for Facebook

        await context.close()

    ok = sum(1 for r in results if r["status"] == "ok")
    logger.info(f"Done: {ok}/{len(results)} groups scraped successfully")
    return results


# ---------------------------------------------------------------------------
# CLAUDE OPUS SUMMARIZER (Max plan, $0)
# ---------------------------------------------------------------------------

async def summarize_cruise_feeds(group_results):
    """Summarize cruise community posts via Claude Opus (Max plan, $0)."""
    raw_text = ""
    for group in group_results:
        if group["status"] == "ok" and group["posts"]:
            raw_text += f"\n\n=== {group['name']} ===\n"
            for post in group["posts"]:
                raw_text += post.get("text", "")[:800] + "\n---\n"

    if not raw_text.strip():
        return "No cruise community posts available."

    prompt = f"""You are a luxury cruise industry analyst preparing a daily brief for a travel advisor who sells Regent, Silversea, Oceania, Viking, and boutique cruise lines.

Analyze these Facebook cruise community posts and produce a CONCISE DAILY BRIEF.

FORMAT:
1. HOT TOPICS (What are passengers buzzing about? Complaints, praise, trends — 3-5 items)
2. CRUISE LINE INTEL (Any pricing mentions, itinerary changes, ship issues, service quality notes)
3. BOOKING SIGNALS (Questions about upcoming voyages, interest in specific destinations, upgrade discussions)
4. COMPETITOR WATCH (Any mentions of competing lines, comparisons, passengers switching brands)
5. ADVISOR OPPORTUNITIES (Posts where someone needs help, is looking for advice, or could benefit from a travel advisor)

For each item:
- One-line summary
- Source group name
- Relevance to D2M: HIGH / MEDIUM / LOW

Be specific about ship names, voyage dates, and destinations when mentioned.

RAW POSTS:
{raw_text[:12000]}"""

    try:
        result = subprocess.run(
            [CLAUDE_CLI, "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "TERM": "dumb"},
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            logger.error(f"Claude CLI error: {result.stderr[:200]}")
            return f"[Claude summarization failed — returning raw feed]\n\n{raw_text[:3000]}"
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return f"[Claude summarization timed out — returning raw feed]\n\n{raw_text[:3000]}"
    except Exception as e:
        logger.error(f"Claude CLI error: {e}")
        return f"[Claude summarization error: {e}]\n\n{raw_text[:3000]}"


# ---------------------------------------------------------------------------
# HTML RENDERER
# ---------------------------------------------------------------------------

def _img_base64(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _clean_fb_text(text):
    """Strip Facebook UI noise from post text."""
    noise = [
        "Like", "Comment", "Send", "Share",
        "Write a comment", "Write a public comment",
        "Make your avatar", "View more comments",
        "All reactions:", "See all", "Facebook",
        "Most relevant", "Newest", "All comments",
    ]
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        # Skip lines that are just noise
        if line in noise:
            continue
        # Skip lines that are just numbers (reaction counts)
        if line.isdigit():
            continue
        # Skip scrambled text (Facebook anti-scrape)
        if len(line) < 20 and all(len(w) <= 2 for w in line.split()):
            continue
        cleaned.append(line)
    return "\n".join(cleaned[:30])  # Cap at 30 lines per post


def render_cruise_digest_html(ai_summary, group_results):
    """Render cruise community digest as branded HTML."""
    logo_uri = _img_base64(LOGO_FILE)
    now = datetime.now()

    total_groups = len([g for g in group_results if g["status"] == "ok"])
    total_posts = sum(len(g["posts"]) for g in group_results if g["status"] == "ok")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #080d14; color: #e0e6ed; line-height: 1.6; }}
  .container {{ max-width: 750px; margin: 0 auto; background: #0d1b2e; }}
  .header {{ background: linear-gradient(135deg, #0d1b2e 0%, #1e3358 100%); padding: 24px; text-align: center; border-bottom: 3px solid #c9a84c; }}
  .header img {{ height: 50px; margin-bottom: 8px; }}
  .header h1 {{ color: #c9a84c; font-size: 22px; letter-spacing: 2px; margin: 4px 0; }}
  .header .meta {{ color: #8a9ab5; font-size: 13px; }}
  .section {{ padding: 20px 24px; border-bottom: 1px solid #1e3358; }}
  .section-title {{ color: #c9a84c; font-size: 16px; font-weight: 700; letter-spacing: 1px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #c9a84c33; }}
  .summary-box {{ background: #152540; padding: 16px; border-radius: 6px; border: 1px solid #c9a84c44; white-space: pre-wrap; font-size: 14px; line-height: 1.7; }}
  .group-block {{ margin: 16px 0; }}
  .group-name {{ color: #c9a84c; font-weight: 700; font-size: 15px; margin-bottom: 8px; }}
  .group-name a {{ color: #c9a84c; text-decoration: none; }}
  .post-card {{ background: #0a1520; margin: 8px 0; padding: 12px; border-radius: 4px; border-left: 3px solid #1e3358; }}
  .post-text {{ font-size: 13px; color: #c8d0dc; white-space: pre-wrap; word-wrap: break-word; }}
  .post-links a {{ color: #e8c97a; font-size: 12px; text-decoration: none; display: block; margin: 2px 0; }}
  .error-msg {{ color: #ff6666; font-style: italic; font-size: 13px; }}
  .stat-grid {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }}
  .stat-box {{ background: #152540; padding: 10px 16px; border-radius: 4px; text-align: center; flex: 1; min-width: 100px; }}
  .stat-num {{ color: #e8c97a; font-size: 22px; font-weight: 700; }}
  .stat-label {{ color: #8a9ab5; font-size: 11px; text-transform: uppercase; }}
  .footer {{ padding: 16px 24px; text-align: center; color: #8a9ab5; font-size: 11px; border-top: 1px solid #1e3358; }}
  .pub-hook {{ display: none; }}
</style>
</head>
<body>
<div class="container">

<div class="header">
  {"<img src='" + logo_uri + "' alt='D2M'>" if logo_uri else ""}
  <h1>CRUISE COMMUNITY DIGEST</h1>
  <div class="meta">{now.strftime('%A, %B %d, %Y')} &mdash; 0900 MT</div>
</div>

<div class="section">
  <div class="stat-grid">
    <div class="stat-box"><div class="stat-num">{total_groups}</div><div class="stat-label">Groups</div></div>
    <div class="stat-box"><div class="stat-num">{total_posts}</div><div class="stat-label">Posts</div></div>
  </div>
</div>

<div class="section">
  <div class="section-title">&#9733; AI CRUISE INTEL SUMMARY</div>
  <div class="summary-box">{ai_summary}</div>
</div>
"""

    # --- GROUP FEEDS ---
    html += """
<div class="section">
  <div class="section-title">&#128674; GROUP FEEDS</div>
"""
    for group in group_results:
        name = group["name"]
        url = group["url"]

        html += f'<div class="group-block">'
        html += f'<div class="group-name"><a href="{url}" target="_blank">{name}</a></div>'

        if group["status"] == "ok" and group["posts"]:
            for post in group["posts"]:
                cleaned = _clean_fb_text(post.get("text", ""))
                cleaned_html = cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

                html += f'<div class="post-card">'
                html += f'<div class="post-text">{cleaned_html}</div>'

                if post.get("links"):
                    html += '<div class="post-links" style="margin-top:6px;padding-top:6px;border-top:1px solid #1e3358;">'
                    seen = set()
                    for link in post["links"]:
                        if link["url"] not in seen and "facebook.com/groups/feed" not in link["url"]:
                            lt = link["text"][:80].replace("&", "&amp;").replace("<", "&lt;")
                            html += f'<a href="{link["url"]}" target="_blank">&#128279; {lt}</a>'
                            seen.add(link["url"])
                    html += '</div>'

                html += '</div>'
        elif group["status"] == "error":
            html += f'<div class="post-card"><div class="error-msg">{group.get("error", "Unknown error")}</div></div>'
        else:
            html += '<div class="post-card"><div class="error-msg">No posts extracted</div></div>'

        html += '</div>'

        # Publishing hook
        html += f'<div class="pub-hook" data-group="{name}" data-url="{url}" data-scraped="{datetime.now().isoformat()}" data-posts="{len(group.get("posts", []))}"></div>'

    html += "</div>"

    # --- FOOTER ---
    html += f"""
<div class="footer">
  CRUISE COMMUNITY DIGEST &mdash; Dreams2Memories Travel, LLC<br>
  Generated {now.strftime('%Y-%m-%d %H:%M')} MT &mdash; {total_groups} groups, {total_posts} posts
</div>
<div class="pub-hook" data-digest-id="{now.strftime('%Y%m%d_%H%M')}" data-type="cruise" data-groups="{total_groups}" data-posts="{total_posts}"></div>
</div>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# EMAIL & SMS
# ---------------------------------------------------------------------------

def send_digest_email(html_content, subject):
    service = _get_gmail_service()
    msg = MIMEMultipart("alternative")
    msg["To"] = COMMANDER_EMAIL
    msg["From"] = OPS_EMAIL
    msg["Subject"] = subject

    plain = f"Cruise Community Digest — {datetime.now().strftime('%B %d, %Y')}\nView in HTML email client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"Digest SENT to {COMMANDER_EMAIL}: {subject}")


def send_sms_ping():
    try:
        service = _get_gmail_service()
        sms_msg = MIMEText("Cruise Community Digest delivered. Check email.")
        sms_msg["to"] = "7192910742@tmomail.net"
        sms_msg["from"] = OPS_EMAIL
        sms_msg["subject"] = "THUNDERBIRD"
        raw = base64.urlsafe_b64encode(sms_msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except Exception as e:
        logger.error(f"SMS ping failed: {e}")


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

async def run_digest(preview=False):
    now = datetime.now()
    logger.info(f"{'='*60}")
    logger.info(f"CRUISE COMMUNITY DIGEST — {now.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"{'='*60}")

    # 1. Scrape Facebook groups
    logger.info("Phase 1: Scraping Facebook cruise groups...")
    group_results = await scrape_all_fb_groups()

    # 2. AI Summary
    logger.info("Phase 2: Claude Opus summarization...")
    ai_summary = await summarize_cruise_feeds(group_results)

    # 3. Render HTML
    logger.info("Phase 3: Rendering HTML digest...")
    html = render_cruise_digest_html(ai_summary, group_results)

    # 4. Save or send
    if preview:
        outpath = OUTPUT_DIR / f"cruise_digest_{now.strftime('%Y%m%d_%H%M')}.html"
        outpath.write_text(html, encoding="utf-8")
        logger.info(f"Preview saved: {outpath}")
        print(f"Preview: {outpath}")
    else:
        ok_count = sum(1 for g in group_results if g["status"] == "ok")
        subject = f"CRUISE COMMUNITY DIGEST // {now.strftime('%b %d')} — {ok_count} groups"
        send_digest_email(html, subject)
        send_sms_ping()
        logger.info("Digest complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cruise Community Digest")
    parser.add_argument("--preview", action="store_true", help="Save HTML locally, don't send")
    args = parser.parse_args()

    asyncio.run(run_digest(preview=args.preview))
