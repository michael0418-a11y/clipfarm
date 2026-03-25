#!/usr/bin/env python3
"""
ClipFarm CLI — TikTok Clip Automation Pipeline
Usage:
    python clipfarm.py single <url> [--clips 5] [--handle @you]
    python clipfarm.py batch <url1> <url2> ... [--clips 5]
    python clipfarm.py edit <video> <start> <end> [--hook "TEXT"]
    python clipfarm.py transcribe <video> [--model base]
    python clipfarm.py find-clips <transcript.json> [--clips 5]
"""

import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_single(args):
    from src.pipeline import process_single
    results = process_single(
        url=args.url,
        num_clips=args.clips,
        handle=args.handle,
        use_ai=not args.no_ai,
        whisper_model=args.whisper_model,
    )
    print(f"\nGenerated {len(results)} clips:")
    for r in results:
        print(f"  [{r['clip_number']}] {r['output_path']}")
        if r.get("captions", {}).get("captions"):
            print(f"      Caption: {r['captions']['captions'][0]['text']}")


def cmd_batch(args):
    from src.pipeline import process_batch
    results = process_batch(
        urls=args.urls,
        clips_per_video=args.clips,
        handle=args.handle,
        use_ai=not args.no_ai,
        whisper_model=args.whisper_model,
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


def cmd_download(args):
    from src.downloader import download_video, download_batch
    if len(args.urls) == 1:
        result = download_video(args.urls[0])
        print(json.dumps(result, indent=2))
    else:
        results = download_batch(args.urls)
        print(json.dumps(results, indent=2))


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
        """,
    )

    # Common args
    parser.add_argument("--handle", default="@yourhandle", help="Your TikTok handle")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI features (no API key needed)")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size")

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

    args = parser.parse_args()

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
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
