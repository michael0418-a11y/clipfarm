"""
Module 4: Caption & Hashtag Generator
Generates TikTok captions and hashtags using Claude.
Falls back to template-based generation with transcript-aware hashtags.
"""

import json
import os
import re
import random

from src.trends import get_trending_hashtags, get_niche, get_viral_hook


CAPTION_PROMPT = """You are a TikTok growth expert. Generate 3 caption variations and hashtags for a clip.

CLIP CONTEXT:
- Hook text: {hook_text}
- Content summary: {summary}
- Style: {style}
- Creator handle: {handle}

Generate:
1. Three caption variations (each under 150 chars):
   - Version A: Dramatic/clickbait style
   - Version B: Relatable/question style
   - Version C: Controversial/hot take style
2. 20 hashtags: mix of viral (#fyp #viral #foryou) + niche (#entrepreneur #luxury #motivation)

Respond in JSON:
{{
  "captions": [
    {{"style": "dramatic", "text": "..."}},
    {{"style": "relatable", "text": "..."}},
    {{"style": "controversial", "text": "..."}}
  ],
  "hashtags": ["#fyp", "#viral", ...]
}}

Return ONLY valid JSON."""


# ---------------------------------------------------------------------------
# Niche detection keywords
# ---------------------------------------------------------------------------

NICHE_KEYWORDS = {
    "entrepreneur": [
        "business", "startup", "company", "ceo", "founder", "revenue",
        "profit", "invest", "deal", "client", "scale", "exit", "ipo",
        "venture", "capital", "equity",
    ],
    "finance": [
        "stock", "market", "crypto", "bitcoin", "trading", "portfolio",
        "dividend", "interest", "bank", "debt", "credit", "loan", "tax",
        "inflation", "recession",
    ],
    "motivation": [
        "grind", "hustle", "discipline", "mindset", "wake up", "sacrifice",
        "success", "failure", "give up", "keep going", "never quit",
        "dream", "goal", "vision", "believe",
    ],
    "gaming": [
        "game", "stream", "twitch", "play", "controller", "pc", "console",
        "win", "lose", "rank", "lobby", "clutch", "squad", "raid", "loot",
    ],
    "comedy": [
        "funny", "joke", "laugh", "lol", "lmao", "haha", "bruh", "sus",
        "cap", "no cap", "dead", "crying", "skit", "prank",
    ],
    "luxury": [
        "million", "billion", "lambo", "ferrari", "rolex", "gucci",
        "mansion", "yacht", "private jet", "rich", "wealthy", "expensive",
        "designer", "penthouse",
    ],
    "fitness": [
        "workout", "gym", "lift", "muscle", "protein", "cardio", "reps",
        "sets", "gains", "shredded", "bulk", "cut", "diet", "calories",
    ],
}

NICHE_HASHTAGS = {
    "entrepreneur": ["#entrepreneur", "#business", "#startup", "#ceo", "#founder", "#hustlehard"],
    "finance": ["#finance", "#investing", "#crypto", "#stocks", "#money", "#wealthbuilding"],
    "motivation": ["#motivation", "#mindset", "#grindmode", "#nevergiveup", "#discipline", "#success"],
    "gaming": ["#gaming", "#gamer", "#twitch", "#streamer", "#gameplay", "#clutch"],
    "comedy": ["#comedy", "#funny", "#meme", "#humor", "#lol", "#skit"],
    "luxury": ["#luxury", "#millionaire", "#richlife", "#lifestyle", "#wealth", "#flexing"],
    "fitness": ["#fitness", "#gym", "#workout", "#gains", "#fitnessmotivation", "#shredded"],
}

VIRAL_BASE_HASHTAGS = [
    "#fyp", "#foryou", "#foryoupage", "#viral", "#trending",
    "#blowthisup", "#xyzbca", "#explore", "#viralvideo",
]


# ---------------------------------------------------------------------------
# Transcript analysis helpers (regex only, no external NLP)
# ---------------------------------------------------------------------------

def _extract_nouns_simple(text: str) -> list:
    """
    Extract likely nouns/topics from text using simple heuristics.
    Looks for capitalized words (proper nouns) and common noun patterns.
    No external NLP library needed.
    """
    # Grab capitalized words that are not at sentence starts
    words = text.split()
    nouns = set()

    for i, word in enumerate(words):
        clean = re.sub(r'[^a-zA-Z]', '', word)
        if not clean or len(clean) < 3:
            continue
        # Proper nouns: capitalized and not first word of a sentence
        if clean[0].isupper() and i > 0:
            prev = words[i - 1].strip()
            if prev and prev[-1] not in '.!?':
                nouns.add(clean.lower())

    # Also grab words that appear multiple times (likely topics)
    word_freq = {}
    for w in words:
        clean = re.sub(r'[^a-zA-Z]', '', w).lower()
        if len(clean) >= 4:
            word_freq[clean] = word_freq.get(clean, 0) + 1
    for w, count in word_freq.items():
        if count >= 3:
            nouns.add(w)

    # Filter out extremely common English words
    stop_words = {
        "that", "this", "with", "from", "have", "they", "been", "were",
        "said", "each", "which", "their", "will", "about", "would", "there",
        "could", "other", "than", "then", "them", "these", "some", "into",
        "just", "like", "what", "when", "make", "know", "take", "come",
        "more", "want", "look", "very", "also", "back", "after", "year",
        "because", "really", "going", "actually", "literally", "think",
        "thing", "things", "right", "well", "even", "still", "here",
    }
    nouns = {n for n in nouns if n not in stop_words}

    return list(nouns)[:10]


