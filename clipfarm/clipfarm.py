#!/usr/bin/env python3
"""
ClipFarm CLI — TikTok Clip Automation Pipeline
Usage:
    python clipfarm.py gui
    python clipfarm.py single <url> [--clips 5] [--handle @you]
    python clipfarm.py batch <url1> <url2> ... [--clips 5]
    python clipfarm.py edit <video> <start> <end> [--hook "TEXT"]
    python clipfarm.py transcribe <video> [--model base]
    python clipfarm.py find-clips <transcript.json> [--clips 5]
    python clipfarm.py stats [--output-dir path]
    python clipfarm.py clean [--downloads] [--all]
    python clipfarm.py config [key] [value]
"""

import argparse
import json
import logging
import shutil
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(PROJECT_ROOT))


def _resolve_output_dir(args) -> Path:
    """Get output directory from args or default."""
    if hasattr(args, "output_dir") and args.output_dir:
        return Path(args.output_dir)
    return None


def _setup_logging(verbose: bool = False):
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _verbose_progress(stage, event, *args):
    """Progress callback that prints detailed info when --verbose is set."""
    parts = [f"[{stage}:{event}]"]
    for a in args:
        parts.append(str(a))
    logging.getLogger("clipfarm").debug(" ".join(parts))


def cmd_single(args):
    from src.pipeline import process_single
    output_dir = _resolve_output_dir(args)
    progress_cb = _verbose_progress if args.verbose else None
    results = process_single(
        url=args.url,
        num_clips=args.clips,
        handle=args.handle,
        use_ai=not args.no_ai,
        whisper_model=args.whisper_model,
        output_dir=output_dir,
        progress_cb=progress_cb,
    )
    print(f"\nGenerated {len(results)} clips:")
    for r in results:
        print(f"  [{r['clip_number']}] {r['output_path']}")
        if r.get("captions", {}).get("captions"):
            print(f"      Caption: {r['captions']['captions'][0]['text']}")


def cmd_batch(args):
    from src.pipeline import process_batch
    output_dir = _resolve_output_dir(args)
    progress_cb = _verbose_progress if args.verbose else None
    results = process_batch(
        urls=args.urls,
        clips_per_video=args.clips,
        handle=args.handle,
        use_ai=not args.no_ai,
        whisper_model=args.whisper_model,
        output_dir=output_dir,
        progress_cb=progress_cb,
        max_concurrent=args.concurrent if hasattr(args, "concurrent") and args.concurrent else None,
    )
    print(f"\nTotal: {len(results)} clips generated")


def cmd_edit(args):
    from src.editor import edit_clip, edit_clip_simple
    try:
        path = edit_clip(
            args.video, args.start, args.end,
            hook_text=args.hook, handle=args.handle,
        )
    except Exception:
        path = edit_clip_simple(
            args.video, args.start, args.end,
            hook_text=args.hook, handle=args.handle,
        )
    print(f"Output: {path}")


def cmd_transcribe(args):
    from src.transcriber import transcribe
    result = transcribe(args.video, model_size=args.model)
    print(f"Segments: {len(result['segments'])}")
    print(f"Duration: {result['duration']:.1f}s")
    print(f"Preview: {result['full_text'][:300]}...")


def cmd_find(args):
    from src.clip_finder import find_clips, find_clips_simple
    with open(args.transcript) as f:
        transcript = json.load(f)
    try:
        clips = find_clips(transcript, args.clips)
    except Exception:
        clips = find_clips_simple(transcript)
    print(json.dumps(clips, indent=2))


def cmd_gui(args):
    from src.gui import launch
    launch()


def cmd_download(args):
    from src.downloader import download_video, download_batch
    if len(args.urls) == 1:
        result = download_video(args.urls[0])
        print(json.dumps(result, indent=2))
    else:
        results = download_batch(args.urls)
        print(json.dumps(results, indent=2))


def cmd_stats(args):
    """Show stats about the output folder."""
    from src.pipeline import get_output_stats
    output_dir = _resolve_output_dir(args)
    stats = get_output_stats(output_dir)

    print(f"\n{'=' * 50}")
    print(f"  ClipFarm Output Stats")
    print(f"{'=' * 50}")
    print(f"  Output folder  : {stats['output_dir']}")
    print(f"  Video folders  : {stats['video_folders']}")
    print(f"  Total clips    : {stats['total_clips']}")
    print(f"  Total size     : {stats['total_size_human']}")

    if stats["videos"]:
        print(f"\n  {'Video':<40} {'Clips':>6} {'Size':>10}")
        print(f"  {'-' * 56}")
        for v in stats["videos"]:
            print(f"  {v['title']:<40} {v['clips']:>6} {v['size']:>10}")

    print(f"{'=' * 50}")


def cmd_clean(args):
    """Delete temp files and optionally downloads."""
    temp_dir = PROJECT_ROOT / "temp"
    downloads_dir = PROJECT_ROOT / "downloads"
    output_dir = PROJECT_ROOT / "output"
    resume_file = output_dir / ".clipfarm_resume.json"

    cleaned = []

    # Always clean temp files
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        cleaned.append(f"  Removed: {temp_dir}")

    # Clean resume state
    if resume_file.exists():
        resume_file.unlink()
        cleaned.append(f"  Removed: {resume_file}")

    # Optionally clean downloads
    if args.downloads or args.all:
        if downloads_dir.exists():
            shutil.rmtree(downloads_dir)
            cleaned.append(f"  Removed: {downloads_dir}")

    # Optionally clean all output
    if args.all:
        if output_dir.exists():
            shutil.rmtree(output_dir)
            cleaned.append(f"  Removed: {output_dir}")

    if cleaned:
        print("Cleaned:")
        for c in cleaned:
            print(c)
    else:
        print("Nothing to clean.")


