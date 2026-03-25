"""
Module 2: AI Clip Finder
Uses transcription + Claude to find the most viral-worthy moments.
Falls back to advanced heuristic scoring when no API key is available.
"""

import json
import os
import re
from pathlib import Path

from src.trends import detect_niche, get_viral_hook, score_moment_virality, get_clip_strategy


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


# ---------------------------------------------------------------------------
# Heuristic helpers for simple (no-API) mode
# ---------------------------------------------------------------------------

SHOCK_WORDS = [
    "crazy", "insane", "unbelievable", "ridiculous", "absurd", "wild",
    "damn", "hell", "crap", "wtf", "omg", "oh my god", "holy",
    "dude", "bro", "no way", "what the", "are you kidding",
    "shut up", "get out", "i swear", "dead serious", "not joking",
]

MONEY_PATTERNS = re.compile(
    r"""
    \$[\d,]+            |   # $100, $1,000,000
    \d+\s*%             |   # 50%
    \bmillion\b         |
    \bbillion\b         |
    \btrillion\b        |
    \bthousand\b        |
    \b\d{4,}\s*dollars?\b|  # 5000 dollars
    \bsix[\s-]?figures?\b|
    \bseven[\s-]?figures?\b|
    \beight[\s-]?figures?\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

SENTENCE_ENDERS = re.compile(r'[.!?]+')


def _silence_score(seg_start: float, seg_end: float, prev_end: float, next_start: float) -> float:
    """Score emphasis pauses before/after a segment. Longer pauses = more emphasis."""
    score = 0.0
    gap_before = seg_start - prev_end if prev_end is not None else 0.0
    gap_after = next_start - seg_end if next_start is not None else 0.0
    # A pause of 0.8s+ before a segment often means the speaker is about to
    # say something important. Cap contribution at 5 points.
    if gap_before > 0.4:
        score += min(gap_before * 3.0, 5.0)
    if gap_after > 0.4:
        score += min(gap_after * 2.0, 4.0)
    return score


def _word_energy_score(text: str, duration: float) -> float:
    """Rapid speech = excitement. Returns 0-10."""
    word_count = len(text.split())
    wps = word_count / max(duration, 0.1)
    # Average conversational English is ~2.5 wps; 4+ is fast/excited
    return min(wps / 3.5, 1.0) * 10.0


def _question_score(text: str) -> float:
    """Questions make great hooks. Returns 0-8."""
    questions = re.findall(r'[^.!?]*\?', text)
    if not questions:
        return 0.0
    score = 3.0  # base for having any question
    # Bonus for strong question openers
    strong_q = re.compile(
        r'\b(do you know|have you ever|what if|would you|can you believe|'
        r'guess what|you know what|want to know|ever wonder)', re.IGNORECASE
    )
    for q in questions:
        if strong_q.search(q):
            score += 2.5
    return min(score, 8.0)


def _money_number_score(text: str) -> float:
    """Money/number mentions are attention magnets. Returns 0-10."""
    hits = MONEY_PATTERNS.findall(text)
    if not hits:
        return 0.0
    return min(len(hits) * 3.0, 10.0)


def _shock_word_score(text: str) -> float:
    """Mild profanity and shock words signal emotional peaks. Returns 0-8."""
    text_lower = text.lower()
    hits = sum(1 for sw in SHOCK_WORDS if sw in text_lower)
    return min(hits * 2.0, 8.0)


def _repetition_score(text: str) -> float:
    """Repeated phrases indicate emphasis. Returns 0-6."""
    words = text.lower().split()
    if len(words) < 6:
        return 0.0
    # Check 2-gram and 3-gram repetitions
    score = 0.0
    for n in (2, 3):
        ngrams = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
        seen = {}
        for ng in ngrams:
            seen[ng] = seen.get(ng, 0) + 1
        repeats = sum(1 for c in seen.values() if c > 1)
        score += repeats * 2.0
    return min(score, 6.0)


def _sentence_boundary_score(text: str) -> float:
    """Clips that start/end on sentence boundaries feel more natural. Returns 0-6."""
    score = 0.0
    stripped = text.strip()
    # Starts with capital letter (sentence start)
    if stripped and stripped[0].isupper():
        score += 3.0
    # Ends with sentence-ending punctuation
    if stripped and stripped[-1] in '.!?':
        score += 3.0
    return score


# ---------------------------------------------------------------------------
# Smart timestamp snapping
# ---------------------------------------------------------------------------

def _collect_all_words(transcript: dict) -> list:
    """Flatten all word-level timestamps from the transcript into a single list."""
    all_words = []
    for seg in transcript.get("segments", []):
        for w in seg.get("words", []):
            all_words.append(w)
    return all_words


def _find_sentence_boundaries(all_words: list) -> list:
    """
    Return a list of word indices that are sentence boundaries
    (the word ends with . ! or ?).
    """
    boundaries = []
    for i, w in enumerate(all_words):
        word_text = w.get("word", "").strip()
        if word_text and word_text[-1] in '.!?':
            boundaries.append(i)
    return boundaries


def _snap_to_boundary(target_time: float, all_words: list, boundaries: list,
                      direction: str = "nearest", max_drift: float = 3.0) -> float:
    """
    Snap a timestamp to the nearest sentence boundary.
    direction: "nearest", "before", or "after"
    max_drift: don't move more than this many seconds from the target
    """
    if not boundaries or not all_words:
        return target_time

    best_time = target_time
    best_dist = max_drift + 1

    for idx in boundaries:
        w = all_words[idx]
        # For start snapping, use the start of the *next* word (sentence begins).
        # For end snapping, use the end of the boundary word (sentence ends).
        if direction == "after":
            # Snap start: find the start of the word right after this boundary
            if idx + 1 < len(all_words):
                candidate = all_words[idx + 1]["start"]
            else:
                candidate = w["end"]
        elif direction == "before":
            candidate = w["end"]
        else:
            candidate = w["end"]

        dist = abs(candidate - target_time)
        if dist < best_dist and dist <= max_drift:
            best_dist = dist
            best_time = candidate

    return best_time


def snap_clip_boundaries(clip: dict, transcript: dict) -> dict:
    """Adjust clip start/end to land on sentence boundaries using word timestamps."""
    all_words = _collect_all_words(transcript)
    if not all_words:
        return clip

    boundaries = _find_sentence_boundaries(all_words)
    if not boundaries:
        return clip

    new_start = _snap_to_boundary(clip["start"], all_words, boundaries,
                                  direction="after", max_drift=3.0)
    new_end = _snap_to_boundary(clip["end"], all_words, boundaries,
                                direction="before", max_drift=3.0)

    # Sanity: keep at least 15s of content
    if new_end - new_start >= 15.0:
        clip["start"] = round(new_start, 2)
        clip["end"] = round(new_end, 2)

    return clip


# ---------------------------------------------------------------------------
# Hook text generator (no API needed)
# ---------------------------------------------------------------------------

def generate_hook_text(text: str) -> str:
    """
    Pick the most interesting short phrase from a segment and format it as
    a dramatic hook overlay. Returns max 6 words, uppercase, with drama
    punctuation.
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return "WAIT FOR IT..."

    best_sentence = ""
    best_score = -1

    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        score = 0
        s_lower = s_clean.lower()
        # Money/numbers are top hooks
        if MONEY_PATTERNS.search(s_clean):
            score += 10
        # Questions are hooks
        if '?' in s_clean:
            score += 5
        # Shock words
        for sw in SHOCK_WORDS:
            if sw in s_lower:
                score += 3
                break
        # Shorter sentences make better hooks
        wc = len(s_clean.split())
        if 3 <= wc <= 8:
            score += 4
        elif wc <= 12:
            score += 2

        if score > best_score:
            best_score = score
            best_sentence = s_clean

    if not best_sentence:
        best_sentence = sentences[0]

    # Trim to max 6 words
    words = best_sentence.split()
    hook = " ".join(words[:6])

    # Clean trailing punctuation, then add drama
    hook = hook.rstrip('.,;:')
    hook = hook.upper()

    # Add dramatic punctuation based on content
    if '?' in best_sentence:
        if not hook.endswith('?'):
            hook += "?!"
    elif MONEY_PATTERNS.search(best_sentence):
        hook += "..."
    elif any(sw in best_sentence.lower() for sw in SHOCK_WORDS[:6]):
        hook += "..."
    else:
        hook += "..."

    return hook


# ---------------------------------------------------------------------------
# Main API-powered clip finder
# ---------------------------------------------------------------------------

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

    # Snap boundaries using word-level timestamps
    for clip in clips:
        snap_clip_boundaries(clip, transcript)

    print(f"[+] Found {len(clips)} viral moments:")
    for i, clip in enumerate(clips, 1):
        print(f"    {i}. [{clip['start']:.1f}s-{clip['end']:.1f}s] "
              f"Score:{clip.get('total_score', '?')} | {clip['hook_text']}")

    return clips


# ---------------------------------------------------------------------------
# Advanced simple (no-API) clip finder
# ---------------------------------------------------------------------------

def find_clips_simple(transcript: dict, min_duration: float = 20, max_duration: float = 50) -> list:
    """
    Advanced clip finder without AI -- uses keyword detection, silence analysis,
    question detection, money/number spotting, shock words, repetition detection,
    speech energy, and sentence boundary scoring.

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

        for j in range(i, len(segments)):
            duration = segments[j]["end"] - segments[i]["start"]
            if duration > max_duration:
                break

            window_text += " " + segments[j]["text"]
            window_end = j

            if duration >= min_duration:
                text_lower = window_text.lower()

                # --- Original keyword score ---
                keyword_hits = sum(1 for kw in viral_keywords if kw in text_lower)
                keyword_score = keyword_hits * 5

                # --- Speech energy / words per second ---
                energy = _word_energy_score(window_text, duration)

                # --- Silence/pause detection (emphasis pauses) ---
                prev_end = segments[i - 1]["end"] if i > 0 else None
                next_start = segments[window_end + 1]["start"] if window_end + 1 < len(segments) else None
                silence = _silence_score(segments[i]["start"], segments[window_end]["end"],
                                         prev_end, next_start)

                # --- Question detection ---
                question = _question_score(window_text)

                # --- Money / number detection ---
                money = _money_number_score(window_text)

                # --- Shock word detection ---
                shock = _shock_word_score(window_text)

                # --- Repetition detection ---
                repetition = _repetition_score(window_text)

                # --- Sentence boundary completeness ---
                boundary = _sentence_boundary_score(window_text)

                # --- Total score ---
                score = (keyword_score + energy + silence + question +
                         money + shock + repetition + boundary)

                # Generate a proper hook text
                hook = generate_hook_text(window_text)

                scored_windows.append({
                    "start": segments[i]["start"],
                    "end": segments[window_end]["end"],
                    "score": round(score, 1),
                    "text_preview": window_text.strip()[:100],
                    "hook_text": hook,
                    "score_breakdown": {
                        "keywords": round(keyword_score, 1),
                        "energy": round(energy, 1),
                        "silence": round(silence, 1),
                        "question": round(question, 1),
                        "money": round(money, 1),
                        "shock": round(shock, 1),
                        "repetition": round(repetition, 1),
                        "boundary": round(boundary, 1),
                    },
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
            # Snap to sentence boundaries
            snap_clip_boundaries(window, transcript)
            selected.append(window)
            if len(selected) >= 5:
                break

    print(f"[+] Found {len(selected)} clips (advanced simple mode):")
    for i, clip in enumerate(selected, 1):
        bd = clip.get("score_breakdown", {})
        detail = " | ".join(f"{k}={v}" for k, v in bd.items() if v > 0)
        print(f"    {i}. [{clip['start']:.1f}s-{clip['end']:.1f}s] "
              f"Score:{clip['score']:.0f} | {clip['hook_text']}")
        print(f"       [{detail}]")

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
