#!/usr/bin/env python3
"""
email_preview.py — render a client-email HTML to PNG the way Gmail will receive it.
Standard gate: NO client draft is staged until its preview has been eyeballed.
Catches rendering breakage BEFORE the Commander ever sees it.

Usage:
  python3 scripts/email_preview.py path/to/email.html [--out preview.png] [--width 700] [--height 5200]

Pipeline: premailer-inline (as Gmail receives) -> headless Chrome screenshot.
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--out")
    ap.add_argument("--width", type=int, default=700)
    ap.add_argument("--height", type=int, default=5200)
    a = ap.parse_args()
    src = Path(a.html)
    if not src.exists():
        print(f"ERROR: {src} not found"); sys.exit(1)
    html = src.read_text(encoding="utf-8")
    try:
        import premailer
        html = premailer.transform(html, remove_classes=False, strip_important=False)
    except Exception as e:
        print(f"(premailer skipped: {e})")
    out = Path(a.out) if a.out else src.with_suffix(".preview.png")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tf:
        tf.write(html); tmp = tf.name
    chrome = next((c for c in ("google-chrome", "google-chrome-stable", "chromium") if _which(c)), None)
    if not chrome:
        print("ERROR: no chrome/chromium found"); sys.exit(1)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
           f"--window-size={a.width},{a.height}", f"--screenshot={out}", tmp]
    r = subprocess.run(cmd, capture_output=True, timeout=90)
    if out.exists():
        print(f"✓ preview: {out} ({out.stat().st_size//1024} KB)")
    else:
        print(f"✗ render failed: {r.stderr.decode()[:200]}"); sys.exit(1)

def _which(c):
    from shutil import which; return which(c)

if __name__ == "__main__":
    main()
