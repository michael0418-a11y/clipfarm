"""
Module 6: Trend Intelligence Engine
Fetches current TikTok/YouTube Shorts trends and bakes them into clip selection,
caption generation, and hashtag strategies.
Works offline with built-in trend data + optional live web scraping.
"""

import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Built-in trend database (updated periodically, works offline)
# ---------------------------------------------------------------------------

VIRAL_HOOKS = [
    # Question hooks
    "What would you do with $1 million?",
    "Is this even legal?",
    "Why does nobody talk about this?",
    "How is this not viral yet?",
    "Did he really just say that?",
    "Wait... did you catch that?",
    "Can someone explain this to me?",
    # Command hooks
    "Watch this till the end",
    "Wait for it...",
    "You need to hear this",
    "Stop scrolling. This is important.",
    "Listen to what he says next",
    "This changed everything for me",
    "POV: You just discovered this",
    # Shock/curiosity hooks
    "Nobody was supposed to see this",
    "This is why you're still broke",
    "He said the quiet part out loud",
    "The part they don't show you",
    "This will blow your mind",
    "I can't believe this is real",
    "They deleted this for a reason",
    # Story hooks
    "So this just happened...",
    "The craziest thing I've ever seen",
    "He went from $0 to $10M doing THIS",
    "This man just broke the internet",
    "Everyone needs to see this clip",
]

TRENDING_HASHTAGS = {
    "always_viral": [
        "#fyp", "#foryou", "#foryoupage", "#viral", "#xyzbca",
        "#trending", "#blowthisup", "#viralvideo", "#goviral",
    ],
    "entrepreneur": [
        "#entrepreneur", "#business", "#money", "#millionaire",
        "#hustle", "#motivation", "#success", "#startup",
        "#financialfreedom", "#sidehustle", "#passiveincome",
        "#investing", "#crypto", "#wealth", "#grind",
        "#billionaire", "#ceo", "#rich", "#luxurylife",
    ],
    "gaming": [
        "#gaming", "#gamer", "#twitch", "#streamer",
        "#gamingclips", "#epicmoment", "#clutch", "#rage",
        "#fortniteclips", "#valorant", "#minecraft", "#apex",
        "#warzone", "#esports", "#twitchclips",
    ],
    "comedy": [
        "#funny", "#comedy", "#meme", "#humor", "#lol",
        "#joke", "#laughing", "#hilarious", "#relatable",
        "#skit", "#comedyclub",
    ],
    "motivation": [
        "#motivation", "#inspiration", "#mindset", "#grindset",
        "#discipline", "#selfimprovement", "#goals",
        "#nevergiveup", "#successmindset", "#hardwork",
        "#motivational", "#lifechanging",
    ],
    "podcast": [
        "#podcast", "#podcastclips", "#interview",
        "#conversation", "#deepthoughts", "#realtalk",
        "#hottake", "#debate", "#storytime",
    ],
    "luxury": [
        "#luxury", "#rich", "#lifestyle", "#lambo",
        "#supercar", "#mansion", "#dubai", "#rolex",
        "#millionairelifestyle", "#luxurylife",
    ],
    "fitness": [
        "#fitness", "#gym", "#workout", "#gains",
        "#bodybuilding", "#fitnessmotivation", "#health",
        "#transformation", "#gymlife",
    ],
    "dating": [
        "#dating", "#relationships", "#love", "#redpill",
        "#datingadvice", "#rizz", "#attraction",
    ],
}

