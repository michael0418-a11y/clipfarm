"""
TikTok Ad Script Generator — creates scroll-stopping video ad scripts
for high-ticket dropshipping products using proven viral frameworks.
"""
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ── Proven TikTok Ad Frameworks ───────────────────────────────────────

FRAMEWORKS = {
    "hook_problem_solution": {
        "name": "Hook → Problem → Solution",
        "structure": "Open with a bold hook (1-3s), present the problem the viewer relates to (3-8s), reveal your product as the solution (8-20s), show social proof + CTA (20-30s)",
        "best_for": "Products that solve a clear pain point",
    },
    "before_after": {
        "name": "Before/After Transformation",
        "structure": "Show the 'before' state (1-5s), transition effect (5-7s), show the 'after' result (7-20s), product reveal + CTA (20-30s)",
        "best_for": "Beauty, wellness, home improvement products",
    },
    "unboxing_reaction": {
        "name": "Unboxing + First Reaction",
        "structure": "Package arrival excitement (1-3s), unboxing reveal (3-10s), first use reaction (10-20s), results + CTA (20-30s)",
        "best_for": "Premium/luxury products, tech gadgets",
    },
    "ugc_testimonial": {
        "name": "UGC-Style Testimonial",
        "structure": "Casual selfie-style intro 'okay so...' (1-3s), personal story/problem (3-10s), discovery of product (10-15s), honest review + results (15-25s), CTA (25-30s)",
        "best_for": "Any product — highest trust factor",
    },
    "myth_buster": {
        "name": "Myth Buster / 'Did You Know'",
        "structure": "Shocking fact or myth (1-3s), explanation with authority (3-12s), product as the answer (12-22s), proof + CTA (22-30s)",
        "best_for": "Health, wellness, skincare — products backed by science",
    },
    "day_in_life": {
        "name": "Day-in-My-Life Integration",
        "structure": "Morning routine start (1-5s), natural product integration moment (5-15s), lifestyle context showing the product in use (15-25s), subtle CTA (25-30s)",
        "best_for": "Lifestyle products, wellness routines",
    },
}

AD_SCRIPT_PROMPT = """You are a TikTok creative strategist who has produced ads generating $10M+ in revenue
for DTC brands. You specialize in scroll-stopping hooks and native-feeling content.

Create a TikTok ad script for this product:

Product: {product_name}
Price point: {price_point}
Key benefit: {key_benefit}
Target audience: {target_audience}
Framework: {framework_name} — {framework_structure}
Brand voice: {brand_voice}
Ad length: {ad_length} seconds

Rules:
- The HOOK (first 1-3 seconds) must stop the scroll. Use pattern interrupts, controversy, or curiosity gaps
- It must feel NATIVE to TikTok — not like an ad. Think "person talking to camera" not "commercial"
- Include specific camera directions, text overlay suggestions, and sound/music notes
- Include 3 alternative hooks to A/B test
- NO corporate language. Use casual, conversational tone
- Include a strong CTA that creates urgency without being pushy

Return a JSON object:
{{
  "primary_script": {{
    "hook": "exact words for first 1-3 seconds",
    "hook_visual": "what the viewer sees",
    "body": ["array of script sections with timestamps"],
    "cta": "call to action",
    "text_overlays": ["text that appears on screen at key moments"],
    "music_suggestion": "type of background audio",
    "total_duration": "{ad_length}s"
  }},
  "alternative_hooks": [
    {{"hook": "alt hook 1", "hook_visual": "visual description"}},
    {{"hook": "alt hook 2", "hook_visual": "visual description"}},
    {{"hook": "alt hook 3", "hook_visual": "visual description"}}
  ],
  "production_notes": "tips for filming this ad",
  "estimated_ctr": "expected click-through rate range",
  "hashtags": ["5-8 relevant hashtags"]
}}

Return ONLY valid JSON."""

