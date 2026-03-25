"""
Email Marketing Sequence Generator — creates automated email flows
for abandoned carts, post-purchase, and win-back campaigns.
"""
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SEQUENCE_PROMPT = """You are an email marketing strategist for a premium {niche} DTC brand.

Create a complete {sequence_type} email sequence.

Brand name: {brand_name}
Brand voice: {brand_voice}
Product examples: {products}
Target customer: {target_customer}

For each email, provide:
1. Subject line (+ 2 A/B test alternatives)
2. Preview text
3. Send timing (e.g., "2 hours after cart abandonment")
4. Full email body (HTML-ready with placeholders like {{{{first_name}}}}, {{{{product_name}}}}, {{{{cart_url}}}})
5. CTA button text

Return as JSON array with keys:
email_number, subject_line, subject_alternatives, preview_text,
send_timing, body_html, cta_text

Return ONLY valid JSON."""

SEQUENCES = {
    "abandoned_cart": {
        "name": "Abandoned Cart Recovery",
        "emails": 3,
        "description": "Re-engage shoppers who left items in cart",
    },
    "welcome": {
        "name": "Welcome Series",
        "emails": 5,
        "description": "Onboard new subscribers and drive first purchase",
    },
    "post_purchase": {
        "name": "Post-Purchase Nurture",
        "emails": 4,
        "description": "Build loyalty, encourage reviews, and upsell",
    },
    "winback": {
        "name": "Win-Back Campaign",
        "emails": 3,
        "description": "Re-engage lapsed customers",
    },
    "launch": {
        "name": "Product Launch Hype",
        "emails": 5,
        "description": "Build anticipation and drive launch-day sales",
    },
}


def generate_email_sequence(
    sequence_type: str = "abandoned_cart",
    niche: str = "LED/Red Light Therapy",
    brand_name: str = "Lumivara",
    brand_voice: str = "Warm, premium, science-backed, empathetic",
    products: str = "LED Face Mask ($249), Red Light Panel ($499), Therapy Wand ($149)",
    target_customer: str = "Women 25-40, skincare enthusiasts with $60K+ income",
) -> list[dict]:
    """Generate a complete email marketing sequence."""
    seq = SEQUENCES.get(sequence_type, SEQUENCES["abandoned_cart"])

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": SEQUENCE_PROMPT.format(
                niche=niche,
                sequence_type=f"{seq['name']} ({seq['emails']} emails — {seq['description']})",
                brand_name=brand_name,
                brand_voice=brand_voice,
                products=products,
                target_customer=target_customer,
            ),
        }],
    )
    return json.loads(message.content[0].text.strip())


def generate_all_sequences(**kwargs) -> dict[str, list[dict]]:
    """Generate all email sequences at once."""
    results = {}
    for seq_type in SEQUENCES:
        print(f"  Generating: {SEQUENCES[seq_type]['name']}...")
        results[seq_type] = generate_email_sequence(sequence_type=seq_type, **kwargs)
    return results


if __name__ == "__main__":
    import sys
    seq_type = sys.argv[1] if len(sys.argv) > 1 else "abandoned_cart"

    if seq_type == "all":
        print("Generating all email sequences...\n")
        all_seqs = generate_all_sequences()
        for name, emails in all_seqs.items():
            print(f"\n{'='*50}")
            print(f"{SEQUENCES[name]['name']} — {len(emails)} emails")
            for email in emails:
                print(f"  {email.get('email_number', '?')}. {email.get('subject_line', '?')}")
                print(f"     Send: {email.get('send_timing', '?')}")
    else:
        print(f"Generating {SEQUENCES.get(seq_type, {}).get('name', seq_type)} sequence...\n")
        emails = generate_email_sequence(sequence_type=seq_type)
        for email in emails:
            print(f"\nEmail #{email.get('email_number', '?')}")
            print(f"  Subject: {email.get('subject_line', '?')}")
            print(f"  Timing: {email.get('send_timing', '?')}")
            print(f"  CTA: {email.get('cta_text', '?')}")
            alts = email.get("subject_alternatives", [])
            for alt in alts:
                print(f"  Alt subject: {alt}")
