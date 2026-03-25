"""
AI Customer Service Auto-Responder — handles common customer queries
(order status, returns, shipping) using Claude, integrated with Shopify orders.
"""
import os
import json
import anthropic
from dotenv import load_dotenv
from shopify_client import get_order, get_orders

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """You are a premium customer service representative for {brand_name}.

Your tone is: warm, professional, empathetic, and solution-oriented.
You represent a high-end brand — every interaction should make the customer feel valued.

Rules:
- NEVER say "I'm an AI" or "I'm a bot"
- ALWAYS address the customer by first name
- For order status: provide specific tracking info if available
- For returns: our policy is 30-day hassle-free returns
- For shipping: standard is 3-5 business days within the US
- If you can't resolve it, say "I've escalated this to our specialist team — you'll hear back within 24 hours"
- Sign off with your name: "Alex from {brand_name}"

Current order data (if available):
{order_context}"""


def get_order_context(email: str) -> str:
    """Look up recent orders for a customer email."""
    orders = get_orders(status="any", limit=10)
    customer_orders = [
        o for o in orders
        if o.get("email", "").lower() == email.lower()
    ]
    if not customer_orders:
        return "No orders found for this customer."

    context_parts = []
    for order in customer_orders[:3]:
        fulfillments = order.get("fulfillments", [])
        tracking = "Not yet shipped"
        if fulfillments:
            f = fulfillments[0]
            tracking = f.get("tracking_url", f.get("tracking_number", "Processing"))

        context_parts.append(
            f"Order #{order['order_number']} — "
            f"Status: {order.get('fulfillment_status', 'unfulfilled')} — "
            f"Total: ${order.get('total_price', '0')} — "
            f"Tracking: {tracking}"
        )
    return "\n".join(context_parts)


def respond_to_customer(
    customer_email: str,
    customer_name: str,
    message: str,
    brand_name: str = "Our Store",
) -> str:
    """Generate a customer service response."""
    order_context = get_order_context(customer_email)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT.format(
            brand_name=brand_name,
            order_context=order_context,
        ),
        messages=[{
            "role": "user",
            "content": f"Customer name: {customer_name}\nEmail: {customer_email}\n\nTheir message:\n{message}",
        }],
    )
    return response.content[0].text.strip()


# ── Email templates for common scenarios ──────────────────────────────
TEMPLATES = {
    "order_confirmation": """Hi {name},

Thank you for your order! We're preparing #{order_number} now.

You'll receive a tracking number within 24 hours once it ships.
Expected delivery: 3-5 business days.

Questions? Just reply to this email.

Warm regards,
Alex from {brand_name}""",

    "shipping_update": """Hi {name},

Great news — your order #{order_number} is on its way!

Tracking: {tracking_url}
Estimated delivery: {estimated_delivery}

We can't wait for you to experience it.

Best,
Alex from {brand_name}""",

    "return_approved": """Hi {name},

Your return for order #{order_number} has been approved.

Here's your prepaid return label: {return_label_url}

Once we receive the item, your refund will process within 3-5 business days.

Thank you for giving us a try — we hope to see you again.

Warm regards,
Alex from {brand_name}""",
}


def get_template(template_name: str, **kwargs) -> str:
    """Fill in an email template with provided values."""
    template = TEMPLATES.get(template_name, "")
    if not template:
        raise ValueError(f"Unknown template: {template_name}")
    return template.format(**kwargs)