# Niche detection keywords
NICHE_KEYWORDS = {
    "entrepreneur": ["money", "business", "startup", "revenue", "profit", "company",
                     "million", "billion", "invest", "stock", "crypto", "bitcoin",
                     "income", "wealth", "entrepreneur", "ceo", "founder"],
    "gaming": ["game", "stream", "twitch", "play", "level", "win", "clutch",
               "rage", "kill", "team", "ranked", "esport", "controller",
               "pc", "console", "fortnite", "valorant", "minecraft"],
    "comedy": ["funny", "laugh", "joke", "hilarious", "comedy", "prank",
               "roast", "skit", "meme"],
    "motivation": ["discipline", "mindset", "grind", "wake up", "goal",
                   "dream", "success", "failure", "never give up", "hustle",
                   "hard work", "sacrifice"],
    "podcast": ["podcast", "interview", "guest", "episode", "host",
                "conversation", "topic", "opinion", "debate"],
    "luxury": ["luxury", "lambo", "ferrari", "rolex", "mansion", "yacht",
               "dubai", "private jet", "penthouse", "designer"],
    "fitness": ["gym", "workout", "muscle", "protein", "cardio", "weight",
                "bench", "squat", "deadlift", "bulk", "cut", "gains"],
    "dating": ["dating", "relationship", "girl", "guy", "rizz", "attraction",
               "red pill", "alpha", "confidence", "approach"],
}

# Best posting times (ET) by day of week
BEST_POSTING_TIMES = {
    "monday": ["7:00", "10:00", "22:00"],
    "tuesday": ["6:00", "9:00", "20:00"],
    "wednesday": ["7:00", "11:00", "21:00"],
    "thursday": ["9:00", "12:00", "19:00"],
    "friday": ["5:00", "13:00", "15:00"],
    "saturday": ["11:00", "19:00", "21:00"],
    "sunday": ["8:00", "16:00", "20:00"],
}

# TikTok algorithm factors (weights for scoring)
ALGORITHM_WEIGHTS = {
    "watch_time_pct": 0.30,       # % of video watched (most important)
    "replay_rate": 0.20,          # How often replayed
    "shares": 0.15,               # Shares > saves > comments > likes
    "saves": 0.12,
    "comments": 0.10,
    "likes": 0.08,
    "follows_from_video": 0.05,
}

# Creativity Program requirements
CREATIVITY_PROGRAM = {
    "min_followers": 10000,
    "min_views_30d": 100000,
    "min_video_length_sec": 60,   # 1+ minute for higher RPM
    "target_length_sec": 90,      # Sweet spot for RPM
    "avg_rpm_short": 0.20,        # RPM for <1min clips (USD per 1000 views)
    "avg_rpm_long": 1.00,         # RPM for 1+ min clips
    "best_rpm_niches": ["entrepreneur", "luxury", "motivation", "dating"],
}


def detect_niche(text: str) -> dict:
    """Detect content niche from transcript text. Returns dict of niche -> score."""
    text_lower = text.lower()
    scores = {}
    for niche, keywords in NICHE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[niche] = score
    # Normalize
    if scores:
        max_score = max(scores.values())
        scores = {k: round(v / max_score, 2) for k, v in scores.items()}
    return dict(sorted(scores.items(), key=lambda x: -x[1]))


def get_niche(text: str) -> str:
    """Get the primary niche for a transcript."""
    scores = detect_niche(text)
    return next(iter(scores), "general") if scores else "general"


def get_trending_hashtags(text: str, count: int = 20) -> list:
    """Generate optimized hashtags based on detected niche + viral tags."""
    niche = get_niche(text)

    tags = list(TRENDING_HASHTAGS["always_viral"][:5])

    # Add niche-specific tags
    niche_tags = TRENDING_HASHTAGS.get(niche, [])
    tags.extend(random.sample(niche_tags, min(8, len(niche_tags))))

    # Add secondary niche tags
    scores = detect_niche(text)
    for secondary_niche in list(scores.keys())[1:3]:
        sec_tags = TRENDING_HASHTAGS.get(secondary_niche, [])
        tags.extend(random.sample(sec_tags, min(3, len(sec_tags))))

    # Deduplicate and limit
    seen = set()
    unique = []
    for tag in tags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            unique.append(tag)
    return unique[:count]


