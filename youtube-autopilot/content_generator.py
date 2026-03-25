import requests
import json
import re

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

SCRIPT_PROMPT = """You are a top YouTube Shorts scriptwriter for a faceless channel in the "{niche}" niche.

Write a fast, punchy, dramatized revenge story for a YouTube SHORT about: {topic}

The story must fit inside 55 seconds total when read aloud. Use this 4-part structure:
1. HOOK (1-2 sentences, ~10 sec) — Start mid-action with the most shocking moment. No setup. Grab instantly.
2. BETRAYAL (2 sentences, ~12 sec) — What they did. Specific, raw, emotionally charged.
3. REVENGE (2 sentences, ~12 sec) — Exactly how the narrator got back at them. Satisfying and specific.
4. OUTCOME (1-2 sentences, ~10 sec) — What happened to the wrongdoer. End with "Follow for more revenge stories."

Return ONLY valid JSON in this exact format:
{{
  "title": "Click-worthy Shorts title (under 60 chars, punchy, first-person angle) #Shorts",
  "description": "Short description (100-150 words). Tease the story with drama. Include: 'reddit revenge', 'betrayal', 'pro revenge', 'shorts'. End with CTA to follow.",
  "tags": ["reddit revenge", "betrayal stories", "pro revenge", "petty revenge", "r/revenge", "reddit stories", "revenge story", "workplace revenge", "shorts", "satisfying revenge"],
  "thumbnail_text": "2-3 WORD HOOK (all caps)",
  "thumbnail_subtitle": "teaser (4-6 words)",
  "script": [
    {{
      "section": 0,
      "text": "HOOK — 1-2 shocking sentences that open mid-action.",
      "image_prompt": "dramatic cinematic scene matching the hook, dark moody atmosphere, no faces, photorealistic, 4K vertical portrait"
    }},
    {{
      "section": 1,
      "text": "BETRAYAL — exactly what they did, 2 vivid sentences.",
      "image_prompt": "tense confrontation scene, dark office or workplace, shadows, dramatic lighting, no faces, cinematic 4K"
    }},
    {{
      "section": 2,
      "text": "REVENGE — how the narrator struck back, 2 satisfying sentences.",
      "image_prompt": "person at computer or desk taking action, determined mood, dramatic lighting, cinematic, photorealistic, no faces"
    }},
    {{
      "section": 3,
      "text": "OUTCOME — what happened to them. End with follow CTA.",
      "image_prompt": "triumphant satisfying scene, warm light breaking through darkness, cinematic, photorealistic, no faces, 4K"
    }}
  ]
}}

Rules:
- TOTAL script when read aloud must be under 55 seconds — keep each section SHORT (1-2 sentences max)
- First-person narrator voice, like reading a Reddit post
- visual_keywords: 2 phrases for stock footage (people, emotions, workplaces — no nature/space)
- Story must feel real and relatable
- Revenge must be legal (expose, quit, report, go public, etc.)
- No special characters that break JSON
- No character names — use "my boss", "my coworker", "my ex", "my sister", etc."""

TOPIC_PROMPT = """Suggest one specific Reddit-style revenge or betrayal story topic for a YouTube channel about: {niche}

The topic should be:
- Relatable (workplace, family, relationship, or friendship betrayal)
- Have a satisfying revenge payoff
- Feel like something that could have actually happened
- Good for a 2-3 minute story video

Reply with ONLY the story topic, nothing else.
Examples:
- "My boss stole my promotion and gave it to his nephew, so I reported him to HR with receipts"
- "My best friend secretly applied to my dream job — so I made sure she didn't get it"
- "My landlord kept my entire deposit illegally, so I took him to court and won double"
"""

TRENDING_TOPIC_PROMPT = """These are currently trending search topics: {trending}

Pick ONE of these (or a closely related angle) that would make the best Reddit-style revenge or betrayal story for a YouTube channel about: {niche}

The chosen topic should be:
- Currently relevant and emotionally resonant
- Suitable for a 2-3 minute revenge story video
- Have a satisfying payoff angle

Reply with ONLY the final story topic title, nothing else.
"""


class ContentGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _call_groq(self, prompt: str) -> str:
        response = requests.post(
            GROQ_URL,
            headers=self.headers,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _pick_trending_topic(self, niche: str) -> str | None:
        """Use pytrends to find a trending topic related to the niche. Returns None on failure."""
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))

            # Extract 1-3 keywords from the niche string
            keywords = [w for w in niche.lower().split() if len(w) > 3][:3]
            if not keywords:
                return None

            pytrends.build_payload(keywords, timeframe='now 7-d', geo='US')
            related = pytrends.related_queries()

            rising_topics = []
            for kw in keywords:
                data = related.get(kw, {})
                rising = data.get('rising')
                if rising is not None and not rising.empty:
                    rising_topics.extend(rising['query'].tolist()[:5])

            if not rising_topics:
                return None

            topic_list = ', '.join(dict.fromkeys(rising_topics)[:8])  # dedupe, take top 8
            print(f"   Trending: {topic_list}")
            return self._call_groq(
                TRENDING_TOPIC_PROMPT.format(trending=topic_list, niche=niche)
            ).strip()

        except Exception as e:
            return None  # Fall back silently

    def pick_topic(self, niche: str) -> str:
        topic = self._pick_trending_topic(niche)
        if topic:
            print(f"   (from trending searches)")
            return topic
        return self._call_groq(TOPIC_PROMPT.format(niche=niche)).strip()

    def generate(self, topic: str, niche: str) -> dict:
        raw = self._call_groq(SCRIPT_PROMPT.format(topic=topic, niche=niche))

        # Strip markdown code blocks if present
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        raw = raw.strip()

        content = json.loads(raw)

        # Add safe_title for use as folder name
        safe = re.sub(r'[^\w\s-]', '', content["title"])
        safe = re.sub(r'\s+', '_', safe).strip('_')[:60]
        content["safe_title"] = safe

        return content
