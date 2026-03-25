"""
Transcription module using faster-whisper.
Generates word-level timestamps for caption sync and clip finding.
"""

import json
from pathlib import Path


def transcribe(video_path: str, model_size: str = "base") -> dict:
    """
    Transcribe a video file using faster-whisper.
    Returns segments with word-level timestamps.
    """
    from faster_whisper import WhisperModel

    print(f"[*] Loading Whisper model '{model_size}'...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"[*] Transcribing: {video_path}")
    segments, info = model.transcribe(
        video_path,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
    )

    result = {
        "language": info.language,
        "duration": info.duration,
        "segments": [],
        "full_text": "",
    }

    all_text = []
    for segment in segments:
        seg_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "words": [],
        }
        for word in segment.words:
            seg_data["words"].append({
                "word": word.word.strip(),
                "start": word.start,
                "end": word.end,
                "probability": round(word.probability, 3),
            })
        result["segments"].append(seg_data)
        all_text.append(segment.text.strip())

    result["full_text"] = " ".join(all_text)
    print(f"[+] Transcribed {len(result['segments'])} segments, {info.duration:.1f}s")

    # Save transcript alongside video
    out_path = Path(video_path).with_suffix(".transcript.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved transcript: {out_path}")

    return result


def get_caption_blocks(transcript: dict, max_words: int = 4, max_duration: float = 2.0) -> list:
    """
    Group words into caption blocks for on-screen display.
    Returns list of {text, start, end} blocks.
    """
    blocks = []
    for segment in transcript["segments"]:
        words = segment["words"]
        i = 0
        while i < len(words):
            block_words = []
            block_start = words[i]["start"]
            block_end = words[i]["end"]

            while i < len(words) and len(block_words) < max_words:
                w = words[i]
                if block_words and (w["start"] - block_start) > max_duration:
                    break
                block_words.append(w["word"])
                block_end = w["end"]
                i += 1

            blocks.append({
                "text": " ".join(block_words),
                "start": block_start,
                "end": block_end,
            })

    return blocks


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <video_path> [model_size]")
        sys.exit(1)
    model = sys.argv[2] if len(sys.argv) > 2 else "base"
    result = transcribe(sys.argv[1], model)
    print(f"\nFull text:\n{result['full_text'][:500]}...")
