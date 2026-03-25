#!/usr/bin/env python3
"""
YouTube Autopilot
-----------------
One command → full YouTube video (script, voiceover, stock footage, thumbnail, upload).
All free. Powered by Groq + Edge-TTS (or ElevenLabs) + Pexels + FFmpeg.
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Fix emoji printing on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

from config import Config
from content_generator import ContentGenerator
from tts_generator import TTSGenerator
from image_generator import ImageGenerator
from video_creator import VideoCreator
from thumbnail_creator import ThumbnailCreator
from youtube_uploader import YouTubeUploader


def run(topic: str | None = None, dry_run: bool = False, palette: int = 0):
    config = Config()
    need_yt = not dry_run
    if not config.validate(need_youtube=need_yt):
        sys.exit(1)

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Generate content ──────────────────────────────────────────────────
    print("\n🧠  Generating content with Groq...")
    gen = ContentGenerator(config.GROQ_API_KEY)

    if not topic:
        print("   Picking a topic for your niche...")
        topic = gen.pick_topic(config.CHANNEL_NICHE)
        print(f"   Topic: {topic}")

    content = gen.generate(topic, config.CHANNEL_NICHE)
    print(f"   Title : {content['title']}")

    out_dir = config.OUTPUT_DIR / content["safe_title"]
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "content.json", "w") as f:
        json.dump(content, f, indent=2)

    # ── 2. Text-to-speech ────────────────────────────────────────────────────
    el_key = config.ELEVENLABS_API_KEY or None
    engine = "ElevenLabs" if el_key else "Edge-TTS"
    print(f"\n🎤  Generating voiceover [{engine}]...")
    tts = TTSGenerator(config.TTS_VOICE, elevenlabs_key=el_key)
    audio_files, timing_files = tts.generate_sections(content["script"], out_dir / "audio")

    # ── 3. Background images ─────────────────────────────────────────────────
    print("\n🎨  Fetching background images...")
    img_gen = ImageGenerator(config.PEXELS_API_KEY)
    image_files = img_gen.download_sections(content["script"], out_dir / "images")

    # ── 4. Assemble video ────────────────────────────────────────────────────
    bgm_path = Path(config.BGM_PATH) if config.BGM_PATH else None
    if bgm_path and bgm_path.exists():
        print(f"\n🎞️  Assembling video [+BGM: {bgm_path.name}]...")
    else:
        print("\n🎞️  Assembling video...")
        bgm_path = None

    creator = VideoCreator()
    video_path = creator.create(
        sections=content["script"],
        audio_files=audio_files,
        image_files=image_files,
        timing_files=timing_files,
        output_path=out_dir / "final_video.mp4",
        bgm_path=bgm_path,
    )
    print(f"   Saved: {video_path}")

    # ── 5. Create thumbnail ──────────────────────────────────────────────────
    stab_key = config.STABILITY_API_KEY or None
    engine_label = "Stability AI" if stab_key else "Pillow"
    print(f"\n🖼️  Creating thumbnail [{engine_label}]...")
    thumb = ThumbnailCreator(stability_key=stab_key)
    thumbnail_path = thumb.create(
        title=content["thumbnail_text"],
        subtitle=content["thumbnail_subtitle"],
        output_path=out_dir / "thumbnail.jpg",
        palette_idx=palette,
        ai_prompt=content["title"],  # use the video title as the image generation prompt
    )
    print(f"   Saved: {thumbnail_path}")

    if dry_run:
        print(f"\n✅  Dry run complete — no upload.")
        print(f"   Output folder: {out_dir}")
        return

    # ── 6. Upload to YouTube ─────────────────────────────────────────────────
    print("\n📤  Uploading to YouTube...")
    uploader = YouTubeUploader(config.YOUTUBE_CLIENT_SECRETS)
    video_id = uploader.upload(
        video_path=video_path,
        thumbnail_path=thumbnail_path,
        title=content["title"],
        description=content["description"],
        tags=content["tags"],
    )
    print(f"\n🎉  Published! https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Autopilot — one prompt, one video")
    parser.add_argument("--topic", type=str, default=None, help="Video topic (auto-picked if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--palette", type=int, default=0, help="Thumbnail color palette 0-3")
    parser.add_argument("--analytics", action="store_true", help="Show channel analytics report")
    args = parser.parse_args()

    if args.analytics:
        from analytics import print_report
        print_report()
    else:
        run(topic=args.topic, dry_run=args.dry_run, palette=args.palette)
