#!/usr/bin/env python3
"""
grok_imagine.py — generate/edit an image via Grok Imagine (grok.com/imagine),
driving the Commander's own logged-in browser through `bsk` (browser-skill).

Same spirit as grok_call.py: the personal SuperGrok subscription, not the
metered XAI_API_KEY lane. Image attachment (optional --reference) goes through
the OS clipboard via `xclip` — grok.com's upload button opens a native OS file
picker bsk cannot drive, but the composer accepts a pasted image, which xclip
can seed without any dialog.

Requires: `bsk daemon` running with a browser connected, the Commander already
logged into grok.com in that browser (human-only wall, same as grok_call.py),
and `xclip` on PATH for --reference (X11 only — no Wayland clipboard tool
wired here, add wl-copy if this ever runs under Wayland).

Usage:
  python3 scripts/grok_imagine.py --prompt "..." [--reference path/to/img.png]
      [--mode image|video|agent] [--quality speed|quality] [--out path/to/save.jpg]
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

IMAGINE_URL = "https://grok.com/imagine"


def run_bsk(*args) -> str:
    result = subprocess.run(["bsk", *args], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"bsk {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def find_ref(snapshot: str, text_match: str, role: str | None = None) -> str | None:
    """Find a snapshot ref (@eN) on a line matching text_match (and role, if given)."""
    for line in snapshot.splitlines():
        if text_match.lower() not in line.lower():
            continue
        if role and role.lower() not in line.lower():
            continue
        m = re.search(r"@e\d+", line)
        if m:
            return m.group(0)
    return None


def attach_reference(session: str, image_path: Path) -> None:
    if not image_path.exists():
        raise FileNotFoundError(f"reference image not found: {image_path}")
    subprocess.run(
        ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", str(image_path)],
        check=True, timeout=15,
    )
    snap = run_bsk("snapshot", "--session", session)
    box = find_ref(snap, "Ask Grok anything", role="textbox")
    if not box:
        raise RuntimeError("could not find Imagine composer textbox to paste reference into")
    run_bsk("click", "--session", session, box)
    time.sleep(0.5)
    run_bsk("press", "--session", session, "Control+v")
    time.sleep(2)


def submit_and_wait(session: str, prompt: str, mode: str, quality: str, timeout_s: int = 180) -> None:
    snap = run_bsk("snapshot", "--session", session)
    box = find_ref(snap, "Ask Grok anything", role="textbox")
    if not box:
        raise RuntimeError("could not find Imagine composer textbox")
    run_bsk("fill", "--session", session, box, "--value", prompt)
    time.sleep(0.5)

    # Mode/quality radios only exist pre-attachment on a fresh composer; if a
    # reference image is attached the quality radiogroup may be hidden — best
    # effort, not fatal if a click target isn't found.
    snap = run_bsk("snapshot", "--session", session)
    mode_ref = find_ref(snap, f'"{mode.capitalize()}"', role="radio")
    if mode_ref:
        run_bsk("click", "--session", session, mode_ref)
        time.sleep(0.5)
    snap = run_bsk("snapshot", "--session", session)
    quality_ref = find_ref(snap, f'"{quality.capitalize()}"', role="radio")
    if quality_ref:
        run_bsk("click", "--session", session, quality_ref)
        time.sleep(0.5)

    snap = run_bsk("snapshot", "--session", session)
    submit_ref = find_ref(snap, "Submit", role="button")
    if not submit_ref:
        raise RuntimeError("could not find Submit button")
    run_bsk("click", "--session", session, submit_ref)

    # Poll for completion: the result panel exposes a "Download" button once
    # generation finishes. No stable "done" text like grok_call.py's chat
    # composer has, so poll on control presence instead.
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(3)
        snap = run_bsk("snapshot", "--session", session)
        if 'button "Download"' in snap:
            return
    raise TimeoutError(f"Imagine generation did not finish within {timeout_s}s")


def download_result(session: str, out_path: Path, downloads_dir: Path) -> Path:
    before = {p.name for p in downloads_dir.glob("*")}
    snap = run_bsk("snapshot", "--session", session)
    dl_ref = find_ref(snap, "Download", role="button")
    if not dl_ref:
        raise RuntimeError("Download button not found after generation completed")
    run_bsk("click", "--session", session, dl_ref)
    time.sleep(3)
    after = {p.name for p in downloads_dir.glob("*")}
    new_files = after - before
    if not new_files:
        raise RuntimeError(f"no new file appeared in {downloads_dir} after clicking Download")
    newest = max((downloads_dir / n for n in new_files), key=lambda p: p.stat().st_mtime)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(newest.read_bytes())
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--reference", type=Path, help="local image path to attach as an editing reference")
    ap.add_argument("--mode", default="image", choices=["image", "video", "agent"])
    ap.add_argument("--quality", default="speed", choices=["speed", "quality"])
    ap.add_argument("--out", type=Path, required=True, help="where to save the downloaded result")
    ap.add_argument("--downloads-dir", type=Path, default=Path.home() / "Downloads")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    session = run_bsk("session", "start").strip()
    try:
        run_bsk("navigate", "--session", session, IMAGINE_URL)
        time.sleep(3)
        if args.reference:
            attach_reference(session, args.reference)
        submit_and_wait(session, args.prompt, args.mode, args.quality, timeout_s=args.timeout)
        result_path = download_result(session, args.out, args.downloads_dir)
        print(str(result_path))
        return 0
    finally:
        try:
            run_bsk("session", "stop", session)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
