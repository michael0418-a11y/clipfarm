import requests
import random
from pathlib import Path


class PexelsDownloader:
    BASE_URL = "https://api.pexels.com/videos/search"

    def __init__(self, api_key: str):
        self.headers = {"Authorization": api_key}
        self._cache: dict[str, Path] = {}

    def _search(self, query: str) -> dict | None:
        """Search Pexels for a video matching query. Returns best video dict or None."""
        for attempt_query in [query, query.split()[0], "nature landscape"]:
            try:
                resp = requests.get(
                    self.BASE_URL,
                    headers=self.headers,
                    params={"query": attempt_query, "per_page": 10, "orientation": "landscape"},
                    timeout=15
                )
                resp.raise_for_status()
                videos = resp.json().get("videos", [])
                if videos:
                    return random.choice(videos[:5])
            except Exception:
                continue
        return None

    def _download(self, video: dict, output_path: Path) -> Path:
        """Download the best available HD file."""
        # Find best quality <= 1280 width
        files = sorted(video["video_files"], key=lambda f: f.get("width", 0), reverse=True)
        chosen = None
        for f in files:
            if f.get("width", 9999) <= 1280 and f.get("file_type") == "video/mp4":
                chosen = f
                break
        if not chosen:
            chosen = files[0]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(chosen["link"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    f.write(chunk)
        return output_path

    def download_sections(self, script: list, output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        clip_files = []
        for section in script:
            keywords = section["visual_keywords"]
            query = " ".join(keywords[:2])
            out = output_dir / f"clip_{section['section']:02d}.mp4"

            if query in self._cache and self._cache[query].exists():
                clip_files.append(self._cache[query])
                print(f"  ✓ Clip {section['section']} (cached)")
                continue

            video = self._search(query)
            if video:
                self._download(video, out)
                self._cache[query] = out
                print(f"  ✓ Clip {section['section']}: '{query}'")
            else:
                # Fallback: reuse previous clip or mark as None
                out = clip_files[-1] if clip_files else None
                print(f"  ⚠ Clip {section['section']}: no result, reusing previous")

            clip_files.append(out)
        return clip_files