def cmd_config(args):
    """View or edit settings from CLI."""
    settings_path = PROJECT_ROOT / "config" / "settings.json"

    if not settings_path.exists():
        print(f"[!] Settings file not found: {settings_path}")
        sys.exit(1)

    with open(settings_path, "r") as f:
        settings = json.load(f)

    # No key specified: show all settings
    if not args.key:
        print(json.dumps(settings, indent=2))
        return

    # Parse dotted key path (e.g. "batch.max_concurrent")
    keys = args.key.split(".")

    # Get value: navigate into nested dicts
    if not args.value:
        current = settings
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                print(f"[!] Key not found: {args.key}")
                sys.exit(1)
        if isinstance(current, (dict, list)):
            print(json.dumps(current, indent=2))
        else:
            print(f"{args.key} = {current}")
        return

    # Set value: navigate to parent, then set
    current = settings
    for k in keys[:-1]:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            print(f"[!] Key path not found: {args.key}")
            sys.exit(1)

    final_key = keys[-1]
    if final_key not in current:
        print(f"[!] Key not found: {args.key}")
        sys.exit(1)

    # Auto-detect type from existing value
    old_val = current[final_key]
    new_val = args.value

    if isinstance(old_val, bool):
        new_val = new_val.lower() in ("true", "1", "yes")
    elif isinstance(old_val, int):
        try:
            new_val = int(new_val)
        except ValueError:
            print(f"[!] Expected integer for {args.key}")
            sys.exit(1)
    elif isinstance(old_val, float):
        try:
            new_val = float(new_val)
        except ValueError:
            print(f"[!] Expected number for {args.key}")
            sys.exit(1)
    elif old_val is None:
        # Keep as string or null
        if new_val.lower() == "null":
            new_val = None

    current[final_key] = new_val

    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"Updated: {args.key} = {new_val}")


def main():
    parser = argparse.ArgumentParser(
        description="ClipFarm - TikTok Clip Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clipfarm.py download https://youtube.com/watch?v=xxx
  python clipfarm.py single https://youtube.com/watch?v=xxx --clips 5
  python clipfarm.py batch url1 url2 url3 --clips 3
  python clipfarm.py edit video.mp4 30 65 --hook "HE MADE MILLIONS"
  python clipfarm.py transcribe video.mp4 --model base
  python clipfarm.py find-clips transcript.json --clips 5
  python clipfarm.py stats
  python clipfarm.py clean --downloads
  python clipfarm.py config batch.max_concurrent
  python clipfarm.py config batch.max_concurrent 5
        """,
    )

    # Common args
    parser.add_argument("--handle", default="@yourhandle", help="Your TikTok handle")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI features (no API key needed)")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable detailed logging")
    parser.add_argument("--output-dir", default=None, help="Override output directory")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Download
    p_dl = subparsers.add_parser("download", help="Download video(s)")
    p_dl.add_argument("urls", nargs="+", help="Video URL(s)")

    # Single video pipeline
    p_single = subparsers.add_parser("single", help="Full pipeline for one video")
    p_single.add_argument("url", help="Video URL")
    p_single.add_argument("--clips", type=int, default=5, help="Number of clips to generate")

    # Batch pipeline
    p_batch = subparsers.add_parser("batch", help="Batch process multiple videos")
    p_batch.add_argument("urls", nargs="+", help="Video URLs")
    p_batch.add_argument("--clips", type=int, default=5, help="Clips per video")
    p_batch.add_argument("--concurrent", type=int, default=None,
                         help="Max concurrent workers (default from config)")

    # Edit only
    p_edit = subparsers.add_parser("edit", help="Edit a single clip")
    p_edit.add_argument("video", help="Video file path")
    p_edit.add_argument("start", type=float, help="Start time in seconds")
    p_edit.add_argument("end", type=float, help="End time in seconds")
    p_edit.add_argument("--hook", default="WAIT FOR IT", help="Hook text")

    # Transcribe only
    p_trans = subparsers.add_parser("transcribe", help="Transcribe a video")
    p_trans.add_argument("video", help="Video file path")
    p_trans.add_argument("--model", default="base", help="Whisper model size")

    # Find clips only
    p_find = subparsers.add_parser("find-clips", help="Find viral moments in transcript")
    p_find.add_argument("transcript", help="Transcript JSON file")
    p_find.add_argument("--clips", type=int, default=5, help="Number of clips")

    # Stats command
    subparsers.add_parser("stats", help="Show output folder statistics")

    # Clean command
    p_clean = subparsers.add_parser("clean", help="Delete temp files and optionally downloads")
    p_clean.add_argument("--downloads", action="store_true", help="Also delete downloaded videos")
    p_clean.add_argument("--all", action="store_true", help="Delete everything (temp, downloads, output)")

    # Config command
    p_config = subparsers.add_parser("config", help="View or edit settings")
    p_config.add_argument("key", nargs="?", default=None, help="Setting key (dot notation, e.g. batch.max_concurrent)")
    p_config.add_argument("value", nargs="?", default=None, help="New value to set")

    args = parser.parse_args()

    # Setup logging
    _setup_logging(getattr(args, "verbose", False))

    if not args.command:
        parser.print_help()
        print("\n[!] Specify a command. Run: python clipfarm.py single <url>")
        sys.exit(1)

    commands = {
        "download": cmd_download,
        "single": cmd_single,
        "batch": cmd_batch,
        "edit": cmd_edit,
        "transcribe": cmd_transcribe,
        "find-clips": cmd_find,
        "stats": cmd_stats,
        "clean": cmd_clean,
        "config": cmd_config,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
