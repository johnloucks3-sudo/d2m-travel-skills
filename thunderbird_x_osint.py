"""
Thunderbird X/OSINT Scraper Module
Browser-based scraping of X/Twitter OSINT feeds with Claude summarization.
"""

import os
import json
import subprocess
import time
from datetime import datetime

FOLLOW_LIST = os.path.expanduser("~/Thunderbird/x_osint_follow_list.txt")
OUTPUT_DIR = os.path.expanduser("~/Thunderbird/output")
PROFILE = "x_twitter"


def load_follow_list(path=None):
    """Load OSINT accounts from follow list file."""
    path = path or FOLLOW_LIST
    accounts = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                accounts.append(line)
    return accounts


def fmt_briefing(account_data):
    """Format scraped account data into a readable briefing."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"OSINT DAILY BRIEFING — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    for acct in account_data:
        handle = acct.get("handle", "unknown")
        status = acct.get("status", "error")
        lines.append("")
        lines.append(f"--- @{handle} ---")

        if status == "ok":
            lines.append(acct.get("content", "(no content)"))
        else:
            lines.append(f"  [SKIP] {acct.get('error', 'unknown error')}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("END BRIEFING")
    lines.append("=" * 60)
    return "\n".join(lines)


def register_x_osint_tools(mcp):
    """Register X/OSINT tools with the MCP server."""

    @mcp.tool()
    async def scrape_x_osint_feed(
        accounts: str = "",
        max_length: int = 4000,
        save_briefing: bool = True,
    ) -> str:
        """Scrape latest posts from OSINT accounts on X/Twitter.

        Args:
            accounts: Comma-separated handles (default: load from follow list)
            max_length: Max chars to pull per account
            save_briefing: Save briefing to output/ directory
        """
        from thunderbird_browser import browse_url

        if accounts:
            account_list = [a.strip() for a in accounts.split(",")]
        else:
            account_list = load_follow_list()

        results = []
        for handle in account_list:
            try:
                url = f"https://x.com/{handle}"
                result = await browse_url(
                    url=url,
                    extract="text",
                    wait_seconds=5,
                    screenshot=False,
                    scroll=True,
                    max_length=max_length,
                    profile=PROFILE,
                )

                data = json.loads(result) if isinstance(result, str) else result
                inner = json.loads(data.get("result", "{}")) if isinstance(data.get("result"), str) else data

                title = inner.get("title", "")
                text = inner.get("text", "")

                if "Log in" in title or "Sign in" in text[:100]:
                    results.append({
                        "handle": handle,
                        "status": "error",
                        "error": "Session expired — need fresh auth_token"
                    })
                else:
                    results.append({
                        "handle": handle,
                        "status": "ok",
                        "content": text,
                    })

            except Exception as e:
                results.append({
                    "handle": handle,
                    "status": "error",
                    "error": str(e)
                })

            time.sleep(2)  # Be polite between requests

        briefing = fmt_briefing(results)

        if save_briefing:
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            outpath = os.path.join(OUTPUT_DIR, f"osint_briefing_{ts}.txt")
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(briefing)
            briefing += f"\n\nSaved to: {outpath}"

        return briefing

    @mcp.tool()
    async def summarize_x_osint(
        accounts: str = "",
        max_length: int = 4000,
    ) -> str:
        """Scrape OSINT feeds and summarize with Claude AI.

        Args:
            accounts: Comma-separated handles (default: load from follow list)
            max_length: Max chars to pull per account
        """
        CLAUDE_CLI = os.path.expanduser("~/.local/bin/claude")

        # First scrape
        raw_briefing = await scrape_x_osint_feed(
            accounts=accounts,
            max_length=max_length,
            save_briefing=False,
        )

        # Summarize with Claude CLI
        prompt = f"""You are an intelligence analyst. Summarize the following OSINT feed into a concise daily briefing.

Group by theme (conflicts, defense, geopolitics, etc). For each item:
- One-line summary of the intel
- Source account
- Significance rating: HIGH / MEDIUM / LOW

Skip duplicate stories. Flag anything that looks time-sensitive.

RAW FEED:
{raw_briefing}"""

        try:
            result = subprocess.run(
                [CLAUDE_CLI, "-p", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "TERM": "dumb"},
            )
            if result.returncode == 0 and result.stdout.strip():
                summary = result.stdout.strip()
            else:
                return raw_briefing + f"\n\n[Claude CLI error: {result.stderr[:200]}]"
        except subprocess.TimeoutExpired:
            return raw_briefing + "\n\n[Claude CLI timed out]"
        except Exception as e:
            return raw_briefing + f"\n\n[Claude error: {e}]"

        ts = datetime.now().strftime("%Y%m%d_%H%M")
        outpath = os.path.join(OUTPUT_DIR, f"osint_summary_{ts}.txt")
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(summary)
        return summary + f"\n\nSaved to: {outpath}"
