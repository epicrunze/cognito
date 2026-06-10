"""One-off PWA icon generator. Run: uv run --with pillow python scripts/generate_icons.py

Draws the Cognito mark (soft orange radial glow on the app's dark base,
matching the inline SVG favicon in app.html) at PWA sizes.
"""

from pathlib import Path

from PIL import Image, ImageDraw

BG = (17, 17, 16)        # --bg-base #111110
ACCENT = (232, 119, 46)  # #E8772E (favicon gradient)

OUT = Path(__file__).parent.parent / "static" / "icons"
OUT.mkdir(parents=True, exist_ok=True)


def radial_glow(size: int, padding_ratio: float) -> Image.Image:
    img = Image.new("RGB", (size, size), BG)
    # supersample the gradient for smoothness
    ss = 4
    big = size * ss
    glow = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(glow)
    cx = cy = big // 2
    max_r = int(big * (0.5 - padding_ratio))
    for r in range(max_r, 0, -1):
        alpha = int(255 * (1 - r / max_r) ** 1.5)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=alpha)
    glow = glow.resize((size, size), Image.LANCZOS)
    orange = Image.new("RGB", (size, size), ACCENT)
    img.paste(orange, mask=glow)
    return img


def badge(size: int, padding_ratio: float) -> Image.Image:
    """Monochrome notification badge: solid white disc on transparency.

    Android renders status-bar icons from the alpha channel only — every
    opaque pixel becomes white — so a full-colour opaque icon shows as a
    white box. A solid anti-aliased disc reads cleanly at status-bar size
    (a gradient just turns to mush at 24dp). Also referenced from the
    manifest with purpose "monochrome" so WebAPK notifications use it.
    """
    ss = 4
    big = size * ss
    mask = Image.new("L", (big, big), 0)
    draw = ImageDraw.Draw(mask)
    pad = int(big * padding_ratio)
    draw.ellipse([pad, pad, big - pad, big - pad], fill=255)
    alpha_mask = mask.resize((size, size), Image.LANCZOS)
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    white = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    img.paste(white, mask=alpha_mask)
    return img


for name, size, padding in [
    ("icon-192.png", 192, 0.06),
    ("icon-512.png", 512, 0.06),
    ("icon-maskable-192.png", 192, 0.18),  # maskable safe zone
    ("icon-maskable-512.png", 512, 0.18),
    ("apple-touch-icon.png", 180, 0.10),
]:
    radial_glow(size, padding).save(OUT / name)
    print(f"wrote {OUT / name}")

badge(96, 0.12).save(OUT / "badge-96.png")
print(f"wrote {OUT / 'badge-96.png'}")
badge(192, 0.12).save(OUT / "monochrome-192.png")
print(f"wrote {OUT / 'monochrome-192.png'}")
