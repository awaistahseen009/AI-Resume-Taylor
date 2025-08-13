from typing import List, Dict, Any, Optional
import os
import requests

class TavilyClient:
    """Thin wrapper around Tavily Search API."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.tavily.com"):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.base_url = base_url.rstrip("/")

    def search_jobs(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        url = f"{self.base_url}/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max(1, min(max_results, 10))
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json() or {}
            results = data.get("results") or data.get("data") or []
            items: List[Dict[str, Any]] = []
            for item in results:
                items.append({
                    "title": item.get("title") or item.get("name") or "",
                    "url": item.get("url") or item.get("link") or "",
                    "snippet": item.get("snippet") or item.get("content") or "",
                    "source": item.get("source") or "web"
                })
            return items
        except Exception:
            return []
