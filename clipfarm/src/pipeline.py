"""
Module 5: Full Pipeline + Batch Mode
Orchestrates: Download -> Transcribe -> Find Clips -> Edit -> Generate Captions
Supports concurrent batch processing, progress tracking, and resume.
"""

import json
import os
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Callable, Optional

from .downloader import download_video
from .transcriber import transcribe, get_caption_blocks
from .clip_finder import find_clips, find_clips_simple
from .editor import edit_clip, edit_clip_simple
from .caption_generator import generate_captions, generate_captions_simple


PROJECT_ROOT = Path(__file__).parent.parent
logger = logging.getLogger("clipfarm")

# Type alias for progress callback
# callback(stage: str, event: str, *args)
ProgressCallback = Callable[..., None]


def _sanitize_title(title: str) -> str:
    """Create a filesystem-safe folder name from a video title."""
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = safe.strip('. ')
    safe = safe[:80]  # Limit length
    return safe or "untitled"


def _load_settings() -> dict:
    """Load settings from config/settings.json."""
    settings_path = PROJECT_ROOT / "config" / "settings.json"
    if settings_path.exists():
        with open(settings_path, "r") as f:
            return json.load(f)
    return {}


def _get_output_dir(video_title: str, output_base: Optional[Path] = None) -> Path:
    """Get organized output directory for a video's clips."""
    base = output_base or (PROJECT_ROOT / "output" / "clips")
    folder = base / _sanitize_title(video_title)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _load_resume_state(resume_path: Path) -> dict:
    """Load resume state from a JSON file."""
    if resume_path.exists():
        with open(resume_path, "r") as f:
            return json.load(f)
    return {"processed_urls": [], "results": []}


def _save_resume_state(resume_path: Path, state: dict):
    """Save resume state to a JSON file."""
    resume_path.parent.mkdir(parents=True, exist_ok=True)
    with open(resume_path, "w") as f:
        json.dump(state, f, indent=2)


def _dir_size_bytes(path: Path) -> int:
    """Calculate total size of all files in a directory tree."""
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_output_stats(output_dir: Optional[Path] = None) -> dict:
    """
    Get statistics about the output folder.
    Returns dict with total_clips, total_size, videos, etc.
    """
    base = output_dir or (PROJECT_ROOT / "output" / "clips")
    stats = {
        "output_dir": str(base),
        "total_clips": 0,
        "total_size_bytes": 0,
        "total_size_human": "0 B",
        "video_folders": 0,
        "videos": [],
    }

    if not base.exists():
        return stats

    for folder in sorted(base.iterdir()):
        if not folder.is_dir():
            continue
        clips = list(folder.glob("clip_*.mp4"))
        folder_size = _dir_size_bytes(folder)
        stats["video_folders"] += 1
        stats["total_clips"] += len(clips)
        stats["total_size_bytes"] += folder_size
        stats["videos"].append({
            "title": folder.name,
            "clips": len(clips),
            "size": _format_size(folder_size),
        })

    stats["total_size_human"] = _format_size(stats["total_size_bytes"])
    return stats