def get_viral_hook(text: str = "") -> str:
    """Pick a hook that matches the content niche."""
    niche = get_niche(text) if text else "general"

    # Niche-specific hooks
    niche_hooks = {
        "entrepreneur": [
            "This is why you're still broke",
            "He went from $0 to $10M doing THIS",
            "The secret they don't teach in school",
            "Nobody was supposed to hear this",
        ],
        "gaming": [
            "THE MOST INSANE PLAY EVER",
            "He actually did it...",
            "This should be ILLEGAL",
            "No way this just happened",
        ],
        "comedy": [
            "I can't stop watching this",
            "Bro is NOT real 💀",
            "This has me CRYING",
            "The ending tho...",
        ],
        "motivation": [
            "This hit different at 3am",
            "Save this for when you want to quit",
            "The speech that changed my life",
            "You needed to hear this today",
        ],
        "luxury": [
            "This is what $10M looks like",
            "POV: Money isn't a problem",
            "How the other half lives",
        ],
    }

    hooks = niche_hooks.get(niche, []) + VIRAL_HOOKS
    return random.choice(hooks)


def get_best_posting_times(count: int = 3) -> list:
    """Get best posting times for today."""
    day = datetime.now().strftime("%A").lower()
    times = BEST_POSTING_TIMES.get(day, ["9:00", "15:00", "20:00"])
    return times[:count]


def get_clip_strategy(text: str) -> dict:
    """Get recommended clip strategy based on content analysis."""
    niche = get_niche(text)
    word_count = len(text.split())

    strategy = {
        "niche": niche,
        "recommended_clip_length": 35,  # Default
        "recommended_clips_per_video": 5,
        "hook_style": "question",
        "caption_style": "dramatic",
        "color_grade": "cinematic",
        "posting_frequency": "3x daily",
        "best_times_today": get_best_posting_times(),
        "hashtag_count": 20,
        "creativity_program_eligible": False,
    }

    # Adjust by niche
    if niche == "entrepreneur":
        strategy["recommended_clip_length"] = 45
        strategy["hook_style"] = "bold_statement"
        strategy["caption_style"] = "controversial"
        strategy["color_grade"] = "cinematic"
    elif niche == "gaming":
        strategy["recommended_clip_length"] = 30
        strategy["hook_style"] = "shock"
        strategy["caption_style"] = "hype"
        strategy["color_grade"] = "vibrant"
    elif niche == "comedy":
        strategy["recommended_clip_length"] = 25
        strategy["hook_style"] = "tease"
        strategy["caption_style"] = "relatable"
        strategy["color_grade"] = "vibrant"
    elif niche == "motivation":
        strategy["recommended_clip_length"] = 50
        strategy["hook_style"] = "emotional"
        strategy["caption_style"] = "dramatic"
        strategy["color_grade"] = "dark"

    # For Creativity Program RPM, recommend 60+ second clips
    if niche in CREATIVITY_PROGRAM["best_rpm_niches"]:
        strategy["creativity_program_clip_length"] = 90
        strategy["creativity_program_eligible"] = True
        strategy["estimated_rpm"] = CREATIVITY_PROGRAM["avg_rpm_long"]

    return strategy


def score_moment_virality(text: str, words_per_sec: float = 0.0,
                          has_numbers: bool = False, has_question: bool = False,
                          has_profanity: bool = False) -> float:
    """Score a moment's viral potential 0-100 based on trend signals."""
    score = 0.0

    # Money/number mentions (huge engagement driver)
    money_words = ["million", "billion", "thousand", "dollar", "$", "percent", "%",
                   "revenue", "profit", "salary", "net worth"]
    money_count = sum(1 for w in money_words if w in text.lower())
    score += min(money_count * 10, 25)

    # Shock/controversy words
    shock_words = ["crazy", "insane", "unbelievable", "impossible", "secret",
                   "truth", "lie", "scam", "exposed", "illegal", "banned",
                   "never", "worst", "best", "most", "only"]
    shock_count = sum(1 for w in shock_words if w in text.lower())
    score += min(shock_count * 8, 20)

    # Questions drive comments
    if has_question or "?" in text:
        score += 15

    # Fast speech = excitement
    if words_per_sec > 3.0:
        score += 10
    elif words_per_sec > 2.5:
        score += 5

    # Numbers catch attention
    if has_numbers or re.search(r'\d+', text):
        score += 10

    # Short punchy segments score higher (better watch-time %)
    word_count = len(text.split())
    if 15 <= word_count <= 60:
        score += 10
    elif word_count < 15:
        score += 5

    # Emotional language
    emotion_words = ["love", "hate", "afraid", "amazing", "terrible",
                     "incredible", "disgusting", "beautiful", "destroyed",
                     "changed my life", "blew my mind"]
    emotion_count = sum(1 for w in emotion_words if w in text.lower())
    score += min(emotion_count * 8, 15)

    return min(score, 100)


