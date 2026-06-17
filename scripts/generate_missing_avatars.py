#!/usr/bin/env python3
"""
MISSION-078: Generate missing persona avatars via Gemini 2.5 Flash Image
Generates headshots for Wing personas that lack storage/output/images/*_avatar.png
"""

import os
import sys
import json
import base64
import time
import requests
from pathlib import Path

# Config
THUNDERBIRD = Path("/home/john/Thunderbird")
OUTPUT_DIR = THUNDERBIRD / "storage/output/images"
ENV_FILE = THUNDERBIRD / ".env"
MAX_AVATARS = 10
THROTTLE_SECS = 4
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

def load_api_key():
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found in .env")

def generate_image(api_key, prompt, persona_name):
    """Call Gemini image gen endpoint, return raw PNG bytes or None."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}"

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"]
        }
    }

    try:
        r = requests.post(url, json=body, timeout=90)
        if r.status_code != 200:
            print(f"  ERROR HTTP {r.status_code}: {r.text[:300]}")
            return None

        data = r.json()
        candidates = data.get("candidates", [])
        if not candidates:
            print(f"  ERROR: no candidates in response")
            print(f"  Response: {json.dumps(data)[:300]}")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                mime = part["inlineData"].get("mimeType", "")
                raw_b64 = part["inlineData"].get("data", "")
                if raw_b64:
                    return base64.b64decode(raw_b64)

        # No image found in parts - log what we got
        print(f"  ERROR: no inlineData in parts. Parts: {json.dumps(parts)[:400]}")
        return None

    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return None

def verify_png(path):
    """Check file is non-zero and starts with PNG magic bytes."""
    if not path.exists() or path.stat().st_size == 0:
        return False, "zero size or missing"
    with open(path, "rb") as f:
        header = f.read(8)
    if header[:4] == b'\x89PNG':
        return True, f"{path.stat().st_size:,} bytes"
    return False, f"bad header: {header.hex()}"

# ── Persona definitions ───────────────────────────────────────────────
# Each: (filename_stem, display_name, prompt)
# cream background #f7f3ea, warm shoulders-up portrait, matching existing set style

PERSONAS_TO_GENERATE = [
    (
        "thomas_sterling",
        "Thomas Sterling (A7)",
        (
            "Professional warm headshot portrait of Brigadier General Thomas Sterling (retired), "
            "a methodical and precise process improvement expert in his late 50s. "
            "Silver-gray hair, closely cropped, sharp intelligent eyes behind wire-frame glasses. "
            "Wears a dark navy blazer with a subtle tie. Expression: calm, analytical, quietly authoritative — "
            "the look of a man who has seen every failure mode and is measuring yours. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
    (
        "sofia_navarro",
        "Dr. Sofia Navarro (A1)",
        (
            "Professional warm headshot portrait of Dr. Sofia Navarro, a behavioral psychologist "
            "and client profiling expert in her early 40s. Latina, warm olive complexion, dark brown eyes "
            "that are intelligent and deeply observant — the eyes of someone who reads everything. "
            "Dark hair pulled back neatly, minimal tasteful jewelry. Wears a structured charcoal blazer. "
            "Expression: precise, contained warmth — quietly attentive, not cold, professional. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
    (
        "elon_wing",
        "ELON (A12)",
        (
            "Professional headshot portrait of a young tech entrepreneur in his early 30s, "
            "the wing's innovation and disruption specialist. Sharp angular features, slightly disheveled "
            "dark hair, bright intense eyes that look like they're already three steps ahead. "
            "Wears a dark heather-gray hoodie — his uniform. Expression: direct, irreverent, "
            "slightly impatient — the energy of someone who finds inefficiency physically painful. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
    (
        "marco_reyes",
        "Marco Reyes (A8)",
        (
            "Professional warm headshot portrait of Marco Reyes, a luxury cruise product manager "
            "and experience architect in his mid-40s. Mediterranean complexion, dark short hair "
            "with slight salt-and-pepper at the temples. Confident, direct gaze — the look of a man "
            "who has inspected 47 ships and has opinions about every one. Wears a fitted dark blazer. "
            "Expression: crisp confidence, zero hedging, product-obsessed. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
    (
        "daniel_marsh",
        "Daniel Marsh (A4 Keel)",
        (
            "Professional warm headshot portrait of Brigadier General Daniel 'Keel' Marsh (retired), "
            "a logistics expert in his late 50s. Solidly built, square jaw, close-cropped salt-and-pepper hair. "
            "Practical, no-nonsense presence. Wears a dark military-adjacent blazer. "
            "Expression: steady, dependable, the look of a man who pre-positions the parts before "
            "the airplanes need them. The train leaves on time — you can see it in his eyes. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
    (
        "sienna_navarro",
        "Sienna Navarro (A13)",
        (
            "Professional warm headshot portrait of Sienna 'Pulse' Navarro, a social media director "
            "and digital brand architect in her early 30s. Latina, vibrant energy, warm complexion, "
            "bright expressive eyes that read the cultural moment before it crystallizes. "
            "Modern professional look — stylish blouse, minimal jewelry. "
            "Expression: warm, energetic, creative confidence — the person who sees the pulse of a trend "
            "before anyone else does. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
    (
        "talon",
        "TALON (CONDOR Group Commander)",
        (
            "Professional warm headshot portrait of TALON, the CONDOR Group Commander, "
            "a strategic communications and quality evaluation expert in his early 50s. "
            "Refined, polished appearance — the look of someone who has made a career of knowing "
            "when words land and when they don't. Dark salt-and-pepper hair, measured thoughtful eyes. "
            "Wears a well-fitted dark blazer. Expression: evaluative, precise, quietly expecting excellence — "
            "a man who hears every sentence before he approves it. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
    (
        "jet",
        "JET (WIND Group Commander)",
        (
            "Professional warm headshot portrait of JET, the WIND Group Commander, "
            "a software engineer and infrastructure specialist in his late 30s. "
            "Technical, precise appearance — the look of someone who builds systems that don't break. "
            "Clean modern haircut, focused intelligent eyes behind minimal glasses. "
            "Wears a dark technical crew-neck sweater. Expression: practical, problem-first, "
            "processing three things at once but completely composed. "
            "Shoulders-up framing. Cream background (#f7f3ea). Soft professional studio lighting. "
            "Photorealistic portrait quality. No text."
        )
    ),
]

def main():
    print("=" * 60)
    print("MISSION-078: Persona Avatar Generation")
    print("=" * 60)

    # Load API key
    try:
        api_key = load_api_key()
        print(f"API key loaded: {api_key[:8]}...")
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check which already exist
    print(f"\nExisting avatars:")
    for p in sorted(OUTPUT_DIR.glob("*_avatar.png")):
        print(f"  {p.name} ({p.stat().st_size:,} bytes)")

    print(f"\nPersonas to generate ({len(PERSONAS_TO_GENERATE)} total, cap={MAX_AVATARS}):")
    for stem, name, _ in PERSONAS_TO_GENERATE:
        path = OUTPUT_DIR / f"{stem}_avatar.png"
        status = "EXISTS" if path.exists() else "MISSING"
        print(f"  {status}: {name} → {stem}_avatar.png")

    results = []
    generated = 0

    for i, (stem, name, prompt) in enumerate(PERSONAS_TO_GENERATE):
        if generated >= MAX_AVATARS:
            print(f"\nCap of {MAX_AVATARS} reached. Stopping.")
            break

        out_path = OUTPUT_DIR / f"{stem}_avatar.png"
        if out_path.exists():
            print(f"\n[{i+1}] SKIP {name} — already exists")
            continue

        print(f"\n[{i+1}] GENERATING: {name}")
        print(f"  Output: {out_path}")

        png_bytes = generate_image(api_key, prompt, name)

        if png_bytes:
            out_path.write_bytes(png_bytes)
            ok, detail = verify_png(out_path)
            if ok:
                print(f"  SUCCESS: {detail}")
                results.append({"name": name, "file": str(out_path), "size": out_path.stat().st_size, "status": "OK"})
                generated += 1
            else:
                print(f"  INVALID PNG: {detail}")
                out_path.unlink(missing_ok=True)
                results.append({"name": name, "file": str(out_path), "status": f"INVALID: {detail}"})
        else:
            print(f"  FAILED: no image data returned")
            results.append({"name": name, "file": str(out_path), "status": "FAILED: no data"})

        if i < len(PERSONAS_TO_GENERATE) - 1:
            print(f"  Throttling {THROTTLE_SECS}s...")
            time.sleep(THROTTLE_SECS)

    # Final report
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    ok_count = sum(1 for r in results if r["status"] == "OK")
    print(f"Generated: {ok_count}/{len(results)} attempted")
    for r in results:
        size_str = f" ({r['size']:,} bytes)" if "size" in r else ""
        print(f"  {r['status']:6s} {r['name']}{size_str}")

    # List still missing
    still_missing = []
    for stem, name, _ in PERSONAS_TO_GENERATE:
        path = OUTPUT_DIR / f"{stem}_avatar.png"
        if not path.exists():
            still_missing.append(name)

    if still_missing:
        print(f"\nStill missing ({len(still_missing)}):")
        for n in still_missing:
            print(f"  - {n}")
    else:
        print("\nAll target personas now have avatars.")

if __name__ == "__main__":
    main()
