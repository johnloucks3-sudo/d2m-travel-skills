#!/usr/bin/env python3
"""
D2M Brand Kit Generator
Produces platform-specific social media assets from Agency_Logo_Enhanced.png
Output: app/static/img/brand/  (web-accessible) + media/brand_kit/ (archive)
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import shutil

SRC_LOGO = Path("/home/john/Thunderbird/media/Agency_Logo_Enhanced.png")
OUT_WEB = Path("/home/john/Thunderbird/app/static/img/brand")
OUT_ARCHIVE = Path("/home/john/Thunderbird/media/brand_kit")

NAVY = (0, 51, 160)       # #0033A0
CREAM = (247, 243, 234)   # #f7f3ea
GOLD = (201, 168, 76)     # #c9a84c
WHITE = (255, 255, 255)

for d in [OUT_WEB, OUT_ARCHIVE]:
    d.mkdir(parents=True, exist_ok=True)

logo_src = Image.open(SRC_LOGO).convert("RGBA")
logo_w, logo_h = logo_src.size
logo_ratio = logo_w / logo_h  # ~1.34


def make_square_profile(size: int, padding_pct: float = 0.15, bg=NAVY, filename: str = None):
    """Logo centered on solid background, square."""
    canvas = Image.new("RGBA", (size, size), (*bg, 255))
    pad = int(size * padding_pct)
    avail = size - 2 * pad
    logo_w_new = avail
    logo_h_new = int(avail / logo_ratio)
    if logo_h_new > avail:
        logo_h_new = avail
        logo_w_new = int(avail * logo_ratio)
    resized = logo_src.resize((logo_w_new, logo_h_new), Image.LANCZOS)
    x = (size - logo_w_new) // 2
    y = (size - logo_h_new) // 2
    canvas.paste(resized, (x, y), resized)
    out = canvas.convert("RGB")
    if filename:
        for d in [OUT_WEB, OUT_ARCHIVE]:
            out.save(d / filename, quality=95)
        print(f"  ✓ {filename} ({size}x{size})")
    return out


def make_cover(width: int, height: int, filename: str, tagline: str = None):
    """Wide cover photo: navy left half, cream right half, logo centered-left."""
    canvas = Image.new("RGB", (width, height), NAVY)
    # Cream stripe on right 40%
    stripe_x = int(width * 0.6)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([stripe_x, 0, width, height], fill=CREAM)
    # Gold accent line at stripe boundary
    draw.rectangle([stripe_x - 4, 0, stripe_x, height], fill=GOLD)

    # Logo in left navy region
    logo_area_w = stripe_x - 40
    logo_area_h = height - 40
    logo_w_new = logo_area_w
    logo_h_new = int(logo_area_w / logo_ratio)
    if logo_h_new > logo_area_h:
        logo_h_new = logo_area_h
        logo_w_new = int(logo_area_h * logo_ratio)
    resized = logo_src.resize((logo_w_new, logo_h_new), Image.LANCZOS)
    # White logo on navy: composite with white fill behind transparent areas
    white_bg = Image.new("RGBA", resized.size, (255, 255, 255, 0))
    logo_on_white = Image.alpha_composite(white_bg, resized)
    x = (stripe_x - logo_w_new) // 2
    y = (height - logo_h_new) // 2
    canvas.paste(logo_on_white.convert("RGB"), (x, y))

    # Tagline in cream area
    if tagline:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", max(12, height // 10))
        except Exception:
            font = ImageFont.load_default()
        tag_x = stripe_x + 20
        tag_y = height // 2 - 30
        draw.text((tag_x, tag_y), tagline, fill=NAVY, font=font)
        slogan_y = tag_y + max(16, height // 8)
        try:
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", max(10, height // 16))
        except Exception:
            small_font = font
        draw.text((tag_x, slogan_y), "dreamstomemories.travel", fill=GOLD, font=small_font)

    for d in [OUT_WEB, OUT_ARCHIVE]:
        canvas.save(d / filename, quality=95)
    print(f"  ✓ {filename} ({width}x{height})")
    return canvas


def make_post_template(size: int = 1080, filename: str = "post_template_1080.jpg"):
    """Square post template: cream bg, logo top, gold border."""
    canvas = Image.new("RGB", (size, size), CREAM)
    draw = ImageDraw.Draw(canvas)
    # Navy border
    border = 12
    draw.rectangle([border, border, size - border, size - border], outline=NAVY, width=border)
    # Gold inner line
    inner = border + 8
    draw.rectangle([inner, inner, size - inner, size - inner], outline=GOLD, width=3)

    # Logo in top third
    logo_area = int(size * 0.55)
    lw = logo_area
    lh = int(logo_area / logo_ratio)
    resized = logo_src.resize((lw, lh), Image.LANCZOS)
    cream_bg = Image.new("RGBA", resized.size, (*CREAM, 255))
    logo_on_cream = Image.alpha_composite(cream_bg, resized)
    x = (size - lw) // 2
    y = int(size * 0.08)
    canvas.paste(logo_on_cream.convert("RGB"), (x, y))

    # Tagline area
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", size // 18)
        small = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", size // 28)
    except Exception:
        font = ImageFont.load_default()
        small = font

    draw.text((size // 2, int(size * 0.72)), "Dreams2Memories Travel", fill=NAVY, font=font, anchor="mm")
    draw.text((size // 2, int(size * 0.80)), "Luxury Cruise Concierge", fill=GOLD, font=small, anchor="mm")
    draw.text((size // 2, int(size * 0.88)), "app.d2mluxury.quest", fill=NAVY, font=small, anchor="mm")

    for d in [OUT_WEB, OUT_ARCHIVE]:
        canvas.save(d / filename, quality=95)
    print(f"  ✓ {filename} ({size}x{size})")


print("\n🎨 D2M Brand Kit Generator")
print("=" * 40)

print("\n→ Profile Images (square, navy bg)")
make_square_profile(320, filename="profile_320.jpg")        # Instagram low-res
make_square_profile(400, filename="profile_400.jpg")        # LinkedIn
make_square_profile(800, filename="profile_800.jpg")        # YouTube
make_square_profile(1080, filename="profile_1080.jpg")      # Instagram/FB hi-res / TikTok
make_square_profile(1600, filename="profile_1600.jpg")      # Master / print

print("\n→ Cover / Banner Photos (wide)")
make_cover(1500, 500,   "cover_twitter_1500x500.jpg",    "Luxury. Personal. Yours.")
make_cover(1584, 396,   "cover_linkedin_1584x396.jpg",   "Luxury. Personal. Yours.")
make_cover(851, 315,    "cover_facebook_851x315.jpg",    "Luxury. Personal. Yours.")
make_cover(2560, 1440,  "cover_youtube_2560x1440.jpg",   "Luxury. Personal. Yours.")
make_cover(1080, 360,   "cover_instagram_story_bg.jpg",  "Luxury. Personal. Yours.")

print("\n→ Post Template")
make_post_template(1080, "post_template_1080.jpg")

# Also copy the best profile to the main static/img for any og:image use
shutil.copy(OUT_WEB / "profile_1080.jpg", Path("/home/john/Thunderbird/app/static/img/og_image.jpg"))
print("\n→ og:image copied to static/img/og_image.jpg")

print(f"\n✅ Brand kit complete.")
print(f"   Web:     {OUT_WEB}")
print(f"   Archive: {OUT_ARCHIVE}")