def process_single(
    url: str,
    num_clips: int = 5,
    handle: str = "@yourhandle",
    use_ai: bool = True,
    whisper_model: str = "base",
    output_dir: Optional[Path] = None,
    progress_cb: Optional[ProgressCallback] = None,
) -> list:
    """
    Full pipeline for a single video URL.
    Returns list of output clip dicts.

    Args:
        url: Video URL to process.
        num_clips: Number of clips to extract.
        handle: TikTok handle for watermark.
        use_ai: Whether to use AI features.
        whisper_model: Whisper model size.
        output_dir: Override base output directory.
        progress_cb: Optional callback for progress events.
    """
    results = []
    start_time = time.time()

    def emit(stage, event, *args):
        if progress_cb:
            try:
                progress_cb(stage, event, *args)
            except Exception:
                pass

    # Step 1: Download
    print("\n" + "=" * 60)
    print("STEP 1: DOWNLOADING VIDEO")
    print("=" * 60)
    emit("download", "start", url)
    video_info = download_video(url)
    video_path = video_info["path"]
    video_title = video_info.get("title", Path(video_path).stem)
    emit("download", "done", video_path)

    # Organize output by source
    clip_dir = _get_output_dir(video_title, output_dir)

    # Step 2: Transcribe
    print("\n" + "=" * 60)
    print("STEP 2: TRANSCRIBING")
    print("=" * 60)
    emit("transcribe", "start", video_path)
    transcript = transcribe(video_path, model_size=whisper_model)
    caption_blocks = get_caption_blocks(transcript)
    emit("transcribe", "done", len(transcript.get("segments", [])))

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
    total_clips = len(clips)
    for i, clip_data in enumerate(clips, 1):
        print(f"\n--- Clip {i}/{total_clips} ---")
        emit("clip", "start", i, total_clips)
        clip_start = clip_data["start"]
        clip_end = clip_data["end"]
        hook = clip_data.get("hook_text", "WAIT FOR IT")
        output_name = f"clip_{i:03d}"

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
                output_dir=str(clip_dir),
            )
        except Exception as e:
            print(f"[!] Full edit failed: {e}, trying simple mode...")
            try:
                output_path = edit_clip_simple(
                    video_path, clip_start, clip_end,
                    hook_text=hook,
                    handle=handle,
                    output_name=output_name,
                    output_dir=str(clip_dir),
                )
            except Exception as e2:
                print(f"[!] Simple edit also failed: {e2}")
                emit("clip", "error", i, str(e2))
                continue

        emit("clip", "done", i, output_path)

        # Step 5: Generate captions
        summary = clip_data.get("reason", clip_data.get("text_preview", ""))
        style = clip_data.get("style", "dramatic")

        if use_ai and os.environ.get("ANTHROPIC_API_KEY"):
            captions = generate_captions(hook, summary, style, handle)
        else:
            captions = generate_captions_simple(hook, summary, style, handle)

        emit("caption", "done", i)

        result = {
            "clip_number": i,
            "output_path": str(output_path),
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

    # Save captions JSON in clip directory
    captions_path = clip_dir / "captions.json"
    with open(captions_path, "w") as f:
        json.dump(
            [{"clip_number": r["clip_number"], "captions": r["captions"]} for r in results],
            f, indent=2,
        )

    # Save manifest in clip directory
    manifest_path = clip_dir / "manifest.json"
    manifest_data = {
        "source_url": url,
        "source_title": video_title,
        "clips": results,
        "processing_time": elapsed,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"[+] Manifest saved: {manifest_path}")

    return results


def process_batch(
    urls: list,
    clips_per_video: int = 5,
    handle: str = "@yourhandle",
    use_ai: bool = True,
    whisper_model: str = "base",
    max_concurrent: Optional[int] = None,
    output_dir: Optional[Path] = None,
    progress_cb: Optional[ProgressCallback] = None,
    resume: bool = True,
) -> list:
    """
    Batch process multiple video URLs with concurrent execution.

    Args:
        urls: List of video URLs.
        clips_per_video: Number of clips per video.
        handle: TikTok handle.
        use_ai: Whether to use AI features.
        whisper_model: Whisper model size.
        max_concurrent: Max parallel workers (default from config or 3).
        output_dir: Override base output directory.
        progress_cb: Optional callback for progress events.
        resume: Whether to skip already-processed URLs.
    """
    # Load settings for defaults
    settings = _load_settings()
    batch_settings = settings.get("batch", {})
    if max_concurrent is None:
        max_concurrent = batch_settings.get("max_concurrent", 3)

    total = len(urls)
    batch_start = time.time()

    # Resume support
    resume_path = (output_dir or PROJECT_ROOT / "output") / ".clipfarm_resume.json"
    resume_state = _load_resume_state(resume_path) if resume else {"processed_urls": [], "results": []}

    # Filter out already-processed URLs
    pending_urls = [u for u in urls if u not in resume_state["processed_urls"]]
    if len(pending_urls) < total:
        skipped = total - len(pending_urls)
        print(f"[*] Resuming: skipping {skipped} already-processed video(s)")

    all_results = list(resume_state.get("results", []))
    results_lock = Lock()

    def emit(stage, event, *args):
        if progress_cb:
            try:
                progress_cb(stage, event, *args)
            except Exception:
                pass

    def _process_one(url_index_tuple):
        """Worker function for a single video in the batch."""
        url, idx = url_index_tuple
        emit("batch", "progress", idx, total)
        print(f"\n{'#' * 60}")
        print(f"# VIDEO {idx}/{total}: {url[:60]}")
        print(f"{'#' * 60}")

        try:
            results = process_single(
                url, clips_per_video, handle, use_ai, whisper_model,
                output_dir=output_dir,
                progress_cb=progress_cb,
            )
            with results_lock:
                all_results.extend(results)
                resume_state["processed_urls"].append(url)
                resume_state["results"] = all_results
                _save_resume_state(resume_path, resume_state)
            return results
        except Exception as e:
            print(f"[!] Failed to process {url}: {e}")
            logger.exception("Failed to process %s", url)
            # Still mark as processed to avoid infinite retry loops
            with results_lock:
                resume_state["processed_urls"].append(url)
                _save_resume_state(resume_path, resume_state)
            return []

    # Build indexed list for pending URLs only, keeping correct display index
    url_index_pairs = []
    for url in pending_urls:
        original_idx = urls.index(url) + 1
        url_index_pairs.append((url, original_idx))

    # Concurrent execution
    if max_concurrent > 1 and len(url_index_pairs) > 1:
        print(f"[*] Processing {len(url_index_pairs)} video(s) with {max_concurrent} workers")
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {
                executor.submit(_process_one, pair): pair
                for pair in url_index_pairs
            }
            for future in as_completed(futures):
                pair = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"[!] Worker error for {pair[0]}: {e}")
    else:
        # Sequential fallback
        for pair in url_index_pairs:
            _process_one(pair)

    batch_elapsed = time.time() - batch_start

    # Clean up resume file on success
    if resume_path.exists():
        try:
            resume_path.unlink()
        except OSError:
            pass

    # Print stats summary
    _print_batch_summary(all_results, total, batch_elapsed, output_dir)

    return all_results


def _print_batch_summary(results: list, total_videos: int, elapsed: float, output_dir: Optional[Path] = None):
    """Print a summary of batch processing results."""
    base = output_dir or (PROJECT_ROOT / "output" / "clips")
    total_clips = len(results)
    durations = [r.get("duration", 0) for r in results if r.get("duration")]
    avg_duration = sum(durations) / len(durations) if durations else 0
    folder_size = _dir_size_bytes(base)

    print(f"\n{'#' * 60}")
    print(f"# BATCH COMPLETE")
    print(f"{'#' * 60}")
    print(f"  Videos processed : {total_videos}")
    print(f"  Total clips      : {total_clips}")
    print(f"  Processing time  : {elapsed:.0f}s ({elapsed / 60:.1f}m)")
    print(f"  Avg clip duration: {avg_duration:.1f}s")
    print(f"  Output size      : {_format_size(folder_size)}")
    print(f"  Output folder    : {base}")
    print(f"{'#' * 60}")
