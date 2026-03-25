"""
Trend Monitor — uses web search to discover viral products and
trending niches before they hit the mainstream.
"""
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

TREND_ANALYSIS_PROMPT = """You are a product research analyst for a high-ticket dropshipping operation.

Analyze the following trend data and identify the top 5 products worth adding to our store.

Niche focus: {niche}
Current date context: March 2026
Platform signals: {platform_signals}

For each product, provide:
1. Product name and description
2. Why it's trending NOW
3. Estimated supplier cost range
4. Recommended selling price for a premium brand
5. Target customer demographic
6. Risk assessment (1-10, where 10 = safest bet)
7. US-based supplier recommendation (Zendrop, Spocket, or AutoDS)

Return as a JSON array of objects with keys:
product_name, description, trend_reason, supplier_cost_range, recommended_price,
target_demo, risk_score, supplier_recommendation

Return ONLY valid JSON."""


def analyze_trends(
    niche: str,
    platform_signals: str = "TikTok viral products, Pinterest trending boards, Instagram Reels top sellers",
) -> list[dict]:
    """Use Claude to analyze current trend signals and recommend products."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": TREND_ANALYSIS_PROMPT.format(
                niche=niche,
                platform_signals=platform_signals,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


COMPETITOR_PROMPT = """Analyze these competitor stores in the {niche} niche and identify gaps we can exploit:

Competitors: {competitors}

For each gap, provide:
1. What they're missing or doing poorly
2. How we can capitalize on it
3. Specific product or feature recommendation

Return as JSON array with keys: gap, strategy, product_recommendation"""


def analyze_competitors(niche: str, competitors: list[str]) -> list[dict]:
    """Analyze competitor stores for gaps and opportunities."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": COMPETITOR_PROMPT.format(
                niche=niche,
                competitors=", ".join(competitors),
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


if __name__ == "__main__":
    import sys
    niche = sys.argv[1] if len(sys.argv) > 1 else "Smart Home & Wellness"
    print(f"Analyzing trends for: {niche}\n")
    trends = analyze_trends(niche)
    print(json.dumps(trends, indent=2))
