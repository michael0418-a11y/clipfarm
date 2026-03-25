"""
Multi-Platform Store Client — supports free platforms (TikTok Shop,
Square Online, WooCommerce) alongside Shopify.

Defaults to TikTok Shop for $0 startup.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

PLATFORM = os.getenv("STORE_PLATFORM", "tiktok")  # tiktok | shopify | woocommerce | square

# ── Shopify ───────────────────────────────────────────────────────────
SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-01")

# ── WooCommerce ───────────────────────────────────────────────────────
WOO_URL = os.getenv("WOO_STORE_URL", "")
WOO_KEY = os.getenv("WOO_CONSUMER_KEY", "")
WOO_SECRET = os.getenv("WOO_CONSUMER_SECRET", "")

# ── TikTok Shop ───────────────────────────────────────────────────────
TIKTOK_SHOP_APP_KEY = os.getenv("TIKTOK_SHOP_APP_KEY", "")
TIKTOK_SHOP_APP_SECRET = os.getenv("TIKTOK_SHOP_APP_SECRET", "")
TIKTOK_SHOP_ACCESS_TOKEN = os.getenv("TIKTOK_SHOP_ACCESS_TOKEN", "")


class StoreClient:
    """Unified interface for multiple e-commerce platforms."""

    def __init__(self, platform: str = PLATFORM):
        self.platform = platform.lower()

    def get_products(self, limit: int = 50) -> list[dict]:
        if self.platform == "shopify":
            return self._shopify_get("products", {"limit": limit}).get("products", [])
        elif self.platform == "woocommerce":
            return self._woo_get("products", {"per_page": limit})
        elif self.platform == "tiktok":
            return self._tiktok_get_products(limit)
        return []

    def update_product(self, product_id, updates: dict) -> dict:
        if self.platform == "shopify":
            return self._shopify_put(f"products/{product_id}", {"product": {"id": product_id, **updates}})
        elif self.platform == "woocommerce":
            return self._woo_put(f"products/{product_id}", updates)
        elif self.platform == "tiktok":
            return self._tiktok_update_product(product_id, updates)
        return {}

    def get_orders(self, limit: int = 50) -> list[dict]:
        if self.platform == "shopify":
            return self._shopify_get("orders", {"status": "any", "limit": limit}).get("orders", [])
        elif self.platform == "woocommerce":
            return self._woo_get("orders", {"per_page": limit})
        elif self.platform == "tiktok":
            return self._tiktok_get_orders(limit)
        return []

    # ── Shopify methods ───────────────────────────────────────────
    def _shopify_headers(self):
        return {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN, "Content-Type": "application/json"}

    def _shopify_base(self):
        return f"https://{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}"

    def _shopify_get(self, endpoint, params=None):
        r = requests.get(f"{self._shopify_base()}/{endpoint}.json",
                         headers=self._shopify_headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _shopify_put(self, endpoint, payload):
        r = requests.put(f"{self._shopify_base()}/{endpoint}.json",
                         headers=self._shopify_headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    # ── WooCommerce methods ───────────────────────────────────────
    def _woo_get(self, endpoint, params=None):
        r = requests.get(f"{WOO_URL}/wp-json/wc/v3/{endpoint}",
                         auth=(WOO_KEY, WOO_SECRET), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _woo_put(self, endpoint, payload):
        r = requests.put(f"{WOO_URL}/wp-json/wc/v3/{endpoint}",
                         auth=(WOO_KEY, WOO_SECRET), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    # ── TikTok Shop methods ───────────────────────────────────────
    def _tiktok_headers(self):
        return {
            "x-tts-access-token": TIKTOK_SHOP_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }

    def _tiktok_get_products(self, limit):
        # TikTok Shop API v2
        r = requests.post(
            "https://open-api.tiktokglobalshop.com/product/202309/products/search",
            headers=self._tiktok_headers(),
            json={"page_size": limit},
            timeout=30,
        )
        if r.ok:
            return r.json().get("data", {}).get("products", [])
        return []

    def _tiktok_update_product(self, product_id, updates):
        r = requests.put(
            f"https://open-api.tiktokglobalshop.com/product/202309/products/{product_id}",
            headers=self._tiktok_headers(),
            json=updates,
            timeout=30,
        )
        return r.json() if r.ok else {}

    def _tiktok_get_orders(self, limit):
        r = requests.post(
            "https://open-api.tiktokglobalshop.com/order/202309/orders/search",
            headers=self._tiktok_headers(),
            json={"page_size": limit},
            timeout=30,
        )
        if r.ok:
            return r.json().get("data", {}).get("orders", [])
        return []


# Convenience functions matching the old shopify_client interface
_client = StoreClient()

def get_products(limit=50): return _client.get_products(limit)
def update_product(product_id, updates): return _client.update_product(product_id, updates)
def get_orders(limit=50): return _client.get_orders(limit)
