"""
Thunderbird Vision Utility
===========================
General-purpose vision analysis using Groq Llama-4-Scout (free, fast).

Supports:
  - Single image analysis
  - Two-image comparison (wireframe vs rendered, diagram vs built, hotel vs proposal, etc.)
  - HTML side-by-side viewer with AI analysis inline
  - Load from file path, URL, or raw base64

Usage:
    from thunderbird_vision import vision_analyze, vision_compare, render_comparison_html

    # Analyze one image
    result = vision_analyze("screenshot.png", mode="ui")

    # Compare two images
    result = vision_compare("wireframe.png", "screenshot.png", mode="ui")

    # Compare and open HTML viewer
    vision_compare("wireframe.png", "screenshot.png", mode="ui", render=True)
"""

import os
import base64
import json
import requests
import mimetypes
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional, Union

# ── Groq config ──────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "***REMOVED-SECRET***")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ── Output directory ──────────────────────────────────────────────────────────
_OUTPUT_DIR = Path(__file__).parent.parent / "output" / "vision"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Mode prompts ─────────────────────────────────────────────────────────────
ANALYZE_PROMPTS = {
    "ui": (
        "You are a UI/UX reviewer. Analyze this interface screenshot or wireframe. "
        "Describe: layout structure, key components, navigation, visual hierarchy, "
        "any usability concerns."
    ),
    "arch": (
        "You are a software architect. Analyze this architecture or system diagram. "
        "Identify: components, data flows, dependencies, integration points, "
        "potential bottlenecks or gaps."
    ),
    "travel": (
        "You are a luxury travel consultant for Dreams2Memories Travel. "
        "Analyze this image of a hotel, ship, destination, or itinerary. "
        "Describe: property quality, standout features, client appeal, price tier indicators, "
        "any red flags."
    ),
    "general": (
        "Analyze this image thoroughly. Describe what you see, identify key elements, "
        "note anything significant or actionable."
    ),
}

COMPARE_PROMPTS = {
    "ui": (
        "You are a UI/UX QA reviewer comparing two images.\n"
        "Image 1 is the WIREFRAME or DESIGN SPEC.\n"
        "Image 2 is the RENDERED/BUILT OUTPUT.\n\n"
        "Provide:\n"
        "1. MATCH — What was implemented correctly\n"
        "2. GAPS — What's missing or wrong vs the spec\n"
        "3. EXTRAS — Anything added that wasn't in the spec\n"
        "4. PRIORITY FIXES — Top 3 things to change, ranked\n"
    ),
    "arch": (
        "You are a software architect comparing two diagrams.\n"
        "Image 1 is the PROPOSED or PLANNED architecture.\n"
        "Image 2 is the CURRENT or BUILT state.\n\n"
        "Provide:\n"
        "1. ALIGNED — What matches the plan\n"
        "2. DRIFT — Where the build diverged from the plan\n"
        "3. RISK — Any architectural risks introduced by the drift\n"
        "4. RECOMMENDATIONS — What to reconcile\n"
    ),
    "travel": (
        "You are a luxury travel consultant comparing two images for Dreams2Memories Travel.\n"
        "Image 1 is the REFERENCE (e.g., what was promised, a competitor, or the proposal).\n"
        "Image 2 is the COMPARISON (e.g., actual property, alternative option, or client photo).\n\n"
        "Provide:\n"
        "1. STRENGTHS — Where Image 2 meets or exceeds Image 1\n"
        "2. GAPS — Where Image 2 falls short\n"
        "3. CLIENT APPEAL — Which would a luxury client prefer and why\n"
        "4. RECOMMENDATION — What to tell the client\n"
    ),
    "general": (
        "Compare these two images carefully.\n"
        "Image 1 is the REFERENCE.\n"
        "Image 2 is the COMPARISON.\n\n"
        "Provide:\n"
        "1. SIMILARITIES — What matches between them\n"
        "2. DIFFERENCES — Key differences, most important first\n"
        "3. ASSESSMENT — Which is better/preferred for the apparent use case and why\n"
    ),
}


# ── Image loading ─────────────────────────────────────────────────────────────

def load_image_b64(source: str) -> tuple[str, str]:
    """Load image from file path, URL, or raw base64. Returns (b64_string, mime_type)."""
    # Already base64
    if source.startswith("data:"):
        # data:image/jpeg;base64,....
        header, data = source.split(",", 1)
        mime = header.split(";")[0].replace("data:", "")
        return data, mime

    # URL
    if source.startswith("http://") or source.startswith("https://"):
        resp = requests.get(source, timeout=15)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        return base64.b64encode(resp.content).decode(), mime

    # File path
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {source}")
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/jpeg"
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode(), mime


