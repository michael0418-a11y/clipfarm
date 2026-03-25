import io
import base64
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap

W, H = 1280, 720

PALETTES = [
    {"bg1": (15, 32, 39), "bg2": (32, 58, 67), "accent": (255, 100, 0), "text": (255, 255, 255)},
    {"bg1": (20, 20, 60), "bg2": (60, 20, 80), "accent": (0, 220, 255), "text": (255, 255, 255)},
    {"bg1": (10, 40, 10), "bg2": (0, 80, 40), "accent": (255, 220, 0), "text": (255, 255, 255)},
    {"bg1": (60, 10, 10), "bg2": (100, 30, 10), "accent": (255, 200, 0), "text": (255, 255, 255)},
]

FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REG = r"C:\Windows\Fonts\arial.ttf"


def _gradient(draw: ImageDraw.ImageDraw, c1: tuple, c2: tuple):
    for y in range(H):
        t = y / H
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _generate_ai_background(prompt: str, api_key: str) -> Image.Image | None:
    """Generate a cinematic thumbnail background via Stability AI."""
    try:
        resp = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "authorization": f"Bearer {api_key}",
                "accept": "image/*",
            },
            files={"none": ""},
            data={
                "prompt": f"cinematic dramatic wide shot, {prompt}, dark moody lighting, 4K, no text, photorealistic",
                "negative_prompt": "text, watermark, logo, people, faces, ugly",
                "aspect_ratio": "16:9",
                "output_format": "jpeg",
            },
            timeout=30,
        )
        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content)).resize((W, H))
            # Darken slightly so text is readable
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 100))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay).convert("RGB")
            return img
        print(f"  ⚠️  Stability AI error {resp.status_code}, using gradient fallback")
        return None
    except Exception as e:
        print(f"  ⚠️  Stability AI failed ({e}), using gradient fallback")
        return None


class ThumbnailCreator:
    def __init__(self, stability_key: str = None):
        self.stability_key = stability_key

    def create(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        palette_idx: int = 0,
        ai_prompt: str = None,
    ) -> Path:
        palette = PALETTES[palette_idx % len(PALETTES)]

        # Try AI background first, fall back to gradient
        img = None
        if self.stability_key and ai_prompt:
            img = _generate_ai_background(ai_prompt, self.stability_key)

        if img is None:
            img = Image.new("RGB", (W, H))
            draw = ImageDraw.Draw(img)
            _gradient(draw, palette["bg1"], palette["bg2"])

        draw = ImageDraw.Draw(img)

        # Decorative accent bars
        draw.rectangle([(0, H - 12), (W, H)], fill=palette["accent"])
        draw.rectangle([(0, 0), (W, 8)], fill=palette["accent"])

        # Title text (large, bold, wrapped)
        title_font = _load_font(FONT_BOLD, 100)
        lines = textwrap.wrap(title.upper(), width=14)[:2]

        total_h = len(lines) * 110
        start_y = (H - total_h) // 2 - 40

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=title_font)
            tw = bbox[2] - bbox[0]
            x = (W - tw) // 2
            y = start_y + i * 110
            # Shadow
            draw.text((x + 4, y + 4), line, font=title_font, fill=(0, 0, 0, 160))
            draw.text((x, y), line, font=title_font, fill=palette["text"])

        # Subtitle pill
        if subtitle:
            sub_font = _load_font(FONT_BOLD, 42)
            sub = subtitle.upper()
            bbox = draw.textbbox((0, 0), sub, font=sub_font)
            sw = bbox[2] - bbox[0]
            sx = (W - sw) // 2
            sy = start_y + len(lines) * 110 + 20

            pad = 20
            draw.rounded_rectangle(
                [(sx - pad, sy - 8), (sx + sw + pad, sy + 50)],
                radius=12, fill=palette["accent"]
            )
            draw.text((sx, sy), sub, font=sub_font, fill=(255, 255, 255))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), "JPEG", quality=95)
        return output_path