def _detect_niches(text: str) -> list:
    """Detect content niches from transcript text. Returns sorted list of (niche, score)."""
    text_lower = text.lower()
    scores = {}
    for niche, keywords in NICHE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > 0:
            scores[niche] = hits

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


def _extract_key_quote(text: str, max_words: int = 12) -> str:
    """
    Pull the most interesting short quote from a transcript chunk.
    Prefers sentences with money, questions, or shock words.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return ""

    money_pat = re.compile(
        r'\$[\d,]+|\d+\s*%|\bmillion\b|\bbillion\b', re.IGNORECASE
    )
    shock = ["crazy", "insane", "wild", "unbelievable", "no way", "oh my god"]

    best = ""
    best_score = -1

    for s in sentences:
        s = s.strip()
        wc = len(s.split())
        if wc < 3 or wc > max_words + 4:
            continue
        score = 0
        if money_pat.search(s):
            score += 5
        if '?' in s:
            score += 4
        s_lower = s.lower()
        for sw in shock:
            if sw in s_lower:
                score += 3
                break
        # Prefer shorter, punchier quotes
        if wc <= max_words:
            score += 2

        if score > best_score:
            best_score = score
            best = s

    if not best and sentences:
        best = sentences[0]

    # Trim to max words
    words = best.split()[:max_words]
    return " ".join(words)


# ---------------------------------------------------------------------------
# Template-based caption generation
# ---------------------------------------------------------------------------

# Each template category has multiple variants so consecutive clips feel different.
CAPTION_TEMPLATES = {
    "question": [
        'Would you do this? "{quote}" {handle}',
        'How is this even real? {handle}',
        'Can someone explain this?? {handle}',
        'Did they really just say this? {handle}',
        'Why is nobody talking about this? {handle}',
    ],
    "dramatic": [
        '"{quote}"... wait for it {handle}',
        'This changes everything. {handle}',
        'I was NOT ready for this {handle}',
        'This hit different {handle}',
        'Pay attention to this part {handle}',
    ],
    "controversial": [
        'Nobody wants you to know this... {handle}',
        'This is why most people stay broke {handle}',
        'Agree or disagree? {handle}',
        'Hot take: they are 100% right {handle}',
        'The hard truth nobody talks about {handle}',
    ],
    "story_tease": [
        'Wait till you hear what happened next {handle}',
        'The ending is wild {handle}',
        'Story time... and it gets CRAZY {handle}',
        'This story is unreal {handle}',
        'You will not believe how this ends {handle}',
    ],
}

# Global rotation counter per style to avoid repeating templates
_template_counters = {}


def _pick_template(style: str, quote: str, handle: str) -> str:
    """Pick the next template in rotation for the given style."""
    templates = CAPTION_TEMPLATES.get(style, CAPTION_TEMPLATES["dramatic"])
    idx = _template_counters.get(style, 0)
    template = templates[idx % len(templates)]
    _template_counters[style] = idx + 1
    return template.format(quote=quote, handle=handle)


# ---------------------------------------------------------------------------
# Smart hashtag generation
# ---------------------------------------------------------------------------

def _generate_smart_hashtags(text: str, count: int = 20) -> list:
    """
    Generate hashtags based on actual transcript content.
    Mixes viral base tags, niche tags, and topic-extracted tags.
    """
    tags = list(VIRAL_BASE_HASHTAGS)  # start with viral base

    # Add niche-specific hashtags
    niches = _detect_niches(text)
    for niche, _score in niches[:3]:
        niche_tags = NICHE_HASHTAGS.get(niche, [])
        for t in niche_tags:
            if t not in tags:
                tags.append(t)

    # Add topic-based hashtags extracted from the text
    nouns = _extract_nouns_simple(text)
    for noun in nouns:
        tag = "#" + noun.lower().replace(" ", "")
        if tag not in tags and len(tag) > 3:
            tags.append(tag)

    # Deduplicate and trim
    seen = set()
    unique = []
    for t in tags:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            unique.append(t)

    # Pad if short
    filler = ["#clips", "#highlights", "#trending", "#blowup", "#mustwatch",
              "#relatable", "#real", "#facts", "#truth", "#wow"]
    for f in filler:
        if len(unique) >= count:
            break
        if f.lower() not in seen:
            unique.append(f)

    return unique[:count]


# ---------------------------------------------------------------------------
# Caption length variants
# ---------------------------------------------------------------------------

def _make_length_variants(caption_text: str, handle: str) -> dict:
    """
    Produce short (under 100 chars, good for TikTok), medium, and long versions.
    """
    # Strip handle temporarily for length calculations
    base = caption_text.replace(handle, "").strip()

    # Short: aggressive trim to under 100 chars total
    short = base
    if len(short) > 90:
        # Take first sentence or phrase
        for sep in ['.', '...', '?', '!']:
            idx = short.find(sep)
            if 10 < idx < 85:
                short = short[:idx + len(sep)]
                break
        else:
            short = short[:87] + "..."

    # Medium: the original caption (under 150 chars target)
    medium = caption_text
    if len(medium) > 150:
        medium = medium[:147] + "..."

    # Long: add context or call-to-action
    ctas = [
        "Follow for more!",
        "Save this for later.",
        "Tag someone who needs to hear this.",
        "Comment your thoughts below.",
        "Share this with a friend.",
    ]
    cta = ctas[hash(base) % len(ctas)]
    long_text = f"{caption_text}\n\n{cta}"

    return {
        "short": short.strip(),
        "medium": medium.strip(),
        "long": long_text.strip(),
    }


# ---------------------------------------------------------------------------
# API-powered caption generator
# ---------------------------------------------------------------------------

def generate_captions(
    hook_text: str,
    summary: str,
    style: str = "dramatic",
    handle: str = "@yourhandle",
    api_key: str = None,
    transcript_text: str = "",
) -> dict:
    """Generate TikTok captions and hashtags using Claude."""
    import anthropic

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return generate_captions_simple(hook_text, summary, style, handle,
                                        transcript_text=transcript_text)

    prompt = CAPTION_PROMPT.format(
        hook_text=hook_text,
        summary=summary,
        style=style,
        handle=handle,
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            data = json.loads(match.group(0))
        else:
            return generate_captions_simple(hook_text, summary, style, handle,
                                            transcript_text=transcript_text)

    # Enrich with smart hashtags if transcript available and API didn't return enough
    if transcript_text and len(data.get("hashtags", [])) < 10:
        data["hashtags"] = _generate_smart_hashtags(transcript_text)

    # Add length variants for each caption
    for cap in data.get("captions", []):
        cap["variants"] = _make_length_variants(cap["text"], handle)

    return data


# ---------------------------------------------------------------------------
# Advanced fallback caption generator (no API)
# ---------------------------------------------------------------------------

def generate_captions_simple(
    hook_text: str,
    summary: str,
    style: str = "dramatic",
    handle: str = "@yourhandle",
    transcript_text: str = "",
) -> dict:
    """
    Fallback caption generator without AI.
    Uses templates, transcript analysis, and smart hashtag generation.
    """
    # Extract a key quote from available text
    source_text = transcript_text or summary or hook_text
    quote = _extract_key_quote(source_text)
    if not quote:
        quote = hook_text.strip('"').strip("'")
    # Shorten quote for templates
    quote_words = quote.split()[:8]
    short_quote = " ".join(quote_words)

    # Build captions from four different template styles, rotating through them
    styles_to_use = ["dramatic", "question", "controversial", "story_tease"]
    captions = []
    for s in styles_to_use[:3]:
        caption_text = _pick_template(s, short_quote, handle)
        variants = _make_length_variants(caption_text, handle)
        captions.append({
            "style": s,
            "text": caption_text,
            "variants": variants,
        })

    # Generate smart hashtags from transcript content
    hashtag_source = transcript_text or summary or hook_text
    hashtags = _generate_smart_hashtags(hashtag_source)

    # Detect the primary niche for metadata
    niches = _detect_niches(hashtag_source)
    primary_niche = niches[0][0] if niches else "general"

    return {
        "captions": captions,
        "hashtags": hashtags,
        "detected_niche": primary_niche,
    }


if __name__ == "__main__":
    # Demo with sample transcript text to show smart features
    sample_transcript = (
        "I started this company when I was 19 years old. Everyone said I was crazy. "
        "But within two years we hit $2 million in revenue. The secret? I worked 18 "
        "hour days while everyone else was partying. No one wants to hear that grind "
        "is the only shortcut. Do you know what the difference is between people who "
        "make it and people who don't? Discipline. Pure discipline. I lost everything "
        "once, went completely broke, had $200 in my bank account. But I kept going."
    )

    result = generate_captions(
        hook_text="HE MADE $2M AT 21",
        summary="Young entrepreneur reveals how he built a business empire",
        style="dramatic",
        transcript_text=sample_transcript,
    )
    print(json.dumps(result, indent=2))