# ── Groq vision call ──────────────────────────────────────────────────────────

def _groq_vision(system_prompt: str, user_text: str,
                 images: list[tuple[str, str]],  # [(b64, mime), ...]
                 max_tokens: int = 1500) -> str:
    """Call Groq vision model with one or more images."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set — cannot call vision model")

    # Build multi-part user content
    content = [{"type": "text", "text": user_text}]
    for b64, mime in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": content},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ── Public API ────────────────────────────────────────────────────────────────

def vision_analyze(image: str,
                   prompt: str = None,
                   mode: str = "general",
                   render: bool = False) -> dict:
    """
    Analyze a single image.

    Args:
        image:  File path, URL, or base64 string
        prompt: Custom prompt (overrides mode default)
        mode:   "ui" | "arch" | "travel" | "general"
        render: If True, open HTML viewer in browser

    Returns:
        {"analysis": str, "model": str, "html_path": str|None}
    """
    system = prompt or ANALYZE_PROMPTS.get(mode, ANALYZE_PROMPTS["general"])
    b64, mime = load_image_b64(image)
    analysis = _groq_vision(system, "Analyze this image.", [(b64, mime)])

    html_path = None
    if render:
        html_path = _render_single_html(image, b64, mime, analysis, mode)
        webbrowser.open(f"file://{html_path}")

    return {"analysis": analysis, "model": VISION_MODEL, "html_path": html_path}


def vision_compare(image_a: str,
                   image_b: str,
                   label_a: str = "Reference / Spec",
                   label_b: str = "Output / Built",
                   prompt: str = None,
                   mode: str = "general",
                   render: bool = False) -> dict:
    """
    Compare two images side-by-side.

    Args:
        image_a:  First image — file path, URL, or base64
        image_b:  Second image — file path, URL, or base64
        label_a:  Label for image A (shown in HTML viewer)
        label_b:  Label for image B (shown in HTML viewer)
        prompt:   Custom prompt (overrides mode default)
        mode:     "ui" | "arch" | "travel" | "general"
        render:   If True, open HTML viewer in browser

    Returns:
        {"analysis": str, "model": str, "html_path": str|None}

    Example — wireframe vs rendered:
        vision_compare("wireframe.png", "screenshot.png", mode="ui", render=True)

    Example — hotel proposal vs actual:
        vision_compare("proposal_hotel.jpg", "actual_photo.jpg",
                       label_a="Proposed Hotel", label_b="Actual Property",
                       mode="travel", render=True)
    """
    system = prompt or COMPARE_PROMPTS.get(mode, COMPARE_PROMPTS["general"])
    b64_a, mime_a = load_image_b64(image_a)
    b64_b, mime_b = load_image_b64(image_b)

    user_text = (
        f"Image 1 ({label_a}) is provided first, "
        f"Image 2 ({label_b}) is provided second. "
        "Compare them per your instructions."
    )
    analysis = _groq_vision(system, user_text, [(b64_a, mime_a), (b64_b, mime_b)])

    html_path = None
    if render:
        html_path = _render_compare_html(
            image_a, b64_a, mime_a, label_a,
            image_b, b64_b, mime_b, label_b,
            analysis, mode,
        )
        webbrowser.open(f"file://{html_path}")

    return {"analysis": analysis, "model": VISION_MODEL, "html_path": html_path}


# ── HTML renderers ────────────────────────────────────────────────────────────

def _md_to_html(text: str) -> str:
    """Minimal markdown → HTML (bold, headers, newlines). No deps."""
    import re
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'^#{1,3} (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\. ', r'<li>', text, flags=re.MULTILINE)
    text = text.replace('\n', '<br>')
    return text


def _render_single_html(source: str, b64: str, mime: str,
                        analysis: str, mode: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = _OUTPUT_DIR / f"vision_{mode}_{ts}.html"
    label = Path(source).name if not source.startswith("http") else source[:60]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Vision Analysis — {mode}</title>
<style>
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #1a1a1a; margin: 0; padding: 24px; }}
  h1   {{ color: #0000ff; font-size: 1.4rem; border-bottom: 2px solid #0000ff; padding-bottom: 8px; }}
  .tag {{ display: inline-block; background: #0000ff; color: #fff;
          font-size: .75rem; padding: 2px 10px; border-radius: 12px; margin-bottom: 16px; }}
  .img-wrap {{ text-align: center; margin-bottom: 24px; }}
  .img-wrap img {{ max-width: 100%; max-height: 520px; border: 2px solid #ccc;
                   border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,.15); }}
  .label {{ font-size: .85rem; color: #666; margin-top: 6px; }}
  .analysis {{ background: #fff; border-left: 4px solid #0000ff;
               padding: 20px 24px; border-radius: 4px; line-height: 1.7;
               box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .model {{ font-size: .75rem; color: #999; margin-top: 16px; }}
</style>
</head>
<body>
  <h1>Vision Analysis</h1>
  <span class="tag">{mode.upper()}</span>
  <div class="img-wrap">
    <img src="data:{mime};base64,{b64}" alt="analyzed image">
    <div class="label">{label}</div>
  </div>
  <div class="analysis">{_md_to_html(analysis)}</div>
  <div class="model">Model: {VISION_MODEL} via Groq · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
</body>
</html>"""

    out.write_text(html)
    return str(out)


