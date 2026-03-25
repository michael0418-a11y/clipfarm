"""
Module 1: Video Downloader
Downloads videos from YouTube, Twitch, TikTok, Instagram using yt-dlp.
"""

import os
import json
import subprocess
from pathlib import Path


DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)


def download_video(url: str, output_name: str = None) -> dict:
    """
    Download a video from any supported platform.
    Returns dict with file path, title, duration, etc.
    """
    if not output_name:
        # Let yt-dlp generate the name
        output_template = str(DOWNLOADS_DIR / "%(title)s.%(ext)s")
    else:
        output_template = str(DOWNLOADS_DIR / f"{output_name}.%(ext)s")

    # First get video info without downloading
    info_cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        url,
    ]

    print(f"[*] Fetching video info: {url}")
    result = subprocess.run(info_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get video info: {result.stderr}")

    info = json.loads(result.stdout)
    title = info.get("title", "unknown")
    duration = info.get("duration", 0)
    print(f"[*] Found: '{title}' ({duration}s)")

    # Download with best quality up to 1080p
    dl_cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--convert-subs", "srt",
        url,
    ]

    print(f"[*] Downloading: '{title}'...")
    result = subprocess.run(dl_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Try simpler format if merge fails
        dl_cmd_simple = [
            "yt-dlp",
            "-f", "best[height<=1080]",
            "-o", output_template,
            "--no-playlist",
            url,
        ]
        result = subprocess.run(dl_cmd_simple, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Download failed: {result.stderr}")

    # Find the downloaded file
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
    downloaded = None
    for f in DOWNLOADS_DIR.iterdir():
        if f.suffix == ".mp4" and (safe_title[:20].lower() in f.stem.lower() or
                                    (output_name and output_name in f.stem)):
            downloaded = f
            break

    # Fallback: find most recent mp4
    if not downloaded:
        mp4s = sorted(DOWNLOADS_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True)
        if mp4s:
            downloaded = mp4s[0]

    if not downloaded:
        raise FileNotFoundError("Could not locate downloaded file")

    # Check for subtitles
    sub_file = downloaded.with_suffix(".en.srt")
    if not sub_file.exists():
        sub_file = None
        for f in DOWNLOADS_DIR.iterdir():
            if f.suffix == ".srt" and downloaded.stem in f.stem:
                sub_file = f
                break

    print(f"[+] Downloaded: {downloaded}")
    return {
        "path": str(downloaded),
        "title": title,
        "duration": duration,
        "subtitle_file": str(sub_file) if sub_file else None,
        "url": url,
    }


def download_batch(urls: list) -> list:
    """Download multiple videos."""
    results = []
    for i, url in enumerate(urls, 1):
        print(f"\n{'='*50}")
        print(f"[{i}/{len(urls)}] Processing...")
        try:
            result = download_video(url)
            results.append(result)
        except Exception as e:
            print(f"[!] Failed: {e}")
            results.append({"url": url, "error": str(e)})
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <url> [url2] [url3] ...")
        sys.exit(1)

    if len(sys.argv) == 2:
        result = download_video(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        results = download_batch(sys.argv[1:])
        print(json.dumps(results, indent=2))
