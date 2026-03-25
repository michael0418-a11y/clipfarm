"""
Module 2: AI Clip Finder
Uses transcription + Claude to find the most viral-worthy moments.
"""

import json
import os
from pathlib import Path


VIRAL_PROMPT = """You are a viral TikTok clip expert specializing in entrepreneur/luxury/streamer content like @whopio_clips.

Analyze this transcript and find the {num_clips} BEST moments to clip for TikTok. Each clip should be 25-45 seconds.

Score each moment on these criteria (1-10 each):
- HOOK POWER: Does it grab attention in the first 2 seconds?
- EMOTIONAL SPIKE: Strong reaction, shock, hype, or controversy?
- MONEY/SUCCESS TALK: Mentions of money, deals, luxury, grinding?
- QUOTABILITY: Would people share/screenshot this?
- STORY ARC: Does it have a mini beginning-middle-end?
- PUNCHLINE: Does it end on something memorable?

For each clip, provide:
1. Start timestamp (seconds)
2. End timestamp (seconds)
3. Hook text (dramatic 3-6 word text for the first frame, ALL CAPS)
4. Why it's viral-worthy (1 sentence)
5. Suggested caption style (dramatic/funny/inspirational/controversial)
6. Total score (sum of all criteria)

TRANSCRIPT (with timestamps in seconds):
{transcript}

Respond in this exact JSON format:
{{
  "clips": [
    {{
      "start": 45.2,
      "end": 78.5,
      "hook_text": "HE MADE $10M AT 19",
      "reason": "Shocking money revelation with emotional buildup",
      "style": "dramatic",
      "scores": {{
        "hook_power": 9,
        "emotional_spike": 8,
        "money_talk": 10,
        "quotability": 7,
        "story_arc": 6,
        "punchline": 8
      }},
      "total_score": 48
    }}
  ]
}}

Return ONLY valid JSON. Rank clips by total_score descending."""


def find_clips(transcript: dict, num_clips: int = 5, api_key: str = None) -> list:
    """
    Use Claude to find the best viral moments in a transcript.
    """
    import anthropic

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Set ANTHROPIC_API_KEY environment variable or pass api_key")

    # Format transcript with timestamps
    formatted = []
    for seg in transcript["segments"]:
        formatted.append(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
    transcript_text = "\n".join(formatted)

    # Truncate if too long (keep under ~100k chars)
    if len(transcript_text) > 80000:
        transcript_text = transcript_text[:80000] + "\n... [truncated]"

    prompt = VIRAL_PROMPT.format(
        num_clips=num_clips,
        transcript=transcript_text,
    )

    print(f"[*] Asking Claude to find {num_clips} best clips...")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text

    # Parse JSON from response
    try:
        # Try direct parse first
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Extract JSON from markdown code blocks
        import re
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if match:
            data = json.loads(match.group(1))
        else:
            # Try finding JSON object
            match = re.search(r'\{[\s\S]*\}', response_text)
            if match:
                data = json.loads(match.group(0))
            else:
                raise ValueError(f"Could not parse response: {response_text[:500]}")

    clips = data.get("clips", [])
    clips.sort(key=lambda x: x.get("total_score", 0), reverse=True)

    print(f"[+] Found {len(clips)} viral moments:")
    for i, clip in enumerate(clips, 1):
        print(f"    {i}. [{clip['start']:.1f}s-{clip['end']:.1f}s] "
              f"Score:{clip.get('total_score', '?')} | {clip['hook_text']}")

    return clips


def find_clips_simple(transcript: dict, min_duration: float = 20, max_duration: float = 50) -> list:
    """
    Simple clip finder without AI — uses keyword detection and energy analysis.
    Good fallback when no API key is available.
    """
    viral_keywords = [
        "million", "billion", "money", "rich", "luxury", "lambo", "ferrari",
        "hustle", "grind", "success", "failed", "broke", "crazy", "insane",
        "secret", "nobody", "everyone", "trust me", "listen", "the truth",
        "i made", "i lost", "i spent", "no way", "oh my god", "what the",
        "literally", "actually", "honestly", "believe", "changed my life",
    ]

    segments = transcript["segments"]
    scored_windows = []

    # Sliding window approach
    for i in range(len(segments)):
        window_text = ""
        window_end = 0
        score = 0

        for j in range(i, len(segments)):
            duration = segments[j]["end"] - segments[i]["start"]
            if duration > max_duration:
                break

            window_text += " " + segments[j]["text"]
            window_end = j

            if duration >= min_duration:
                # Score this window
                text_lower = window_text.lower()
                keyword_hits = sum(1 for kw in viral_keywords if kw in text_lower)
                word_count = len(window_text.split())
                words_per_sec = word_count / max(duration, 1)

                # Higher speech rate = more energy
                energy_score = min(words_per_sec / 3.0, 1.0) * 10

                score = keyword_hits * 5 + energy_score

                scored_windows.append({
                    "start": segments[i]["start"],
                    "end": segments[window_end]["end"],
                    "score": score,
                    "text_preview": window_text.strip()[:100],
                    "hook_text": window_text.strip().split(".")[0][:40].upper(),
                })

    # Remove overlapping windows, keep highest scored
    scored_windows.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for window in scored_windows:
        overlaps = False
        for sel in selected:
            if not (window["end"] < sel["start"] or window["start"] > sel["end"]):
                overlaps = True
                break
        if not overlaps:
            selected.append(window)
            if len(selected) >= 5:
                break

    print(f"[+] Found {len(selected)} clips (simple mode):")
    for i, clip in enumerate(selected, 1):
        print(f"    {i}. [{clip['start']:.1f}s-{clip['end']:.1f}s] Score:{clip['score']:.0f}")

    return selected


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python clip_finder.py <transcript.json> [num_clips]")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        transcript = json.load(f)

    num = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    try:
        clips = find_clips(transcript, num)
    except Exception as e:
        print(f"[!] AI clip finder failed ({e}), using simple mode...")
        clips = find_clips_simple(transcript)

    print(json.dumps(clips, indent=2))
