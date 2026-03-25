"""
Pricing Optimizer — monitors competitor prices and adjusts your
Shopify prices to maintain target margins while staying competitive.
"""
import os
import anthropic
from dotenv import load_dotenv
from shopify_client import get_products, update_product

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

PRICING_PROMPT = """You are a pricing strategist for a high-ticket dropshipping brand.

Given this product data, recommend the optimal price:

Product: {title}
Cost (from supplier): ${cost}
Current selling price: ${current_price}
Category: {category}
Competitor prices: {competitor_prices}
Target margin: {target_margin}%

Consider:
1. Perceived value — high-ticket customers associate price with quality
2. Psychological pricing (e.g., $497 vs $500)
3. Competitor positioning — undercut slightly OR price higher if brand justifies it
4. Shipping costs baked into price (free shipping perception)

Return ONLY a JSON object:
{{"recommended_price": 0.00, "reasoning": "one sentence", "margin_pct": 0.0}}"""


def calculate_optimal_price(
    title: str,
    cost: float,
    current_price: float,
    category: str = "Home & Wellness",
    competitor_prices: str = "Not available",
    target_margin: float = 40.0,
) -> dict:
    """Get AI-recommended price for a product."""
    import json
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": PRICING_PROMPT.format(
                title=title,
                cost=cost,
                current_price=current_price,
                category=category,
                competitor_prices=competitor_prices,
                target_margin=target_margin,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


def optimize_store_prices(
    cost_map: dict[int, float],
    target_margin: float = 40.0,
    dry_run: bool = True,
) -> list[dict]:
    """Optimize prices for all products.

    cost_map: {product_id: supplier_cost}
    """
    products = get_products(limit=250)
    results = []

    for product in products:
        pid = product["id"]
        if pid not in cost_map:
            continue

        variant = product["variants"][0] if product.get("variants") else None
        if not variant:
            continue

        current_price = float(variant.get("price", 0))
        cost = cost_map[pid]

        rec = calculate_optimal_price(
            title=product["title"],
            cost=cost,
            current_price=current_price,
            target_margin=target_margin,
        )

        result = {
            "id": pid,
            "title": product["title"],
            "current_price": current_price,
            "cost": cost,
            **rec,
            "pushed": False,
        }

        if not dry_run and rec.get("recommended_price"):
            update_product(pid, {
                "variants": [{"id": variant["id"], "price": str(rec["recommended_price"])}]
            })
            result["pushed"] = True

        results.append(result)
        print(f"  ${current_price} → ${rec.get('recommended_price', '?')}  {product['title']}")

    return results
