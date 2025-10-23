from __future__ import annotations
from typing import Dict, Any
from .base_client import BaseClient

class LiquipediaClient(BaseClient):
    """
    MediaWiki API Liquipedia: ищем по Fortnite/terms.
    Нужен корректный User-Agent.
    """
    def __init__(self, base_url: str, user_agent: str):
        super().__init__(user_agent=user_agent)
        self.base_url = base_url

    def search(self, term: str = "Fortnite", limit: int = 25) -> Dict[str, Any]:
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": term,
            "srlimit": limit,
        }
        r = self.get(self.base_url, params=params)
        r.raise_for_status()
        return r.json()