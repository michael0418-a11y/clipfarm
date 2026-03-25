"""
Module 4: Caption & Hashtag Generator
Generates TikTok captions and hashtags using Claude.
"""

import json
import os


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


def generate_captions(
    hook_text: str,
    summary: str,
    style: str = "dramatic",
    handle: str = "@yourhandle",
    api_key: str = None,
) -> dict:
    """Generate TikTok captions and hashtags using Claude."""
    import anthropic

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return generate_captions_simple(hook_text, summary, style, handle)

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
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            data = json.loads(match.group(0))
        else:
            return generate_captions_simple(hook_text, summary, style, handle)

    return data


def generate_captions_simple(
    hook_text: str,
    summary: str,
    style: str = "dramatic",
    handle: str = "@yourhandle",
) -> dict:
    """Fallback caption generator without AI."""
    hook_clean = hook_text.strip('"').strip("'")

    captions = [
        {"style": "dramatic", "text": f"{hook_clean}... wait for it 🤯 {handle}"},
        {"style": "relatable", "text": f"Would you do this? 👀 {handle}"},
        {"style": "controversial", "text": f"Nobody talks about this... {handle}"},
    ]

    hashtags = [
        "#fyp", "#foryou", "#viral", "#foryoupage", "#trending",
        "#entrepreneur", "#luxury", "#motivation", "#success", "#money",
        "#mindset", "#grind", "#hustle", "#rich", "#millionaire",
        "#lifestyle", "#business", "#investing", "#clips", "#highlights",
    ]

    return {"captions": captions, "hashtags": hashtags}


if __name__ == "__main__":
    result = generate_captions(
        hook_text="HE MADE $10M AT 19",
        summary="Young entrepreneur reveals how he built a business empire",
        style="dramatic",
    )
    print(json.dumps(result, indent=2))
