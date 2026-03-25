"""
Shopify API Client — handles authentication and core CRUD operations
for products, orders, and inventory.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-01")
BASE_URL = f"https://{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}"

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json",
}


def _get(endpoint: str, params: dict | None = None) -> dict:
    resp = requests.get(f"{BASE_URL}/{endpoint}.json", headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _put(endpoint: str, payload: dict) -> dict:
    resp = requests.put(f"{BASE_URL}/{endpoint}.json", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(endpoint: str, payload: dict) -> dict:
    resp = requests.post(f"{BASE_URL}/{endpoint}.json", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── Products ──────────────────────────────────────────────────────────
def get_products(limit: int = 50) -> list[dict]:
    """Fetch products from the store."""
    data = _get("products", {"limit": limit})
    return data.get("products", [])


def get_product(product_id: int) -> dict:
    return _get(f"products/{product_id}").get("product", {})


def update_product(product_id: int, updates: dict) -> dict:
    return _put(f"products/{product_id}", {"product": {"id": product_id, **updates}})


def create_product(product_data: dict) -> dict:
    return _post("products", {"product": product_data})


# ── Orders ────────────────────────────────────────────────────────────
def get_orders(status: str = "any", limit: int = 50) -> list[dict]:
    data = _get("orders", {"status": status, "limit": limit})
    return data.get("orders", [])


def get_order(order_id: int) -> dict:
    return _get(f"orders/{order_id}").get("order", {})


# ── Inventory ─────────────────────────────────────────────────────────
def get_inventory_levels(location_id: int) -> list[dict]:
    data = _get("inventory_levels", {"location_ids": location_id})
    return data.get("inventory_levels", [])


def set_inventory(inventory_item_id: int, location_id: int, available: int) -> dict:
    return _post("inventory_levels/set", {
        "inventory_item_id": inventory_item_id,
        "location_id": location_id,
        "available": available,
    })
