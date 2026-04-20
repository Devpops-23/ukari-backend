# utils/marketplace_client.py

from typing import List, Dict, Any
import httpx


class MarketplaceClient:
    """
    Thin wrapper around external marketplace APIs (Amazon, Walmart, etc.).
    For now, this uses placeholder endpoints and expects you to plug in
    real API URLs + auth keys.
    """

    def __init__(self, amazon_api_key: str | None = None, walmart_api_key: str | None = None):
        self.amazon_api_key = amazon_api_key
        self.walmart_api_key = walmart_api_key

    # -----------------------------
    # PUBLIC METHODS
    # -----------------------------
    def search_products(self, source: str, query: str) -> List[Dict[str, Any]]:
        if source == "amazon":
            return self._search_amazon(query)
        elif source == "walmart":
            return self._search_walmart(query)
        else:
            raise ValueError("Unsupported marketplace source")

    def get_product_details(self, source: str, product_id: str) -> Dict[str, Any]:
        if source == "amazon":
            return self._get_amazon_product(product_id)
        elif source == "walmart":
            return self._get_walmart_product(product_id)
        else:
            raise ValueError("Unsupported marketplace source")

    # -----------------------------
    # AMAZON (PLACEHOLDER)
    # -----------------------------
    def _search_amazon(self, query: str) -> List[Dict[str, Any]]:
        # TODO: Replace with real Amazon Product Advertising API call
        # This is a stub returning fake data structure for now.
        return [
            {
                "id": "AMZ-EXAMPLE-1",
                "title": f"Sample Amazon Item for '{query}'",
                "price": 49.99,
                "image_url": "https://example.com/amazon-item.jpg",
            }
        ]

    def _get_amazon_product(self, product_id: str) -> Dict[str, Any]:
        # TODO: Replace with real Amazon Product Advertising API call
        return {
            "id": product_id,
            "title": "Sample Amazon Product",
            "price": 49.99,
            "image_url": "https://example.com/amazon-item.jpg",
            "weight": 1.5,  # kg
        }

    # -----------------------------
    # WALMART (PLACEHOLDER)
    # -----------------------------
    def _search_walmart(self, query: str) -> List[Dict[str, Any]]:
        # TODO: Replace with real Walmart API call
        return [
            {
                "id": "WMT-EXAMPLE-1",
                "title": f"Sample Walmart Item for '{query}'",
                "price": 39.99,
                "image_url": "https://example.com/walmart-item.jpg",
            }
        ]

    def _get_walmart_product(self, product_id: str) -> Dict[str, Any]:
        # TODO: Replace with real Walmart API call
        return {
            "id": product_id,
            "title": "Sample Walmart Product",
            "price": 39.99,
            "image_url": "https://example.com/walmart-item.jpg",
            "weight": 2.0,  # kg
        }


# Singleton-style accessor
def get_marketplace_client() -> MarketplaceClient:
    # Later: load real keys from env
    return MarketplaceClient(
        amazon_api_key=None,
        walmart_api_key=None,
    )
