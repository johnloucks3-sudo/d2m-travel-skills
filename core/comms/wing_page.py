#!/usr/bin/env python3
"""
wing_page.py — Standardized Wing → Commander Communication

Commander doctrine 2026-06-19: macro awareness, not micromanagement.
Every Wing page follows the 5-part format. Short form to Telegram.
Long form renders to HTML screenshot + sendPhoto.

Format:
  1. Problem     — one sentence: what broke or what decision is needed
  2. Discussion  — 2-3 sentences: why it matters, context
  3. Options     — numbered list: the choices
  4. Action      — what the Wing did or is doing
  5. Next Steps  — what (if anything) Commander must do

Usage:
    from core.comms.wing_page import WingPage, send_page

    send_page(
        problem="Regent ASPXAUTH expired — Ely booking portal inaccessible.",
        discussion="Session died 2h before FPD contact window opens. Auto-heal failed (Akamai blocks headless). Manual Firefox login needed.",
        options=["1. Commander logs in now (2 min)", "2. Delay Ely contact to tonight"],
        action="Wing attempted auto-heal x2. Failed. Repair queue updated.",
        next_steps="Commander: open portal.rssc.com in Firefox, log in — Wing will capture cookies automatically.",
        level="P0",
        long_form=False,
    )
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent.parent
sys.path.insert(0, str(THUNDERBIRD / "OpsCenter"))

log = logging.getLogger("wing-page")

# Levels
P0 = "P0"   # Red — Commander action required now
P1 = "P1"   # Yellow — FYI, may need Commander soon
P2 = "P2"   # Green — informational, no action needed

LEVEL_EMOJI = {P0: "🚨", P1: "⚠️", P2: "ℹ️"}

# ---------------------------------------------------------------------------
# Core format builder
# ---------------------------------------------------------------------------

class WingPage:
    def __init__(
        self,
        problem: str,
        discussion: str = "",
        options: list[str] | None = None,
        action: str = "",
        next_steps: str = "",
        level: str = P1,
        source: str = "Hale",
    ):
        self.problem = problem
        self.discussion = discussion
        self.options = options or []
        self.action = action
        self.next_steps = next_steps
        self.level = level
        self.source = source

    def to_telegram(self) -> str:
        """Compact Telegram format — fits in a single message."""
        emoji = LEVEL_EMOJI.get(self.level, "📋")
        lines = [f"{emoji} <b>{self.level} — {self.source}</b>"]
        lines.append(f"\n<b>1. Problem:</b> {self.problem}")
        if self.discussion:
            lines.append(f"<b>2. Discussion:</b> {self.discussion}")
        if self.options:
            lines.append("<b>3. Options:</b>")
            for opt in self.options:
                lines.append(f"  {opt}")
        if self.action:
            lines.append(f"<b>4. Action:</b> {self.action}")
        if self.next_steps:
            lines.append(f"<b>5. Next Steps:</b> {self.next_steps}")
        return "\n".join(lines)

    def to_html(self, title: str = "") -> str:
        """Long-form HTML for screenshot delivery."""
        emoji = LEVEL_EMOJI.get(self.level, "📋")
        color = {"P0": "#c0392b", "P1": "#e67e22", "P2": "#27ae60"}.get(self.level, "#003087")
        header = title or f"{self.level} — Wing Page"

        opts_html = ""
        if self.options:
            items = "".join(f"<li>{o}</li>" for o in self.options)
            opts_html = f"<div class='section'><div class='label'>3. Options</div><ol>{items}</ol></div>"

        disc_html = f"<div class='section'><div class='label'>2. Discussion</div><p>{self.discussion}</p></div>" if self.discussion else ""
        act_html  = f"<div class='section'><div class='label'>4. Action</div><p>{self.action}</p></div>" if self.action else ""
        ns_html   = f"<div class='section'><div class='label'>5. Next Steps</div><p>{self.next_steps}</p></div>" if self.next_steps else ""

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #1a1a2e;
          margin: 0; padding: 24px; max-width: 680px; }}
  .header {{ background: {color}; color: white; padding: 16px 20px; border-radius: 8px;
             font-size: 22px; font-weight: bold; margin-bottom: 16px; }}
  .header .sub {{ font-size: 13px; opacity: 0.85; margin-top: 4px; }}
  .problem {{ background: white; border-left: 5px solid {color}; padding: 14px 18px;
              margin-bottom: 14px; border-radius: 0 6px 6px 0; font-size: 17px; font-weight: bold; }}
  .section {{ background: white; padding: 14px 18px; margin-bottom: 10px; border-radius: 6px; }}
  .label {{ color: {color}; font-weight: bold; font-size: 12px; text-transform: uppercase;
            letter-spacing: 1px; margin-bottom: 6px; }}
  p {{ margin: 0; line-height: 1.6; }}
  ol {{ margin: 6px 0 0 16px; padding: 0; line-height: 1.8; }}
  .footer {{ font-size: 11px; color: #888; margin-top: 16px; text-align: right; }}
</style></head><body>
<div class='header'>{emoji} {header}<div class='sub'>Thunderbird Wing · D2M · Source: {self.source}</div></div>
<div class='problem'>1. Problem: {self.problem}</div>
{disc_html}{opts_html}{act_html}{ns_html}
<div class='footer'>Generated by Wing — macro awareness briefing</div>
</body></html>"""

    def to_email_sss(self, subject: str = "") -> str:
        """USAF Staff Summary Sheet format for email body."""
        subj = subject or f"[{self.level}] {self.problem[:60]}"
        lines = [
            f"<b>SUBJECT:</b> {subj}",
            "<br><b>PURPOSE:</b> Decision / Awareness / Action required (see Section 5)",
            f"<br><b>BACKGROUND:</b> {self.discussion}" if self.discussion else "",
            "<br><b>DISCUSSION:</b>",
        ]
        if self.options:
            lines.append("<ol>" + "".join(f"<li>{o}</li>" for o in self.options) + "</ol>")
        if self.action:
            lines.append(f"<br><b>WING ACTION:</b> {self.action}")
        if self.next_steps:
            lines.append(f"<br><b>RECOMMENDATION / REQUIRED ACTION:</b> {self.next_steps}")
        lines.append("<br><br><i>— V. Hale, VCS · Thunderbird Wing · D2M</i>")
        return "\n".join(l for l in lines if l)