def _render_compare_html(src_a: str, b64_a: str, mime_a: str, label_a: str,
                          src_b: str, b64_b: str, mime_b: str, label_b: str,
                          analysis: str, mode: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = _OUTPUT_DIR / f"vision_compare_{mode}_{ts}.html"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Vision Comparison — {mode}</title>
<style>
  body  {{ font-family: Georgia, serif; background: #f7f3ea; color: #1a1a1a; margin: 0; padding: 24px; }}
  h1    {{ color: #0000ff; font-size: 1.4rem; border-bottom: 2px solid #0000ff; padding-bottom: 8px; }}
  .tag  {{ display: inline-block; background: #0000ff; color: #fff;
           font-size: .75rem; padding: 2px 10px; border-radius: 12px; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 28px; }}
  .panel {{ background: #fff; border-radius: 6px; padding: 14px;
            box-shadow: 0 1px 4px rgba(0,0,0,.1); text-align: center; }}
  .panel img {{ max-width: 100%; max-height: 440px; border: 1px solid #ddd; border-radius: 3px; }}
  .panel .lbl {{ font-size: .9rem; font-weight: bold; color: #0000ff; margin-bottom: 10px; }}
  .analysis {{ background: #fff; border-left: 4px solid #0000ff;
               padding: 20px 24px; border-radius: 4px; line-height: 1.7;
               box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .model {{ font-size: .75rem; color: #999; margin-top: 16px; }}
  strong {{ color: #0000ff; }}
</style>
</head>
<body>
  <h1>Vision Comparison</h1>
  <span class="tag">{mode.upper()}</span>
  <div class="grid">
    <div class="panel">
      <div class="lbl">{label_a}</div>
      <img src="data:{mime_a};base64,{b64_a}" alt="{label_a}">
    </div>
    <div class="panel">
      <div class="lbl">{label_b}</div>
      <img src="data:{mime_b};base64,{b64_b}" alt="{label_b}">
    </div>
  </div>
  <div class="analysis">{_md_to_html(analysis)}</div>
  <div class="model">Model: {VISION_MODEL} via Groq · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
</body>
</html>"""

    out.write_text(html)
    return str(out)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Thunderbird Vision Utility")
    parser.add_argument("images", nargs="+", help="Image path(s) or URL(s) — 1 to analyze, 2 to compare")
    parser.add_argument("--mode", default="general", choices=["ui", "arch", "travel", "general"])
    parser.add_argument("--label-a", default="Reference / Spec")
    parser.add_argument("--label-b", default="Output / Built")
    parser.add_argument("--prompt", default=None, help="Custom prompt override")
    parser.add_argument("--render", action="store_true", help="Open HTML viewer in browser")
    parser.add_argument("--no-render", dest="render", action="store_false")
    parser.set_defaults(render=True)
    args = parser.parse_args()

    if len(args.images) == 1:
        result = vision_analyze(args.images[0], prompt=args.prompt,
                                mode=args.mode, render=args.render)
    else:
        result = vision_compare(args.images[0], args.images[1],
                                label_a=args.label_a, label_b=args.label_b,
                                prompt=args.prompt, mode=args.mode, render=args.render)

    print("\n── ANALYSIS ──────────────────────────────────────────────")
    print(result["analysis"])
    if result.get("html_path"):
        print(f"\n── HTML viewer → {result['html_path']}")