def fetch_trending_sounds() -> list:
    """Return list of trending sound categories/descriptions.
    In future versions, this could scrape TikTok's trending page."""
    return [
        {"name": "Dramatic orchestral build", "style": "motivation/entrepreneur"},
        {"name": "Bass-boosted trap beat", "style": "gaming/hype"},
        {"name": "Lo-fi chill beat", "style": "podcast/chill"},
        {"name": "Epic cinematic score", "style": "luxury/motivation"},
        {"name": "Meme sound effect compilation", "style": "comedy"},
        {"name": "Phonk drift music", "style": "gaming/car"},
        {"name": "Dark ambient suspense", "style": "storytime/mystery"},
        {"name": "Pop remix instrumental", "style": "general/trending"},
    ]


def analyze_twitch_chat(chat_log: list) -> list:
    """Analyze Twitch chat messages to find hype moments.

    Args:
        chat_log: List of dicts with 'timestamp' (seconds), 'user', 'message'

    Returns:
        List of hype moments with timestamp and intensity score.
    """
    if not chat_log:
        return []

    # Hype indicators in chat
    hype_patterns = [
        (r'(?i)(pog|pogchamp|poggers|pogu)', 10),
        (r'(?i)(omg|oh my god|wtf|wth)', 8),
        (r'(?i)(lol|lmao|lmfao|rofl|dead|💀)', 7),
        (r'(?i)(no way|noway|insane|crazy)', 9),
        (r'(?i)(let.?s.?go|lets go|gg|ez|clutch)', 8),
        (r'(?i)(w+$|wwww)', 6),  # Just "W" spam
        (r'(?i)(hype|hyped|fire|🔥)', 7),
        (r'[A-Z]{5,}', 5),  # ALL CAPS messages
        (r'(.)\1{4,}', 4),  # Character spam like "aaaaa"
        (r'[!?]{3,}', 5),   # Excessive punctuation
    ]

    # Bucket messages into 10-second windows
    if not chat_log:
        return []

    max_ts = max(m.get("timestamp", 0) for m in chat_log)
    bucket_size = 10
    buckets = {}

    for msg in chat_log:
        ts = msg.get("timestamp", 0)
        bucket = (ts // bucket_size) * bucket_size
        if bucket not in buckets:
            buckets[bucket] = {"messages": [], "score": 0, "count": 0}

        buckets[bucket]["messages"].append(msg.get("message", ""))
        buckets[bucket]["count"] += 1

        # Score this message
        text = msg.get("message", "")
        for pattern, weight in hype_patterns:
            if re.search(pattern, text):
                buckets[bucket]["score"] += weight

    # Find peaks (hype moments)
    if not buckets:
        return []

    avg_score = sum(b["score"] for b in buckets.values()) / len(buckets)
    avg_count = sum(b["count"] for b in buckets.values()) / len(buckets)

    hype_moments = []
    for ts, data in sorted(buckets.items()):
        # Hype = high score AND high message volume
        intensity = 0
        if data["score"] > avg_score * 2:
            intensity += 50
        if data["count"] > avg_count * 2:
            intensity += 30
        if data["score"] > avg_score * 3:
            intensity += 20

        if intensity >= 50:
            hype_moments.append({
                "timestamp": ts,
                "intensity": min(intensity, 100),
                "message_count": data["count"],
                "score": data["score"],
                "sample_messages": data["messages"][:5],
            })

    return sorted(hype_moments, key=lambda x: -x["intensity"])


def generate_posting_schedule(clips_per_day: int = 3, days: int = 7) -> list:
    """Generate an optimal posting schedule for the next N days."""
    schedule = []
    now = datetime.now()

    for d in range(days):
        day = now + timedelta(days=d)
        day_name = day.strftime("%A").lower()
        times = BEST_POSTING_TIMES.get(day_name, ["9:00", "15:00", "20:00"])

        for i in range(min(clips_per_day, len(times))):
            schedule.append({
                "date": day.strftime("%Y-%m-%d"),
                "day": day.strftime("%A"),
                "time": times[i],
                "slot": i + 1,
            })

    return schedule


def get_content_tips(niche: str = "general") -> dict:
    """Get niche-specific content creation tips."""
    tips = {
        "general": {
            "hook_duration": "0-1.5 seconds",
            "caption_position": "center",
            "font_style": "bold white + black outline",
            "cta": "Follow for more",
            "reply_to_comments": True,
            "pin_comment": "Drop a 🔥 if you agree",
        },
        "entrepreneur": {
            "hook_duration": "0-2 seconds",
            "best_sources": ["podcasts", "interviews", "keynotes", "panels"],
            "money_mentions": "Always highlight specific $ amounts",
            "caption_position": "center-bottom",
            "font_style": "bold white + gold accents",
            "cta": "Follow for daily business tips",
            "pin_comment": "What would you do with that money? 👇",
            "avoid": "Don't use copyrighted music from the source",
        },
        "gaming": {
            "hook_duration": "0-1 second (instant action)",
            "best_sources": ["Twitch VODs", "tournament highlights", "rage compilations"],
            "caption_position": "top",
            "font_style": "bold neon colors + glow effect",
            "cta": "Follow for insane clips",
            "pin_comment": "Rate this play 1-10 👇",
            "use_chat_overlay": True,
        },
        "motivation": {
            "hook_duration": "0-2 seconds",
            "best_sources": ["speeches", "podcast moments", "documentary clips"],
            "caption_position": "center",
            "font_style": "large white text + cinematic bars",
            "cta": "Save this for when you need it",
            "pin_comment": "Tag someone who needs to hear this",
        },
    }
    return tips.get(niche, tips["general"])


# ---------------------------------------------------------------------------
# Live trend fetching (optional, uses web scraping)
# ---------------------------------------------------------------------------

def fetch_live_trends() -> dict:
    """Attempt to fetch live trending data. Returns cached data if offline.

    This is a placeholder for future web scraping integration.
    Could use APIs like:
    - TikTok Research API (requires approval)
    - YouTube Data API (free tier)
    - Social Blade / TokBoard scraping
    """
    # Return built-in data for now
    return {
        "top_niches": ["entrepreneur", "gaming", "motivation", "comedy", "luxury"],
        "trending_formats": [
            "podcast highlight clips",
            "luxury lifestyle compilations",
            "gaming clutch moments",
            "motivational speech edits",
            "controversial hot takes",
            "reaction clips",
        ],
        "algorithm_tips": [
            "First 1-2 seconds determine 80% of performance",
            "Watch time % is the #1 ranking factor",
            "Shares are weighted 5x more than likes",
            "Post 3-5x daily for fastest growth",
            "1+ minute clips earn 3-5x higher RPM",
            "Reply to every comment in first hour",
            "Use 3-5 hashtags (not 30)",
            "Hook text on screen in first 0.5 seconds",
        ],
        "copyright_tips": [
            "Add visual transformations (zoom, color grade, captions)",
            "Keep clips under 60 seconds of original content",
            "Add your own commentary or text overlays",
            "Use royalty-free background music",
            "Avoid music-heavy content (highest strike risk)",
            "Speed up/slow down slightly (even 1.05x helps)",
            "Mirror/flip the video subtly",
            "Add borders or overlays that change the frame",
        ],
        "updated": datetime.now().isoformat(),
    }