# ---------------------------------------------------------------------------
# Send helpers
# ---------------------------------------------------------------------------

def _load_env() -> dict:
    env = dict(os.environ)
    env_file = THUNDERBIRD / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def send_page(
    problem: str,
    discussion: str = "",
    options: list[str] | None = None,
    action: str = "",
    next_steps: str = "",
    level: str = P1,
    source: str = "Hale",
    long_form: bool = False,
    screenshot_title: str = "",
) -> bool:
    """
    Send a Wing page to Commander via Telegram.
    long_form=True: renders HTML screenshot + sends as photo.
    long_form=False: sends compact text message.
    """
    page = WingPage(
        problem=problem, discussion=discussion, options=options,
        action=action, next_steps=next_steps, level=level, source=source,
    )
    env = _load_env()
    token = env.get("TELEGRAM_D2MC2C_TOKEN", "")
    chat_id = env.get("TELEGRAM_COMMANDER_ID", "7554895206")

    if not token:
        log.error("TELEGRAM_D2MC2C_TOKEN not set")
        return False

    if long_form:
        return _send_screenshot(page, token, chat_id, screenshot_title)
    else:
        return _send_text(page, token, chat_id)


def _send_text(page: WingPage, token: str, chat_id: str) -> bool:
    try:
        import urllib.request
        text = page.to_telegram()
        # Split if over 4000 chars
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            payload = json.dumps({
                "chat_id": chat_id, "text": chunk, "parse_mode": "HTML"
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=payload, headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        log.error(f"Telegram text send failed: {e}")
        return False


def _send_screenshot(page: WingPage, token: str, chat_id: str, title: str = "") -> bool:
    """Render HTML → PNG → sendPhoto to Commander."""
    try:
        import asyncio
        from playwright.async_api import async_playwright

        html = page.to_html(title)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            f.write(html)
            html_path = f.name

        png_path = html_path.replace(".html", ".png")

        async def _render():
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page_obj = await browser.new_page(viewport={"width": 720, "height": 800})
                await page_obj.goto(f"file://{html_path}")
                await page_obj.wait_for_load_state("networkidle")
                # Fit to content
                height = await page_obj.evaluate("document.body.scrollHeight")
                await page_obj.set_viewport_size({"width": 720, "height": max(height + 40, 200)})
                await page_obj.screenshot(path=png_path, full_page=True)
                await browser.close()

        asyncio.run(_render())

        # Send photo
        import urllib.request
        with open(png_path, "rb") as img:
            from urllib.request import Request
            import urllib.parse
            boundary = "----ThunderbirdBoundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="photo"; filename="wing_page.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode() + img.read() + f"\r\n--{boundary}--\r\n".encode()

            req = Request(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=20)

        # Clean up
        Path(html_path).unlink(missing_ok=True)
        Path(png_path).unlink(missing_ok=True)
        return True

    except Exception as e:
        log.error(f"Screenshot send failed: {e}")
        # Fall back to text
        return _send_text(page, token, chat_id)
