"""
Brand Bible Generator — creates a complete brand identity document
using Claude, tailored to your chosen niche.
"""
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

BRAND_BIBLE_PROMPT = """You are a world-class brand strategist who has built identities for DTC brands
that scaled from $0 to $10M+.

Create a complete Brand Bible for the following store:

Niche: {niche}
Target customer: {target_customer}
Price range: {price_range}
Competitive angle: {competitive_angle}

Return a JSON object with these exact keys:

{{
  "brand_name_options": ["3 brand name suggestions — short, memorable, domain-available style"],
  "tagline_options": ["3 tagline options"],
  "mission_statement": "2-3 sentences",
  "brand_voice": {{
    "tone": "3-5 adjective description",
    "do": ["5 things the brand voice DOES"],
    "dont": ["5 things the brand voice NEVER does"]
  }},
  "visual_identity": {{
    "primary_colors": ["hex codes with names"],
    "secondary_colors": ["hex codes with names"],
    "typography": {{
      "headings": "font recommendation",
      "body": "font recommendation"
    }},
    "photography_style": "description of image style"
  }},
  "target_persona": {{
    "name": "fictional customer name",
    "age_range": "range",
    "income": "range",
    "values": ["list"],
    "pain_points": ["list"],
    "where_they_shop": ["list of comparable brands"]
  }},
  "content_pillars": ["4-5 content themes for social media"],
  "elevator_pitch": "One paragraph pitch for investors or partners"
}}

Return ONLY valid JSON, no markdown fences."""


def generate_brand_bible(
    niche: str,
    target_customer: str = "Affluent millennials and Gen-Z professionals, 25-40",
    price_range: str = "$200 - $800",
    competitive_angle: str = "Premium quality with fast US shipping and curated selection",
) -> dict:
    """Generate a complete brand identity document."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": BRAND_BIBLE_PROMPT.format(
                niche=niche,
                target_customer=target_customer,
                price_range=price_range,
                competitive_angle=competitive_angle,
            ),
        }],
    )
    raw = message.content[0].text.strip()
    return json.loads(raw)


if __name__ == "__main__":
    import sys
    niche = sys.argv[1] if len(sys.argv) > 1 else "Premium Smart Home & Wellness Devices"
    print(f"Generating brand bible for: {niche}\n")
    bible = generate_brand_bible(niche)
    print(json.dumps(bible, indent=2))
