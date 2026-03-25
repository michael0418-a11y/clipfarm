"""
Organic TikTok Growth Engine — generates viral content ideas, hooks,
and posting strategies for $0 marketing budget.

No ads. Pure organic reach.
"""
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ── Proven Organic TikTok Formats (no ad spend) ──────────────────────

VIRAL_FORMATS = {
    "storytime": {
        "name": "Storytime / Personal Experience",
        "why_free": "Highest organic reach — TikTok pushes authentic stories",
        "example": "I spent $3,000 on skincare that didn't work. Then I found THIS.",
    },
    "myth_bust": {
        "name": "Myth Busting / Controversial Take",
        "why_free": "Drives comments (algorithm fuel). Controversy = engagement",
        "example": "Dermatologists don't want you to know this about LED masks...",
    },
    "pov": {
        "name": "POV / Relatable Skit",
        "why_free": "High share rate. People tag friends",
        "example": "POV: Your friend asks why your skin looks different and you show them your LED mask",
    },
    "asmr_demo": {
        "name": "ASMR / Satisfying Demo",
        "why_free": "High watch time = algorithm boost. No talking needed",
        "example": "The sound of unboxing + clicking the mask on. Satisfying AF.",
    },
    "side_by_side": {
        "name": "Side-by-Side Comparison",
        "why_free": "Educational + saves. People bookmark comparisons",
        "example": "$30 Amazon LED mask vs $249 clinical-grade. Let me show you the difference.",
    },
    "stitch_duet": {
        "name": "Stitch/Duet Trending Content",
        "why_free": "Piggybacks on existing viral videos. Zero creative effort",
        "example": "Stitch a viral skincare routine video and add your product",
    },
    "carousel": {
        "name": "Photo Carousel / Slideshow",
        "why_free": "TikTok is pushing carousels HARD in 2026. Easy to make",
        "example": "5 reasons dermatologists recommend red light therapy (carousel slides)",
    },
    "get_ready": {
        "name": "GRWM (Get Ready With Me)",
        "why_free": "Evergreen format. Casual, authentic, high watch time",
        "example": "Night routine: double cleanse → serum → LED mask → moisturize",
    },
}

ORGANIC_PROMPT = """You are a TikTok organic growth strategist who has built accounts from 0 to 100K
followers without spending a single dollar on ads. You specialize in the wellness/beauty niche.

Create {num_ideas} organic TikTok content ideas for a {niche} brand.

Brand: {brand_name}
Products: {products}
Target audience: {target_audience}
Current follower count: {follower_count} (adjust difficulty accordingly)

Rules for ZERO BUDGET content:
- Must be filmable with just a phone (no studio, no fancy equipment)
- Must work without a large following (algorithm-first, not follower-first)
- Include the EXACT hook text (first 1-3 seconds that stops the scroll)
- Include trending sounds/audio suggestions (or "original audio" if talking)
- Must feel native — NOT like an ad. TikTok kills reach on salesy content
- Focus on formats TikTok's algorithm rewards: high watch time, comments, shares, saves

For each idea, return:
{{
  "format": "format name",
  "hook": "exact opening words or text overlay",
  "concept": "2-3 sentence description of the full video",
  "filming_tips": "how to film this with just a phone",
  "audio": "trending sound suggestion or 'original audio'",
  "hashtags": ["5-7 hashtags mixing niche + broad"],
  "why_it_works": "why this will get organic reach",
  "best_time": "optimal posting time",
  "difficulty": "easy | medium | hard"
}}

Return as a JSON array. Return ONLY valid JSON."""

POSTING_SCHEDULE_PROMPT = """Create a free, organic-only 30-day TikTok posting schedule for a {niche} brand
starting from ZERO followers.

Brand: {brand_name}
Products: {products}

Rules:
- 2-3 posts per day (TikTok rewards consistency)
- Mix formats to test what works
- Week 1-2: Focus on trending formats and hooks to grow fast
- Week 3-4: Start soft-selling once you have an audience
- NEVER hard-sell in organic content — TikTok suppresses it
- Include "engagement bait" posts (questions, polls, hot takes)
- Include 2-3 "batch filming" days where you film 10+ videos at once

For each day, return:
{{
  "day": 1,
  "posts": [
    {{
      "time": "7:00 AM",
      "format": "format name",
      "concept": "brief concept",
      "selling": false
    }}
  ],
  "batch_film_day": false,
  "notes": "any strategy notes for this day"
}}

Return as a JSON array of 30 objects. Return ONLY valid JSON."""


def generate_content_ideas(
    num_ideas: int = 10,
    niche: str = "LED/Red Light Therapy",
    brand_name: str = "Novara",
    products: str = "LED Face Mask ($249), Red Light Panel ($499), Therapy Wand ($149)",
    target_audience: str = "Women 25-40, skincare enthusiasts",
    follower_count: str = "0 (brand new account)",
) -> list[dict]:
    """Generate organic TikTok content ideas — no ad spend needed."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": ORGANIC_PROMPT.format(
                num_ideas=num_ideas,
                niche=niche,
                brand_name=brand_name,
                products=products,
                target_audience=target_audience,
                follower_count=follower_count,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


def generate_posting_schedule(
    niche: str = "LED/Red Light Therapy",
    brand_name: str = "Novara",
    products: str = "LED Face Mask ($249), Red Light Panel ($499), Therapy Wand ($149)",
) -> list[dict]:
    """Generate a 30-day organic posting schedule."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": POSTING_SCHEDULE_PROMPT.format(
                niche=niche,
                brand_name=brand_name,
                products=products,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "schedule":
        print("30-Day Organic TikTok Schedule (FREE)\n" + "="*50)
        schedule = generate_posting_schedule()
        for day in schedule:
            batch = " [BATCH FILM DAY]" if day.get("batch_film_day") else ""
            print(f"\nDay {day.get('day', '?')}{batch}")
            for post in day.get("posts", []):
                sell = " $" if post.get("selling") else ""
                print(f"  {post.get('time', '?')} — {post.get('format', '?')}: {post.get('concept', '?')}{sell}")
    else:
        print("Organic TikTok Content Ideas (FREE)\n" + "="*50)
        ideas = generate_content_ideas(num_ideas=10)
        for i, idea in enumerate(ideas, 1):
            print(f"\n{'─'*50}")
            print(f"#{i} [{idea.get('format', '?')}] ({idea.get('difficulty', '?')})")
            print(f"  Hook: \"{idea.get('hook', '?')}\"")
            print(f"  Concept: {idea.get('concept', '?')}")
            print(f"  Audio: {idea.get('audio', '?')}")
            print(f"  Best time: {idea.get('best_time', '?')}")
            print(f"  Why it works: {idea.get('why_it_works', '?')}")
