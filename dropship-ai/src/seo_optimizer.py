"""
SEO & Meta Tag Optimizer — generates optimized meta titles, descriptions,
and collection page copy for Shopify products.
"""
import os
import json
import anthropic
from dotenv import load_dotenv
from shopify_client import get_products, update_product

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SEO_PROMPT = """You are an e-commerce SEO specialist for a premium {niche} brand.

Optimize the following product for search engines:

Product title: {title}
Current description: {description}
Price: {price}
Brand name: {brand_name}

Generate:
1. SEO-optimized meta title (under 60 characters, includes primary keyword)
2. Meta description (under 155 characters, includes CTA and keyword)
3. 5 target keywords (long-tail, buyer-intent)
4. URL slug recommendation
5. Alt text for product images (3 variations)
6. Schema markup suggestions (Product schema fields)

Return as JSON:
{{
  "meta_title": "",
  "meta_description": "",
  "target_keywords": [],
  "url_slug": "",
  "image_alt_texts": [],
  "schema_fields": {{}}
}}

Return ONLY valid JSON."""


def optimize_product_seo(
    title: str,
    description: str = "",
    price: str = "$249",
    niche: str = "LED/Red Light Therapy",
    brand_name: str = "Lumivara",
) -> dict:
    """Generate SEO-optimized metadata for a product."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": SEO_PROMPT.format(
                niche=niche,
                title=title,
                description=description[:500],
                price=price,
                brand_name=brand_name,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


def optimize_all_products(
    niche: str = "LED/Red Light Therapy",
    brand_name: str = "Lumivara",
    dry_run: bool = True,
) -> list[dict]:
    """Optimize SEO for all products in the store."""
    products = get_products(limit=250)
    results = []

    for product in products:
        variant = product["variants"][0] if product.get("variants") else {}
        price = f"${variant.get('price', '0')}"

        seo = optimize_product_seo(
            title=product["title"],
            description=product.get("body_html", ""),
            price=price,
            niche=niche,
            brand_name=brand_name,
        )

        result = {"id": product["id"], "title": product["title"], **seo, "pushed": False}

        if not dry_run:
            update_product(product["id"], {
                "metafields_global_title_tag": seo.get("meta_title", ""),
                "metafields_global_description_tag": seo.get("meta_description", ""),
                "handle": seo.get("url_slug", ""),
            })
            result["pushed"] = True

        results.append(result)
        print(f"  ✓ {product['title']}")

    return results


if __name__ == "__main__":
    print("SEO Optimization (DRY RUN)\n" + "="*50)
    results = optimize_all_products(dry_run=True)
    print(f"\nOptimized {len(results)} products.")
    if results:
        print(json.dumps(results[0], indent=2))
