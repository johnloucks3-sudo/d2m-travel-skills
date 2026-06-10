---
name: xvfb-driver
description: "Xvfb + Headful Firefox driver for Playwright — bypasses Akamai Bot Manager and similar CDN bot detectors. Triggers on: xvfb, headful firefox, akamai bypass, cdn bypass, bot detection bypass, portal automation, automated login, cookie injection, persistent profile, x11 browser, headless bypass"
---

# /xvfb-driver — Xvfb + Headful Firefox Portal Automation

Bypasses CDN bot detectors (Akamai, Cloudflare, reCAPTCHA) by presenting a real X11 desktop environment with headful Firefox. Proven on RSSC (Regent) agent portal. Use for any login-gated travel portal that blocks headless browsers.

## Architecture

`XvfbDriver` — async context manager in `core/ai_infra/xvfb_driver.py`

```
XvfbDriver (async context manager)
  ├── __init__        — display num, profile dir, viewport
  ├── __aenter__      — lock cleanup → Xvfb spawn → DISPLAY set → Firefox launch → cookie restore
  ├── __aexit__       — cookie save → browser close → Xvfb kill → DISPLAY restore
  ├── navigate()      — goto + return {url, title, text_snippet}
  ├── screenshot()    — full-page screenshot
  ├── evaluate()      — JS eval with error handling
  ├── save_cookies()  — context.cookies() → JSON file
  └── load_cookies()  — JSON file → context.add_cookies()
```

## Usage

```python
from core.ai_infra.xvfb_driver import XvfbDriver

async with XvfbDriver(display_num=99, profile_dir="state/my_portal") as d:
    info = await d.navigate("https://portal.com/login")
    print(f"Page: {info['title']}")

    # Fill login form
    await d.page.fill("#username", "email@example.com")
    await d.page.fill("#password", "sekret")
    await d.page.keyboard.press("Enter")
    await asyncio.sleep(5)

    # Capture cookies
    cookies = await d.page.context.cookies()
    await d.save_cookies("creds/portal_cookies.json")
```

## Cookie Persistence Strategy

Cookies auto-save to `{profile_dir}/cookies.json` on exit and auto-load on entry. This means:
- **First run**: Manual login (or auto-login) → cookies saved
- **Subsequent runs**: Cookies loaded automatically → already authenticated
- **Expired cookies**: Script detects auth failure → triggers re-login → saves fresh cookies

## Three-Tier Architecture

| Tier | Method | When |
|------|--------|------|
| **Tier 1** | `XvfbDriver` headless=False (headful Firefox in Xvfb) | First login, session refresh, portals with strict bot detection |
| **Tier 2** | Persistent profile with `launch_persistent_context(headless=True)` | Daily scraping between logins (cookies still valid) |
| **Tier 3** | Commander manual login in persistent profile | Emergency fallback if automated login fails |

## Supported Portals (confirmed)

| Portal | Status | Notes |
|--------|--------|-------|
| Regent RSSC (rssc.com/agent) | ✅ AUTOMATED | Login: `#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox` |
| Centrav (centrav.com) | 🔧 IN PROGRESS | Uses reCAPTCHA v2 — Xvfb headful reduces triggers |
| Silversea (my.silversea.com) | 🔧 IN PROGRESS | Needs password from Commander |
| Room-Res (room-res.com) | 🔧 IN PROGRESS | Hotel booking portal, credentials available |

## Quick Test

```bash
/home/john/Thunderbird/.venv_scraper/bin/python3 -c "
import asyncio
from core.ai_infra.xvfb_driver import XvfbDriver
async def t():
    async with XvfbDriver(display_num=99) as d:
        info = await d.navigate('https://example.com')
        print(f'OK: {info[\"title\"]}')
asyncio.run(t())
" 2>&1 | grep -E '(OK:|ERROR|ready)'
```
