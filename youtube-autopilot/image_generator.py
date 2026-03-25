"""
Image generator for video backgrounds.
Primary: Google Gemini API (free — 500 images/day, no credit card)
         This is the same model as Nano Banana Pro.
         Get free key: https://aistudio.google.com/apikey
Fallback: Pexels photos (already have API key)
"""
import requests
import random
import io
from pathlib import Path
from PIL import Image

PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent"


class ImageGenerator:
    def __init__(self, pexels_key: str, gemini_key: str = None):
        self.pexels_key = pexels_key
        self.gemini_key = gemini_key

    def download_sections(self, sections: list, output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        image_files = []
        engine = "Gemini AI" if self.gemini_key else "Pexels"

        for section in sections:
            i = section["section"]
            out_path = output_dir / f"bg_{i:02d}.jpg"

            if self.gemini_key:
                prompt = section.get("image_prompt", "cinematic dramatic scene")
                success = self._gemini(prompt, out_path)
                if success:
                    print(f"  ✓ Image {i}: AI generated [Gemini]")
                    image_files.append(out_path)
                    continue
                print(f"  ⚠ Gemini failed for image {i}, falling back to Pexels")

            # Pexels fallback
            prompt = section.get("image_prompt", "dramatic cinematic scene")
            query = " ".join(prompt.split()[:6])
            success = self._pexels(query, out_path)
            if success:
                print(f"  ✓ Image {i}: '{query}' [{engine if not self.gemini_key else 'Pexels fallback'}]")
            else:
                self._solid_fallback(out_path)
                print(f"  ✗ Image {i}: solid fallback")
            image_files.append(out_path)

        return image_files

    # ── Gemini (Nano Banana) ──────────────────────────────────────────────────

    def _gemini(self, prompt: str, output_path: Path) -> bool:
        try:
            # Enhance prompt for cinematic vertical portrait style
            full_prompt = (
                f"Generate a single cinematic photorealistic image: {prompt}. "
                "Vertical portrait orientation (9:16), dramatic moody lighting, "
                "ultra high detail, 4K quality, no text or watermarks."
            )
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
            }
            resp = requests.post(
                f"{GEMINI_URL}?key={self.gemini_key}",
                headers=headers,
                json=payload,
                timeout=45
            )
            if resp.status_code != 200:
                return False

            data = resp.json()
            for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                if "inlineData" in part:
                    img_bytes = bytes.fromhex("") # placeholder
                    import base64
                    img_bytes = base64.b64decode(part["inlineData"]["data"])
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    img = self._fill_crop(img, 1080, 1920)
                    img.save(output_path, "JPEG", quality=92)
                    return True
        except Exception as e:
            pass
        return False

    # ── Pexels fallback ───────────────────────────────────────────────────────

    def _pexels(self, query: str, output_path: Path) -> bool:
        try:
            resp = requests.get(
                PEXELS_PHOTO_URL,
                headers={"Authorization": self.pexels_key},
                params={"query": query, "per_page": 15, "orientation": "portrait"},
                timeout=15,
            )
            if resp.status_code != 200:
                return False
            photos = resp.json().get("photos", [])
            if not photos:
                return False
            photo = random.choice(photos)
            img_resp = requests.get(photo["src"]["large2x"], timeout=20)
            if img_resp.status_code != 200:
                return False
            img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
            img = self._fill_crop(img, 1080, 1920)
            img.save(output_path, "JPEG", quality=92)
            return True
        except Exception:
            return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _fill_crop(self, img: Image.Image, w: int, h: int) -> Image.Image:
        orig_w, orig_h = img.size
        scale = max(w / orig_w, h / orig_h)
        img = img.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
        left = (img.width - w) // 2
        top = (img.height - h) // 2
        return img.crop((left, top, left + w, top + h))

    def _solid_fallback(self, output_path: Path):
        Image.new("RGB", (1080, 1920), (15, 15, 30)).save(output_path, "JPEG")