BATCH_PROMPT = """You are a TikTok content calendar strategist for a premium {niche} brand.

Create a 30-day TikTok content calendar that mixes organic content with paid ad scripts.

Brand voice: {brand_voice}
Products: {products}
Target audience: {target_audience}

For each day, provide:
- Content type (organic/paid)
- Framework used
- Brief concept (1-2 sentences)
- Best posting time
- Hashtag set

Return as a JSON array of 30 objects with keys:
day, content_type, framework, concept, posting_time, hashtags

Return ONLY valid JSON."""


def generate_ad_script(
    product_name: str,
    price_point: str = "$249",
    key_benefit: str = "Professional-grade skin rejuvenation at home",
    target_audience: str = "Women 25-40 interested in anti-aging and skincare",
    framework: str = "hook_problem_solution",
    brand_voice: str = "Confident, warm, science-backed but approachable",
    ad_length: int = 30,
) -> dict:
    """Generate a single TikTok ad script."""
    fw = FRAMEWORKS.get(framework, FRAMEWORKS["hook_problem_solution"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": AD_SCRIPT_PROMPT.format(
                product_name=product_name,
                price_point=price_point,
                key_benefit=key_benefit,
                target_audience=target_audience,
                framework_name=fw["name"],
                framework_structure=fw["structure"],
                brand_voice=brand_voice,
                ad_length=ad_length,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


def generate_ad_variations(
    product_name: str,
    price_point: str = "$249",
    key_benefit: str = "Professional-grade skin rejuvenation at home",
    target_audience: str = "Women 25-40 interested in anti-aging and skincare",
    brand_voice: str = "Confident, warm, science-backed but approachable",
    num_variations: int = 3,
) -> list[dict]:
    """Generate multiple ad variations using different frameworks."""
    framework_keys = list(FRAMEWORKS.keys())[:num_variations]
    results = []

    for fw_key in framework_keys:
        print(f"  Generating: {FRAMEWORKS[fw_key]['name']}...")
        script = generate_ad_script(
            product_name=product_name,
            price_point=price_point,
            key_benefit=key_benefit,
            target_audience=target_audience,
            framework=fw_key,
            brand_voice=brand_voice,
        )
        script["framework_used"] = FRAMEWORKS[fw_key]["name"]
        results.append(script)

    return results


def generate_content_calendar(
    niche: str = "LED/Red Light Therapy",
    products: str = "LED Face Mask ($249), Red Light Panel ($499), Therapy Wand ($149)",
    target_audience: str = "Women 25-40, skincare & wellness enthusiasts",
    brand_voice: str = "Confident, warm, science-backed but approachable",
) -> list[dict]:
    """Generate a 30-day TikTok content calendar."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": BATCH_PROMPT.format(
                niche=niche,
                products=products,
                target_audience=target_audience,
                brand_voice=brand_voice,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "calendar":
        print("Generating 30-day TikTok content calendar...\n")
        calendar = generate_content_calendar()
        for day in calendar:
            print(f"Day {day.get('day', '?')}: [{day.get('content_type', '?')}] "
                  f"{day.get('concept', '?')}")
    else:
        product = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Professional LED Face Mask"
        print(f"Generating TikTok ad scripts for: {product}\n{'='*50}")
        scripts = generate_ad_variations(product_name=product)
        for i, script in enumerate(scripts, 1):
            print(f"\n{'─'*50}")
            print(f"Ad #{i}: {script.get('framework_used', '?')}")
            primary = script.get("primary_script", {})
            print(f"  Hook: \"{primary.get('hook', '?')}\"")
            print(f"  CTA: \"{primary.get('cta', '?')}\"")
            print(f"  Music: {primary.get('music_suggestion', '?')}")
            alt_hooks = script.get("alternative_hooks", [])
            for j, alt in enumerate(alt_hooks, 1):
                print(f"  Alt Hook {j}: \"{alt.get('hook', '?')}\"")
