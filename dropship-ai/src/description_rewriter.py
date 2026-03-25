"""
AI Product Description Rewriter — takes generic supplier descriptions
and rewrites them as luxury-brand copy using Claude.
"""
import os
import anthropic
from dotenv import load_dotenv
from shopify_client import get_products, update_product

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

BRAND_VOICE_PROMPT = """You are a luxury brand copywriter for a premium e-commerce store.

Rewrite the following product description so it:
- Sounds like it belongs on a high-end brand website (think Dyson, Restoration Hardware, Aesop)
- Leads with the BENEFIT to the customer, not the feature list
- Uses sensory language and short, punchy sentences
- Includes a compelling one-liner hook at the top
- Keeps SEO keywords naturally embedded
- Is 150-250 words max
- NEVER sounds like AI wrote it — no "elevate", "transform", "revolutionize"

Brand tone: {brand_tone}
Product title: {title}
Original description:
{description}

Rewritten description:"""


def rewrite_description(
    title: str,
    description: str,
    brand_tone: str = "Sophisticated, warm, understated confidence",
) -> str:
    """Rewrite a single product description using Claude."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": BRAND_VOICE_PROMPT.format(
                brand_tone=brand_tone,
                title=title,
                description=description,
            ),
        }],
    )
    return message.content[0].text.strip()


def rewrite_all_products(
    brand_tone: str = "Sophisticated, warm, understated confidence",
    dry_run: bool = True,
) -> list[dict]:
    """Fetch all products and rewrite their descriptions.

    Set dry_run=False to push changes live to Shopify.
    """
    products = get_products(limit=250)
    results = []

    for product in products:
        original = product.get("body_html", "") or ""
        if not original.strip():
            continue

        new_desc = rewrite_description(product["title"], original, brand_tone)
        result = {
            "id": product["id"],
            "title": product["title"],
            "original": original,
            "rewritten": new_desc,
            "pushed": False,
        }

        if not dry_run:
            update_product(product["id"], {"body_html": new_desc})
            result["pushed"] = True

        results.append(result)
        print(f"  ✓ {product['title']}")

    return results


if __name__ == "__main__":
    import json
    print("Running in DRY RUN mode (no changes pushed to Shopify)...\n")
    results = rewrite_all_products(dry_run=True)
    print(f"\nRewrote {len(results)} product descriptions.")
    print(json.dumps(results[:2], indent=2))
