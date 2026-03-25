"""
Module 5: Full Pipeline + Batch Mode
Orchestrates: Download -> Transcribe -> Find Clips -> Edit -> Generate Captions
"""

import json
import os
import time
from pathlib import Path

from .downloader import download_video
from .transcriber import transcribe, get_caption_blocks
from .clip_finder import find_clips, find_clips_simple
from .editor import edit_clip, edit_clip_simple
from .caption_generator import generate_captions, generate_captions_simple


PROJECT_ROOT = Path(__file__).parent.parent


def process_single(
    url: str,
    num_clips: int = 5,
    handle: str = "@yourhandle",
    use_ai: bool = True,
    whisper_model: str = "base",
) -> list:
    """
    Full pipeline for a single video URL.
    Returns list of output clip dicts.
    """
    results = []
    start_time = time.time()

    # Step 1: Download
    print("\n" + "=" * 60)
    print("STEP 1: DOWNLOADING VIDEO")
    print("=" * 60)
    video_info = download_video(url)
    video_path = video_info["path"]

    # Step 2: Transcribe
    print("\n" + "=" * 60)
    print("STEP 2: TRANSCRIBING")
    print("=" * 60)
    transcript = transcribe(video_path, model_size=whisper_model)
    caption_blocks = get_caption_blocks(transcript)

    # Step 3: Find best clips
    print("\n" + "=" * 60)
    print("STEP 3: FINDING VIRAL MOMENTS")
    print("=" * 60)
    if use_ai and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            clips = find_clips(transcript, num_clips)
        except Exception as e:
            print(f"[!] AI clip finder failed: {e}")
            clips = find_clips_simple(transcript)
    else:
        clips = find_clips_simple(transcript)

    # Step 4: Edit each clip
    print("\n" + "=" * 60)
    print(f"STEP 4: EDITING {len(clips)} CLIPS")
    print("=" * 60)
    for i, clip_data in enumerate(clips, 1):
        print(f"\n--- Clip {i}/{len(clips)} ---")
        clip_start = clip_data["start"]
        clip_end = clip_data["end"]
        hook = clip_data.get("hook_text", "WAIT FOR IT")
        output_name = f"{Path(video_path).stem}_clip{i}"

        # Get caption blocks for this time range
        clip_captions = [
            b for b in caption_blocks
            if b["start"] >= clip_start and b["end"] <= clip_end
        ]

        try:
            output_path = edit_clip(
                video_path, clip_start, clip_end,
                hook_text=hook,
                caption_blocks=clip_captions,
                handle=handle,
                output_name=output_name,
            )
        except Exception as e:
            print(f"[!] Full edit failed: {e}, trying simple mode...")
            try:
                output_path = edit_clip_simple(
                    video_path, clip_start, clip_end,
                    hook_text=hook,
                    handle=handle,
                    output_name=output_name,
                )
            except Exception as e2:
                print(f"[!] Simple edit also failed: {e2}")
                continue

        # Step 5: Generate captions
        summary = clip_data.get("reason", clip_data.get("text_preview", ""))
        style = clip_data.get("style", "dramatic")

        if use_ai and os.environ.get("ANTHROPIC_API_KEY"):
            captions = generate_captions(hook, summary, style, handle)
        else:
            captions = generate_captions_simple(hook, summary, style, handle)

        result = {
            "clip_number": i,
            "output_path": output_path,
            "start": clip_start,
            "end": clip_end,
            "duration": clip_end - clip_start,
            "hook_text": hook,
            "captions": captions,
            "score": clip_data.get("total_score", clip_data.get("score", 0)),
        }
        results.append(result)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"DONE! Processed {len(results)} clips in {elapsed:.0f}s")
    print(f"{'=' * 60}")

    # Save results manifest
    manifest_path = PROJECT_ROOT / "output" / f"manifest_{int(time.time())}.json"
    with open(manifest_path, "w") as f:
        json.dump({
            "source_url": url,
            "source_title": video_info.get("title", ""),
            "clips": results,
            "processing_time": elapsed,
        }, f, indent=2)
    print(f"[+] Manifest saved: {manifest_path}")

    return results


def process_batch(
    urls: list,
    clips_per_video: int = 5,
    handle: str = "@yourhandle",
    use_ai: bool = True,
    whisper_model: str = "base",
) -> list:
    """
    Batch process multiple video URLs.
    """
    all_results = []
    total = len(urls)

    for i, url in enumerate(urls, 1):
        print(f"\n{'#' * 60}")
        print(f"# VIDEO {i}/{total}: {url[:60]}")
        print(f"{'#' * 60}")

        try:
            results = process_single(
                url, clips_per_video, handle, use_ai, whisper_model
            )
            all_results.extend(results)
        except Exception as e:
            print(f"[!] Failed to process {url}: {e}")
            continue

    print(f"\n{'#' * 60}")
    print(f"# BATCH COMPLETE: {len(all_results)} total clips from {total} videos")
    print(f"{'#' * 60}")

    return all_results
